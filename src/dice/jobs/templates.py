from __future__ import annotations

from dice.core.registry import JobTypeMetadata
from dice.core.workflow import ActionSpec, TriggerSpec, WorkflowActionKind, WorkflowSpec, WorkflowTriggerKind


def metadata(
    key: str,
    name: str,
    description: str,
    triggers: list[WorkflowTriggerKind],
    actions: list[WorkflowActionKind],
) -> JobTypeMetadata:
    return JobTypeMetadata(
        key=key,
        name=name,
        description=description,
        trigger_kinds=[trigger.value for trigger in triggers],
        action_kinds=[action.value for action in actions],
    )


def workflow(trigger: WorkflowTriggerKind, actions: list[WorkflowActionKind]) -> WorkflowSpec:
    return WorkflowSpec(
        trigger=TriggerSpec(kind=trigger),
        actions=[ActionSpec(kind=action) for action in actions],
    )
