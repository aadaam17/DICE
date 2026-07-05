from __future__ import annotations

from dice.core.registry import register_job
from dice.core.workflow import WorkflowActionKind, WorkflowSpec, WorkflowTriggerKind
from dice.jobs.base import JobPlugin
from dice.jobs.templates import metadata, workflow


@register_job
class ScheduledTransferJob(JobPlugin):
    @classmethod
    def metadata(cls):
        return metadata(
            "scheduled_transfer",
            "Scheduled Transfer",
            "Execute transfers once or on a recurring time schedule.",
            [WorkflowTriggerKind.TIME],
            [WorkflowActionKind.TRANSFER_NATIVE, WorkflowActionKind.TRANSFER_ERC20],
        )

    @classmethod
    def default_workflow(cls) -> WorkflowSpec:
        return workflow(WorkflowTriggerKind.TIME, [WorkflowActionKind.TRANSFER_NATIVE])
