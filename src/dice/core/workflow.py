from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class WorkflowTriggerKind(StrEnum):
    BLOCK = "block"
    EVENT = "event"
    TIME = "time"
    WALLET_CHANGE = "wallet_change"
    BALANCE = "balance"
    FUNCTION_RESULT = "function_result"
    MANUAL = "manual"


class WorkflowActionKind(StrEnum):
    TRANSFER_NATIVE = "transfer_native"
    TRANSFER_ERC20 = "transfer_erc20"
    CALL_CONTRACT = "call_contract"
    WAIT = "wait"
    NOTIFY = "notify"
    RUN_WORKFLOW = "run_workflow"
    WITHDRAW = "withdraw"
    SWEEP = "sweep"
    SWAP = "swap"
    BRIDGE = "bridge"


@dataclass(slots=True)
class TriggerSpec:
    kind: WorkflowTriggerKind
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind.value, "params": self.params}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TriggerSpec":
        return cls(kind=WorkflowTriggerKind(data["kind"]), params=data.get("params", {}))


@dataclass(slots=True)
class ConditionSpec:
    field: str
    operator: str
    value: Any

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConditionSpec":
        return cls(field=data["field"], operator=data["operator"], value=data.get("value"))


@dataclass(slots=True)
class ActionSpec:
    kind: WorkflowActionKind
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind.value, "params": self.params}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ActionSpec":
        return cls(kind=WorkflowActionKind(data["kind"]), params=data.get("params", {}))


@dataclass(slots=True)
class WorkflowSpec:
    trigger: TriggerSpec
    actions: list[ActionSpec]
    conditions: list[ConditionSpec] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trigger": self.trigger.to_dict(),
            "conditions": [condition.to_dict() for condition in self.conditions],
            "actions": [action.to_dict() for action in self.actions],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkflowSpec":
        return cls(
            trigger=TriggerSpec.from_dict(data["trigger"]),
            conditions=[ConditionSpec.from_dict(item) for item in data.get("conditions", [])],
            actions=[ActionSpec.from_dict(item) for item in data.get("actions", [])],
        )


class WorkflowEngine:
    """Generic sequential workflow executor.

    Concrete blockchain action handlers can be injected later. For now, this engine
    provides a stable abstraction and validation surface for workflow plugins.
    """

    def validate(self, workflow: WorkflowSpec) -> list[str]:
        errors: list[str] = []
        if not workflow.actions:
            errors.append("Workflow requires at least one action")
        for action in workflow.actions:
            if action.kind == WorkflowActionKind.CALL_CONTRACT and not action.params.get("function_name"):
                errors.append("call_contract action requires function_name")
        return errors

    async def execute(self, workflow: WorkflowSpec) -> list[str]:
        events: list[str] = []
        for action in workflow.actions:
            events.append(f"action:{action.kind.value}")
        return events
