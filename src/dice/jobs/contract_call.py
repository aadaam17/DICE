from __future__ import annotations

from dice.core.registry import register_job
from dice.core.workflow import WorkflowActionKind, WorkflowSpec, WorkflowTriggerKind
from dice.jobs.base import JobPlugin
from dice.jobs.templates import field, metadata, workflow


@register_job
class ContractCallJob(JobPlugin):
    @classmethod
    def metadata(cls):
        return metadata(
            "contract_call",
            "Contract Call",
            "Execute a smart contract function directly or from a trigger.",
            [WorkflowTriggerKind.MANUAL, WorkflowTriggerKind.EVENT, WorkflowTriggerKind.TIME],
            [WorkflowActionKind.CALL_CONTRACT],
            [
                field("contract_address", "Contract address", "contract", "0xTargetContract", True),
                field("abi_path", "ABI path", "contract", "C:\\path\\to\\abi.json", True),
                field("function_name", "Function", "execution", "claim"),
                field("arguments", "Arguments", "execution", "poolId, recipient"),
                field("trigger_kind", "Trigger", "trigger", "manual"),
            ],
        )

    @classmethod
    def default_workflow(cls) -> WorkflowSpec:
        return workflow(WorkflowTriggerKind.MANUAL, [WorkflowActionKind.CALL_CONTRACT])
