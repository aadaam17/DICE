from __future__ import annotations

from dice.core.registry import register_job
from dice.core.workflow import WorkflowActionKind, WorkflowSpec, WorkflowTriggerKind
from dice.jobs.base import JobPlugin
from dice.jobs.templates import metadata, workflow


@register_job
class EventTriggerJob(JobPlugin):
    @classmethod
    def metadata(cls):
        return metadata(
            "event_trigger",
            "Event Trigger",
            "Subscribe to contract events and execute actions when they fire.",
            [WorkflowTriggerKind.EVENT],
            [WorkflowActionKind.CALL_CONTRACT, WorkflowActionKind.TRANSFER_NATIVE, WorkflowActionKind.NOTIFY],
        )

    @classmethod
    def default_workflow(cls) -> WorkflowSpec:
        return workflow(WorkflowTriggerKind.EVENT, [WorkflowActionKind.CALL_CONTRACT])
