from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from dice.adapters.base import ChainAdapter
from dice.core.models import TriggerConfig, TriggerKind


class TriggerEvaluator:
    def __init__(self, adapter: ChainAdapter) -> None:
        self.adapter = adapter

    async def should_execute(self, trigger: TriggerConfig) -> bool:
        if trigger.kind == TriggerKind.MANUAL:
            return True
        if trigger.kind == TriggerKind.TIMESTAMP:
            timestamp = int(trigger.params["timestamp"])
            return datetime.now(UTC).timestamp() >= timestamp
        if trigger.kind == TriggerKind.BLOCK:
            target_block = int(trigger.params["block"])
            return await self.adapter.latest_block() >= target_block
        return False

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
