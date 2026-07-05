from __future__ import annotations

from dataclasses import dataclass

from dice.core.models import JobConfig


@dataclass(frozen=True, slots=True)
class TransactionPayload:
    chain: str
    to: str | None
    function_name: str
    arguments: list[object]
    gas_limit: int


class TransactionBuilder:
    async def build(self, job: JobConfig, gas_limit: int) -> TransactionPayload:
        return TransactionPayload(
            chain=job.chain,
            to=job.contract.address if job.contract else None,
            function_name=job.execution.function_name,
            arguments=job.execution.arguments,
            gas_limit=gas_limit,
        )
