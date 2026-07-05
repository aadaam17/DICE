from __future__ import annotations

from dataclasses import dataclass

from dice.core.secrets import SecretStore


class SignerError(RuntimeError):
    """Raised when a transaction cannot be signed."""


@dataclass(slots=True)
class SignedTransaction:
    raw_transaction: str
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

    def sign_transaction(self, transaction: dict[str, object], private_key_ref: str) -> SignedTransaction:
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
