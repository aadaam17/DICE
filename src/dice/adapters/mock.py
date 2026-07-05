from __future__ import annotations

import asyncio
from hashlib import sha256

from dice.adapters.base import ChainProfile


class MockChainAdapter:
    def __init__(self, profile: ChainProfile) -> None:
        self.profile = profile
        self.connected = False
        self._block = 1

    async def connect(self) -> None:
        await asyncio.sleep(0)
        self.connected = True

    async def latest_block(self) -> int:
        await asyncio.sleep(0)
        self._block += 1
        return self._block

    async def estimate_gas(self, payload: dict[str, object]) -> int:
        await asyncio.sleep(0)
        return 21_000 + len(repr(payload))

    async def get_code(self, address: str) -> str:
        await asyncio.sleep(0)
        return "0x01" if address else "0x"

    async def broadcast(self, signed_transaction: str) -> str:
        await asyncio.sleep(0)
        digest = sha256(signed_transaction.encode("utf-8")).hexdigest()
        return "0x" + digest

    async def close(self) -> None:
        await asyncio.sleep(0)
        self.connected = False
