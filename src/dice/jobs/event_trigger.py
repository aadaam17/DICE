from __future__ import annotations

from dice.core.registry import register_job
from dice.core.workflow import WorkflowActionKind, WorkflowSpec, WorkflowTriggerKind
from dice.jobs.base import JobPlugin
from dice.jobs.templates import field, metadata, workflow


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
            [
                field("contract_address", "Event contract", "contract", "0xEventContract", True),
                field("abi_path", "ABI path", "contract", "C:\\path\\to\\abi.json"),
                field("trigger_kind", "Trigger", "trigger", "event", True),
                field("trigger_param_1", "Event name", "trigger", "RewardUnlocked", True),
                field("trigger_param_2", "Event signature", "trigger", "RewardUnlocked(address,uint256)"),
                field("function_name", "Action function", "execution", "claimReward"),
            ],
        )

    @classmethod
    def default_workflow(cls) -> WorkflowSpec:
        return workflow(WorkflowTriggerKind.EVENT, [WorkflowActionKind.CALL_CONTRACT])
