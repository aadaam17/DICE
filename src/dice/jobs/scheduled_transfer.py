from __future__ import annotations

from dice.core.registry import register_job
from dice.core.workflow import WorkflowActionKind, WorkflowSpec, WorkflowTriggerKind
from dice.jobs.base import JobPlugin
from dice.jobs.templates import field, metadata, workflow


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
            [
                field("trigger_kind", "Schedule trigger", "trigger", "timestamp", True),
                field("trigger_param_1", "Unix timestamp", "trigger", "1767225600", True),
                field("destination", "Recipient", "wallet", "0xRecipient", True),
                field("asset_kind", "Asset", "asset", "native or erc20"),
                field("arguments", "Amount", "execution", "1000000000000000", True),
            ],
        )

    @classmethod
    def default_workflow(cls) -> WorkflowSpec:
        return workflow(WorkflowTriggerKind.TIME, [WorkflowActionKind.TRANSFER_NATIVE])
