from __future__ import annotations

from dice.core.registry import register_job
from dice.core.workflow import WorkflowActionKind, WorkflowSpec, WorkflowTriggerKind
from dice.jobs.base import JobPlugin
from dice.jobs.templates import metadata, workflow


@register_job
class WalletWatchJob(JobPlugin):
    @classmethod
    def metadata(cls):
        return metadata(
            "wallet_watch",
            "Wallet Watch",
            "Monitor wallet activity and trigger notifications or workflows.",
            [WorkflowTriggerKind.WALLET_CHANGE, WorkflowTriggerKind.BALANCE],
            [WorkflowActionKind.NOTIFY, WorkflowActionKind.RUN_WORKFLOW],
        )

    @classmethod
    def default_workflow(cls) -> WorkflowSpec:
        return workflow(WorkflowTriggerKind.WALLET_CHANGE, [WorkflowActionKind.NOTIFY])
