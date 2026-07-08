from __future__ import annotations

from dice.core.registry import register_job
from dice.core.workflow import WorkflowActionKind, WorkflowSpec, WorkflowTriggerKind
from dice.jobs.base import JobPlugin
from dice.jobs.templates import field, metadata, workflow


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
            [
                field("wallet_address", "Watched wallet", "wallet", "0xWalletToWatch", True),
                field("trigger_kind", "Watch trigger", "trigger", "balance_change"),
                field("trigger_param_1", "Address", "trigger", "0xWalletToWatch", True),
                field("function_name", "Action", "execution", "notify"),
            ],
        )

    @classmethod
    def default_workflow(cls) -> WorkflowSpec:
        return workflow(WorkflowTriggerKind.WALLET_CHANGE, [WorkflowActionKind.NOTIFY])
