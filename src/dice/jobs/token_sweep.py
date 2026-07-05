from __future__ import annotations

from dice.core.registry import register_job
from dice.core.workflow import WorkflowActionKind, WorkflowSpec, WorkflowTriggerKind
from dice.jobs.base import JobPlugin
from dice.jobs.templates import metadata, workflow


@register_job
class TokenSweepJob(JobPlugin):
    @classmethod
    def metadata(cls):
        return metadata(
            "token_sweep",
            "Token Sweep",
            "Transfer ERC20 tokens when a watched wallet receives them.",
            [WorkflowTriggerKind.WALLET_CHANGE],
            [WorkflowActionKind.TRANSFER_ERC20],
        )

    @classmethod
    def default_workflow(cls) -> WorkflowSpec:
        return workflow(WorkflowTriggerKind.WALLET_CHANGE, [WorkflowActionKind.TRANSFER_ERC20])
