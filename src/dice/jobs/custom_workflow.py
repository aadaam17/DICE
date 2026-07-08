from __future__ import annotations

from dice.core.registry import register_job
from dice.core.workflow import ActionSpec, TriggerSpec, WorkflowActionKind, WorkflowSpec, WorkflowTriggerKind
from dice.jobs.base import JobPlugin
from dice.jobs.templates import field, metadata


@register_job
class CustomWorkflowJob(JobPlugin):
    @classmethod
    def metadata(cls):
        return metadata(
            "custom_workflow",
            "Custom Workflow",
            "Chain reusable triggers and actions into a custom automation.",
            [
                WorkflowTriggerKind.BLOCK,
                WorkflowTriggerKind.EVENT,
                WorkflowTriggerKind.TIME,
                WorkflowTriggerKind.WALLET_CHANGE,
                WorkflowTriggerKind.BALANCE,
                WorkflowTriggerKind.FUNCTION_RESULT,
                WorkflowTriggerKind.MANUAL,
            ],
            [
                WorkflowActionKind.TRANSFER_NATIVE,
                WorkflowActionKind.TRANSFER_ERC20,
                WorkflowActionKind.CALL_CONTRACT,
                WorkflowActionKind.WAIT,
                WorkflowActionKind.NOTIFY,
                WorkflowActionKind.RUN_WORKFLOW,
                WorkflowActionKind.WITHDRAW,
                WorkflowActionKind.SWAP,
                WorkflowActionKind.BRIDGE,
            ],
            [
                field("trigger_kind", "Trigger", "trigger", "manual"),
                field("function_name", "Primary action", "execution", "notify"),
                field("arguments", "Action arguments", "execution", "message, value"),
            ],
        )

    @classmethod
    def default_workflow(cls) -> WorkflowSpec:
        return WorkflowSpec(
            trigger=TriggerSpec(kind=WorkflowTriggerKind.MANUAL),
            actions=[ActionSpec(kind=WorkflowActionKind.NOTIFY)],
        )
