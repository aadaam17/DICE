from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from dice.adapters.base import ChainAdapter
from dice.core.models import JobConfig


@dataclass(frozen=True, slots=True)
class TransactionSimulation:
    gas_limit: int
    fee_per_gas_wei: int | None
    max_cost_wei: int | None
    max_cost_native: str | None
    native_symbol: str

    def to_dict(self) -> dict[str, object]:
        return {
            "gas_limit": self.gas_limit,
            "fee_per_gas_wei": self.fee_per_gas_wei,
            "max_cost_wei": self.max_cost_wei,
            "max_cost_native": self.max_cost_native,
            "native_symbol": self.native_symbol,
        }

    def summary(self) -> str:
        if self.max_cost_native is None:
            return f"estimated gas {self.gas_limit:,}"
        return f"estimated gas {self.gas_limit:,}, max fee {self.max_cost_native} {self.native_symbol}"


class TransactionSimulator:
    def __init__(self, adapter: ChainAdapter) -> None:
        self.adapter = adapter

    async def simulate(self, job: JobConfig, from_address: str) -> TransactionSimulation:
        build_transaction = getattr(self.adapter, "build_transaction", None)
        if not callable(build_transaction):
            gas_limit = await self.adapter.estimate_gas(
                {
                    "contract": job.contract.address if job.contract else None,
                    "function": job.execution.function_name,
                    "arguments": job.execution.arguments,
                }
            )
            return TransactionSimulation(
                gas_limit=gas_limit,
                fee_per_gas_wei=None,
                max_cost_wei=None,
                max_cost_native=None,
                native_symbol=self.adapter.profile.native_symbol,
            )

        transaction = await build_transaction(job, from_address)
        return transaction_cost(transaction, self.adapter.profile.native_symbol)


def transaction_cost(transaction: dict[str, Any], native_symbol: str) -> TransactionSimulation:
    gas_limit = int(transaction.get("gas", 0))
    fee_per_gas = _fee_per_gas(transaction)
    max_cost_wei = gas_limit * fee_per_gas if fee_per_gas is not None else None
    max_cost_native = _wei_to_native(max_cost_wei) if max_cost_wei is not None else None
    return TransactionSimulation(
        gas_limit=gas_limit,
        fee_per_gas_wei=fee_per_gas,
        max_cost_wei=max_cost_wei,
        max_cost_native=max_cost_native,
        native_symbol=native_symbol,
    )


def _fee_per_gas(transaction: dict[str, Any]) -> int | None:
    if transaction.get("maxFeePerGas") is not None:
        return int(transaction["maxFeePerGas"])
    if transaction.get("gasPrice") is not None:
        return int(transaction["gasPrice"])
    return None


def _wei_to_native(value: int) -> str:
    native = Decimal(value) / Decimal(10**18)
    return format(native.normalize(), "f")
