from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ChainProfile:
    key: str
    name: str
    chain_id: int
    native_symbol: str
    explorer_url: str
    default_http_rpc: str | None = None
    default_websocket_rpc: str | None = None


class ChainAdapter(Protocol):
    profile: ChainProfile

    async def connect(self) -> None:
        """Open network resources for this adapter."""

    async def latest_block(self) -> int:
        """Return latest observed block number."""

    async def estimate_gas(self, payload: dict[str, object]) -> int:
        """Estimate gas for a prepared transaction payload."""

    async def broadcast(self, signed_transaction: str) -> str:
        """Broadcast a signed transaction and return its transaction hash."""

    async def close(self) -> None:
        """Release network resources."""
