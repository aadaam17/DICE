from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from dice.adapters.base import ChainAdapter
from dice.core.models import JobConfig, SweepAssetKind, TriggerConfig, TriggerKind


class TriggerEvaluator:
    def __init__(self, adapter: ChainAdapter) -> None:
        self.adapter = adapter
        self._last_balances: dict[str, int] = {}

    async def should_execute(self, trigger: TriggerConfig, job: JobConfig | None = None) -> bool:
        if trigger.kind == TriggerKind.MANUAL:
            return True
        if trigger.kind == TriggerKind.TIMESTAMP:
            timestamp = int(trigger.params["timestamp"])
            return datetime.now(UTC).timestamp() >= timestamp
        if trigger.kind == TriggerKind.BLOCK:
            target_block = int(trigger.params["block"])
            return await self.adapter.latest_block() >= target_block
        if trigger.kind == TriggerKind.BALANCE_CHANGE:
            return await self._balance_changed(trigger, job)
        return False

    async def _balance_changed(self, trigger: TriggerConfig, job: JobConfig | None) -> bool:
        address = str(trigger.params.get("address") or (job.wallet.address if job else ""))
        if not address:
            return False
        balance = await self._balance_for_job(address, job)
        minimum = job.execution.min_amount if job and job.execution.min_amount is not None else 1
        previous = self._last_balances.get(address)
        self._last_balances[address] = balance
        if balance < minimum:
            return False
        return previous is None or balance > previous

    async def _balance_for_job(self, address: str, job: JobConfig | None) -> int:
        if job and job.execution.asset_kind == SweepAssetKind.ERC20 and job.execution.token_contract:
            token_balance = getattr(self.adapter, "get_erc20_balance", None)
            if callable(token_balance):
                return int(await token_balance(job.execution.token_contract, address))
        return int(await self.adapter.get_native_balance(address))

    def required_fields(self, kind: TriggerKind) -> dict[str, type[Any]]:
        fields: dict[TriggerKind, dict[str, type[Any]]] = {
            TriggerKind.EVENT: {"event_name": str, "event_signature": str},
            TriggerKind.TIMESTAMP: {"timestamp": int},
            TriggerKind.BLOCK: {"block": int},
            TriggerKind.CLAIMABLE_FUNCTION: {"function_name": str},
            TriggerKind.BALANCE_CHANGE: {"address": str},
            TriggerKind.MANUAL: {},
        }
        return fields[kind]
