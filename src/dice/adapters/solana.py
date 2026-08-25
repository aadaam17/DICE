from __future__ import annotations

from typing import Any

from dice.adapters.base import ChainProfile
from dice.core.models import JobConfig, RpcConfig


LAMPORTS_PER_SOL = 1_000_000_000
DEFAULT_SIGNATURE_FEE_LAMPORTS = 5_000


class SolanaAdapterError(RuntimeError):
    """Raised when a Solana RPC operation cannot be completed."""


class SolanaChainAdapter:
    def __init__(self, profile: ChainProfile, rpc: RpcConfig) -> None:
        self.profile = profile
        self.rpc = rpc
        self._client: Any | None = None

    async def connect(self) -> None:
        try:
            from solana.rpc.async_api import AsyncClient
        except ImportError as exc:
            raise SolanaAdapterError("solana and solders are required for Solana execution. Run: pip install -r requirements.txt") from exc
        self._client = AsyncClient(self.rpc.http_url)
        if not await self._client.is_connected():
            raise SolanaAdapterError(f"Could not connect to Solana RPC: {self.rpc.http_url}")

    async def latest_block(self) -> int:
        response = await self._client_or_raise().get_slot()
        return int(response.value)

    async def get_native_balance(self, address: str) -> int:
        from solders.pubkey import Pubkey

        response = await self._client_or_raise().get_balance(Pubkey.from_string(address))
        return int(response.value)

    async def get_native_transferable_balance(
        self,
        job: JobConfig,
        from_address: str,
        destination: str,
    ) -> int:
        transaction = await self.build_native_transfer(job, from_address, destination, 0)
        fee = int(transaction.get("fee_lamports", DEFAULT_SIGNATURE_FEE_LAMPORTS))
        balance = await self.get_native_balance(from_address)
        return max(balance - fee, 0)

    async def build_native_transfer(
        self,
        job: JobConfig,
        from_address: str,
        destination: str,
        amount_lamports: int,
    ) -> dict[str, Any]:
        from solders.message import MessageV0
        from solders.pubkey import Pubkey
        from solders.system_program import TransferParams, transfer

        sender = Pubkey.from_string(from_address)
        recipient = Pubkey.from_string(destination)
        latest_blockhash = await self._client_or_raise().get_latest_blockhash()
        instruction = transfer(
            TransferParams(
                from_pubkey=sender,
                to_pubkey=recipient,
                lamports=int(amount_lamports),
            )
        )
        message = MessageV0.try_compile(
            payer=sender,
            instructions=[instruction],
            address_lookup_table_accounts=[],
            recent_blockhash=latest_blockhash.value.blockhash,
        )
        return {
            "__chain": "solana",
            "message": message,
            "from": str(sender),
            "to": str(recipient),
            "value": int(amount_lamports),
            "fee_lamports": await self._fee_for_message(message),
        }

    async def build_native_sweep_transfer(
        self,
        job: JobConfig,
        from_address: str,
        destination: str,
    ) -> dict[str, Any]:
        draft = await self.build_native_transfer(job, from_address, destination, 0)
        fee = int(draft.get("fee_lamports", DEFAULT_SIGNATURE_FEE_LAMPORTS))
        balance = await self.get_native_balance(from_address)
        amount = max(balance - fee, 0)
        return await self.build_native_transfer(job, from_address, destination, amount)

    async def get_erc20_balance(self, token_contract: str, address: str) -> int:
        from solders.pubkey import Pubkey
        from spl.token.instructions import get_associated_token_address

        owner = Pubkey.from_string(address)
        mint = Pubkey.from_string(token_contract)
        token_account = get_associated_token_address(owner, mint)
        try:
            response = await self._client_or_raise().get_token_account_balance(token_account)
        except Exception:
            return 0
        return int(response.value.amount)

    async def get_erc20_decimals(self, token_contract: str) -> int:
        from solders.pubkey import Pubkey

        response = await self._client_or_raise().get_token_supply(Pubkey.from_string(token_contract))
        return int(response.value.decimals)

    async def build_erc20_transfer(
        self,
        job: JobConfig,
        from_address: str,
        token_contract: str,
        destination: str,
        amount: int,
    ) -> dict[str, Any]:
        from solders.message import MessageV0
        from solders.pubkey import Pubkey
        from spl.token.constants import TOKEN_PROGRAM_ID
        from spl.token.instructions import (
            create_idempotent_associated_token_account,
            get_associated_token_address,
            transfer_checked,
        )
        from spl.token.models import TransferCheckedParams

        owner = Pubkey.from_string(from_address)
        receiver = Pubkey.from_string(destination)
        mint = Pubkey.from_string(token_contract)
        source_token_account = get_associated_token_address(owner, mint, TOKEN_PROGRAM_ID)
        destination_token_account = get_associated_token_address(receiver, mint, TOKEN_PROGRAM_ID)
        decimals = await self.get_erc20_decimals(token_contract)
        create_destination = create_idempotent_associated_token_account(
            payer=owner,
            owner=receiver,
            mint=mint,
            token_program_id=TOKEN_PROGRAM_ID,
        )
        transfer_instruction = transfer_checked(
            TransferCheckedParams(
                program_id=TOKEN_PROGRAM_ID,
                source=source_token_account,
                mint=mint,
                dest=destination_token_account,
                owner=owner,
                amount=int(amount),
                decimals=decimals,
                signers=[],
            )
        )
        latest_blockhash = await self._client_or_raise().get_latest_blockhash()
        message = MessageV0.try_compile(
            payer=owner,
            instructions=[create_destination, transfer_instruction],
            address_lookup_table_accounts=[],
            recent_blockhash=latest_blockhash.value.blockhash,
        )
        return {
            "__chain": "solana",
            "message": message,
            "from": str(owner),
            "to": str(receiver),
            "mint": str(mint),
            "source_token_account": str(source_token_account),
            "destination_token_account": str(destination_token_account),
            "value": int(amount),
            "fee_lamports": await self._fee_for_message(message),
        }

    async def estimate_gas(self, payload: dict[str, object]) -> int:
        return DEFAULT_SIGNATURE_FEE_LAMPORTS

    async def broadcast(self, signed_transaction: object) -> str:
        if not isinstance(signed_transaction, bytes):
            raise SolanaAdapterError("Solana broadcast requires signed transaction bytes")
        response = await self._client_or_raise().send_raw_transaction(signed_transaction)
        return str(response.value)

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
        self._client = None

    async def _fee_for_message(self, message: object) -> int:
        try:
            response = await self._client_or_raise().get_fee_for_message(message)
        except Exception:
            return DEFAULT_SIGNATURE_FEE_LAMPORTS
        return int(response.value or DEFAULT_SIGNATURE_FEE_LAMPORTS)

    def _client_or_raise(self) -> Any:
        if self._client is None:
            raise SolanaAdapterError("Adapter is not connected")
        return self._client
