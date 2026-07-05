from __future__ import annotations

from dice.core.registry import register_job
from dice.core.workflow import WorkflowActionKind, WorkflowSpec, WorkflowTriggerKind
from dice.jobs.base import JobPlugin
from dice.jobs.templates import metadata, workflow


@register_job
class BalanceTriggerJob(JobPlugin):
    @classmethod
    def metadata(cls):
        return metadata(
            "balance_trigger",
            "Balance Trigger",
            "Run actions when a wallet balance crosses a condition.",
            [WorkflowTriggerKind.BALANCE],
            [WorkflowActionKind.TRANSFER_NATIVE, WorkflowActionKind.CALL_CONTRACT, WorkflowActionKind.NOTIFY],
        )

    @classmethod
    def default_workflow(cls) -> WorkflowSpec:
        return workflow(WorkflowTriggerKind.BALANCE, [WorkflowActionKind.NOTIFY])
