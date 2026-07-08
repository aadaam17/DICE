from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from pathlib import Path


class SecretStoreError(RuntimeError):
    """Raised when a secret cannot be stored or read safely."""


@dataclass(frozen=True, slots=True)
class WalletSecret:
    ref: str
    wallet_id: str
    label: str
    address: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "ref": self.ref,
            "wallet_id": self.wallet_id,
            "label": self.label,
            "address": self.address,
        }


class SecretStore:
    def __init__(
        self,
        root: Path = Path("storage/secrets"),
        password_env: str = "DICE_SECRET_PASSWORD",
    ) -> None:
        self.root = root
        self.password_env = password_env
        self.root.mkdir(parents=True, exist_ok=True)

    def store_private_key(self, job_id: str, label: str, private_key: str) -> str:
        return self.store_wallet(job_id, label, None, private_key)

    def store_wallet(
        self,
        wallet_id: str,
        label: str,
        address: str | None,
        private_key: str,
    ) -> str:
        private_key = private_key.strip()
        if not private_key:
            raise SecretStoreError("Private key is empty")
        if not _looks_like_private_key(private_key):
            raise SecretStoreError("Private key must look like a 32-byte EVM private key")

        fernet = self._fernet()
        safe_wallet_id = _safe_secret_name(wallet_id)
        ref = f"secret://wallets/{safe_wallet_id}"
        payload = {
            "version": 1,
            "kind": "evm_private_key",
            "wallet_id": safe_wallet_id,
            "label": label,
            "address": address,
            "ciphertext": fernet.encrypt(private_key.encode("utf-8")).decode("utf-8"),
        }
        path = self._path_for_ref(ref)
        temp_path = path.with_suffix(".json.tmp")
        temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        temp_path.replace(path)
        return ref

    def list_wallets(self) -> list[WalletSecret]:
        wallets: list[WalletSecret] = []
        for path in sorted(self.root.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if data.get("kind") != "evm_private_key":
                continue
            wallet_id = str(data.get("wallet_id") or path.stem)
            wallets.append(
                WalletSecret(
                    ref=f"secret://wallets/{wallet_id}",
                    wallet_id=wallet_id,
                    label=str(data.get("label") or wallet_id),
                    address=data.get("address"),
                )
            )
        return wallets

    def load_private_key(self, ref: str) -> str:
        path = self._path_for_ref(ref)
        if not path.exists():
            raise SecretStoreError(f"Secret not found: {ref}")
        data = json.loads(path.read_text(encoding="utf-8"))
        return self._fernet().decrypt(data["ciphertext"].encode("utf-8")).decode("utf-8")

    def delete(self, ref: str | None) -> None:
        if not ref:
            return
        self._path_for_ref(ref).unlink(missing_ok=True)

    def _fernet(self):
        try:
            from cryptography.fernet import Fernet
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        except ImportError as exc:
            raise SecretStoreError(
                "cryptography is required for private key storage. Run: pip install -r requirements.txt"
            ) from exc

        password = os.environ.get(self.password_env)
        if not password:
            raise SecretStoreError(f"Set {self.password_env} before importing private keys")
        salt = b"dice-secret-store-v1"
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=390_000)
        key = base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))
        return Fernet(key)

    def _path_for_ref(self, ref: str) -> Path:
        prefix = "secret://wallets/"
        if not ref.startswith(prefix):
            raise SecretStoreError(f"Unsupported secret reference: {ref}")
        name = ref.removeprefix(prefix)
        return self.root / f"{_safe_secret_name(name)}.json"


def _looks_like_private_key(value: str) -> bool:
    key = value[2:] if value.startswith("0x") else value
    return len(key) == 64 and all(character in "0123456789abcdefABCDEF" for character in key)


def _safe_secret_name(value: str) -> str:
    safe_name = "".join(character for character in value.strip() if character.isalnum() or character in "-_")
    if not safe_name:
        raise SecretStoreError("Secret reference is empty")
    return safe_name
