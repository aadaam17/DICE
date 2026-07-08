from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dice.adapters.base import ChainProfile
from dice.core.models import GasMode, JobConfig, RpcConfig


class EVMAdapterError(RuntimeError):
    """Raised when a real EVM RPC operation cannot be completed."""


class EVMChainAdapter:
    def __init__(self, profile: ChainProfile, rpc: RpcConfig) -> None:
        self.profile = profile
        self.rpc = rpc
        self._web3: Any | None = None

    async def connect(self) -> None:
        web3 = self._load_web3()
        self._web3 = web3.Web3(
            web3.HTTPProvider(
                self.rpc.http_url,
                request_kwargs={"timeout": 5},
            )
        )
        if not self._web3.is_connected():
            raise EVMAdapterError(f"Could not connect to RPC: {self.rpc.http_url}")
        chain_id = int(self._web3.eth.chain_id)
        if chain_id != self.profile.chain_id:
            raise EVMAdapterError(
                f"RPC chain id {chain_id} does not match {self.profile.name} ({self.profile.chain_id})"
            )

    async def latest_block(self) -> int:
        return int(self._w3.eth.block_number)

    async def estimate_gas(self, payload: dict[str, object]) -> int:
        tx = payload.get("transaction")
        if isinstance(tx, dict):
            return int(self._w3.eth.estimate_gas(tx))
        raise EVMAdapterError("EVM gas estimation requires a transaction payload")

    async def get_code(self, address: str) -> str:
        code = self._w3.eth.get_code(self._w3.to_checksum_address(address))
        return self._w3.to_hex(code)

    async def broadcast(self, signed_transaction: str) -> str:
        tx_hash = self._w3.eth.send_raw_transaction(signed_transaction)
        return self._w3.to_hex(tx_hash)

    async def close(self) -> None:
        self._web3 = None

    async def build_transaction(self, job: JobConfig, from_address: str) -> dict[str, Any]:
        if not job.contract:
            raise EVMAdapterError("Real EVM execution currently requires a contract address and ABI")
        if not job.contract.abi_path:
            raise EVMAdapterError("Real EVM execution requires an ABI path")

        contract = self._w3.eth.contract(
            address=self._w3.to_checksum_address(job.contract.address),
            abi=self._load_abi(job.contract.abi_path),
        )
        function = getattr(contract.functions, job.execution.function_name, None)
        if function is None:
            raise EVMAdapterError(f"ABI does not expose function: {job.execution.function_name}")

        sender = self._w3.to_checksum_address(from_address)
        base_tx = {
            "from": sender,
            "nonce": self._w3.eth.get_transaction_count(sender),
            "chainId": self.profile.chain_id,
        }
        base_tx.update(self._gas_price_fields(job))
        tx = function(*job.execution.arguments).build_transaction(base_tx)
        tx["gas"] = int(self._w3.eth.estimate_gas(tx))
        return tx

    async def build_native_transfer(
        self,
        job: JobConfig,
        from_address: str,
        destination: str,
        amount_wei: int,
    ) -> dict[str, Any]:
        sender = self._w3.to_checksum_address(from_address)
        tx = {
            "from": sender,
            "to": self._w3.to_checksum_address(destination),
            "value": int(amount_wei),
            "nonce": self._w3.eth.get_transaction_count(sender),
            "chainId": self.profile.chain_id,
        }
        tx.update(self._gas_price_fields(job))
        tx["gas"] = int(self._w3.eth.estimate_gas(tx))
        return tx

    async def build_erc20_transfer(
        self,
        job: JobConfig,
        from_address: str,
        token_contract: str,
        destination: str,
        amount: int,
    ) -> dict[str, Any]:
        contract = self._w3.eth.contract(
            address=self._w3.to_checksum_address(token_contract),
            abi=[
                {
                    "constant": False,
                    "inputs": [
                        {"name": "to", "type": "address"},
                        {"name": "value", "type": "uint256"},
                    ],
                    "name": "transfer",
                    "outputs": [{"name": "", "type": "bool"}],
                    "type": "function",
                }
            ],
        )
        sender = self._w3.to_checksum_address(from_address)
        base_tx = {
            "from": sender,
            "nonce": self._w3.eth.get_transaction_count(sender),
            "chainId": self.profile.chain_id,
        }
        base_tx.update(self._gas_price_fields(job))
        tx = contract.functions.transfer(
            self._w3.to_checksum_address(destination),
            int(amount),
        ).build_transaction(base_tx)
        tx["gas"] = int(self._w3.eth.estimate_gas(tx))
        return tx

    @property
    def _w3(self) -> Any:
        if self._web3 is None:
            raise EVMAdapterError("Adapter is not connected")
        return self._web3

    def _gas_price_fields(self, job: JobConfig) -> dict[str, int]:
        if job.gas.mode == GasMode.CUSTOM:
            fields: dict[str, int] = {}
            if job.gas.max_fee_gwei is not None:
                fields["maxFeePerGas"] = self._w3.to_wei(job.gas.max_fee_gwei, "gwei")
            if job.gas.priority_fee_gwei is not None:
                fields["maxPriorityFeePerGas"] = self._w3.to_wei(job.gas.priority_fee_gwei, "gwei")
            if fields:
                return fields
        multiplier = {
            GasMode.STANDARD: 1.0,
            GasMode.AGGRESSIVE: 1.2,
            GasMode.ULTRA: 1.5,
            GasMode.CUSTOM: 1.0,
        }[job.gas.mode]
        return {"gasPrice": int(self._w3.eth.gas_price * multiplier)}

    def _load_abi(self, abi_path: str) -> list[dict[str, Any]]:
        path = Path(abi_path)
        if not path.exists():
            raise EVMAdapterError(f"ABI file not found: {abi_path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "abi" in data:
            data = data["abi"]
        if not isinstance(data, list):
            raise EVMAdapterError("ABI file must contain an ABI list or an object with an 'abi' key")
        return data

    def _load_web3(self):
        try:
            import web3
        except ImportError as exc:
            raise EVMAdapterError("web3 is required for real EVM execution. Run: pip install -r requirements.txt") from exc
        return web3
