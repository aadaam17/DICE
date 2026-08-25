from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from dice.core.secrets import SecretStore


class SignerError(RuntimeError):
    """Raised when a transaction cannot be signed."""


@dataclass(slots=True)
class SignedTransaction:
    raw_transaction: Any
    signer_address: str


class PrivateKeySigner:
    def __init__(self, secret_store: SecretStore) -> None:
        self.secret_store = secret_store

    def address_for_ref(self, private_key_ref: str) -> str:
        private_key = self.secret_store.load_private_key(private_key_ref)
        try:
            from eth_account import Account
        except ImportError as exc:
            raise SignerError("eth-account is required for signing. Run: pip install -r requirements.txt") from exc
        return str(Account.from_key(private_key).address)

    def solana_address_for_ref(self, private_key_ref: str) -> str:
        keypair = self._solana_keypair(private_key_ref)
        return str(keypair.pubkey())

    def sign_transaction(self, transaction: dict[str, object], private_key_ref: str) -> SignedTransaction:
        if transaction.get("__chain") == "solana":
            return self._sign_solana_transaction(transaction, private_key_ref)

        private_key = self.secret_store.load_private_key(private_key_ref)
        try:
            from eth_account import Account
        except ImportError as exc:
            raise SignerError("eth-account is required for signing. Run: pip install -r requirements.txt") from exc

        account = Account.from_key(private_key)
        signed = account.sign_transaction(transaction)
        raw = getattr(signed, "raw_transaction", None) or getattr(signed, "rawTransaction", None)
        if raw is None:
            raise SignerError("Signed transaction did not include raw transaction bytes")
        if isinstance(raw, bytes):
            raw_hex = "0x" + raw.hex()
        else:
            raw_hex = str(raw)
        return SignedTransaction(raw_transaction=raw_hex, signer_address=str(account.address))

    def _sign_solana_transaction(
        self,
        transaction: dict[str, object],
        private_key_ref: str,
    ) -> SignedTransaction:
        try:
            from solders.transaction import VersionedTransaction
        except ImportError as exc:
            raise SignerError("solders is required for Solana signing. Run: pip install -r requirements.txt") from exc
        keypair = self._solana_keypair(private_key_ref)
        message = transaction.get("message")
        if message is None:
            raise SignerError("Solana transaction did not include a message")
        signed = VersionedTransaction(message, [keypair])
        return SignedTransaction(raw_transaction=bytes(signed), signer_address=str(keypair.pubkey()))

    def _solana_keypair(self, private_key_ref: str):
        private_key = self.secret_store.load_private_key(private_key_ref)
        try:
            from solders.keypair import Keypair
        except ImportError as exc:
            raise SignerError("solders is required for Solana signing. Run: pip install -r requirements.txt") from exc
        value = private_key.strip()
        try:
            return Keypair.from_base58_string(value)
        except Exception:
            pass
        try:
            raw = json.loads(value)
        except json.JSONDecodeError as exc:
            raise SignerError("Solana private key must be a base58 keypair string or a JSON byte array") from exc
        if not isinstance(raw, list) or not all(isinstance(item, int) for item in raw):
            raise SignerError("Solana private key JSON must be an array of bytes")
        try:
            return Keypair.from_bytes(bytes(raw))
        except Exception as exc:
            raise SignerError("Solana private key JSON bytes did not form a valid keypair") from exc
