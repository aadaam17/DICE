from __future__ import annotations

from dice.adapters.base import ChainAdapter
from dice.execution.builder import TransactionPayload


class Broadcaster:
    def __init__(self, adapter: ChainAdapter) -> None:
        self.adapter = adapter

    async def broadcast(self, payload: TransactionPayload) -> str:
        # Real signing belongs behind a signer abstraction. This development path is deterministic.
        signed_development_tx = repr(payload)
        return await self.adapter.broadcast(signed_development_tx)
