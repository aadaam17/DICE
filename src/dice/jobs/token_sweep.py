from __future__ import annotations

from dice.core.registry import register_job
from dice.core.workflow import WorkflowActionKind, WorkflowSpec, WorkflowTriggerKind
from dice.jobs.base import JobPlugin
from dice.jobs.templates import field, metadata, workflow


@register_job
class TokenSweepJob(JobPlugin):
    @classmethod
    def metadata(cls):
        return metadata(
            "token_sweep",
            "Token Sweep",
            "Transfer EVM ERC20 or Solana SPL tokens when a watched wallet receives them.",
            [WorkflowTriggerKind.WALLET_CHANGE],
            [WorkflowActionKind.TRANSFER_ERC20],
            [
                field("token_contract", "Token contract or mint", "asset", "0xTokenContractOrSolanaMint", True),
                field("token_symbol", "Token symbol", "asset", "USDC"),
                field("token_decimals", "Token decimals", "asset", "6"),
                field("destination", "Destination", "wallet", "0xColdWallet", True),
                field("trigger_kind", "Trigger", "trigger", "balance_change"),
                field("function_name", "Function", "execution", "transfer"),
                field("arguments", "Amount", "execution", "1"),
                field("min_amount", "Minimum sweep amount", "execution", "1"),
            ],
        )

    @classmethod
    def default_workflow(cls) -> WorkflowSpec:
        return workflow(WorkflowTriggerKind.WALLET_CHANGE, [WorkflowActionKind.TRANSFER_ERC20])
