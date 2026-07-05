from __future__ import annotations

from dice.core.registry import register_job
from dice.core.workflow import WorkflowActionKind, WorkflowSpec, WorkflowTriggerKind
from dice.jobs.base import JobPlugin
from dice.jobs.templates import metadata, workflow


@register_job
class StakeSweepJob(JobPlugin):
    @classmethod
    def metadata(cls):
        return metadata(
            key="stake_sweep",
            name="Stake Sweep",
            description="Watch staking unlocks, withdraw, then optionally sweep funds.",
            triggers=[
                WorkflowTriggerKind.EVENT,
                WorkflowTriggerKind.TIME,
                WorkflowTriggerKind.BLOCK,
                WorkflowTriggerKind.FUNCTION_RESULT,
            ],
            actions=[WorkflowActionKind.WITHDRAW, WorkflowActionKind.SWEEP],
        )

    @classmethod
    def default_workflow(cls) -> WorkflowSpec:
        return workflow(WorkflowTriggerKind.FUNCTION_RESULT, [WorkflowActionKind.WITHDRAW, WorkflowActionKind.SWEEP])
