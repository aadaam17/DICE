from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Protocol

from dice.adapters.base import ChainAdapter
from dice.core.models import JobConfig, SweepAssetKind
from dice.core.workflow import ActionSpec, WorkflowActionKind
from dice.execution.broadcaster import Broadcaster
from dice.execution.builder import TransactionBuilder
from dice.execution.signer import PrivateKeySigner


@dataclass(frozen=True, slots=True)
class ActionResult:
    action: WorkflowActionKind
    message: str
    tx_hash: str | None = None


@dataclass(slots=True)
class ActionContext:
    adapter: ChainAdapter
    builder: TransactionBuilder
    broadcaster: Broadcaster
    signer: PrivateKeySigner | None = None


class ActionHandler(Protocol):
    async def execute(self, job: JobConfig, action: ActionSpec, context: ActionContext) -> ActionResult:
        """Execute a workflow action."""


class WorkflowActionDispatcher:
    def __init__(self) -> None:
        self.handlers: dict[WorkflowActionKind, ActionHandler] = {
            WorkflowActionKind.CALL_CONTRACT: ContractCallAction(),
            WorkflowActionKind.WITHDRAW: ContractCallAction(),
            WorkflowActionKind.TRANSFER_NATIVE: NativeTransferAction(),
            WorkflowActionKind.TRANSFER_ERC20: Erc20TransferAction(),
            WorkflowActionKind.SWEEP: SweepAction(),
            WorkflowActionKind.WAIT: WaitAction(),
            WorkflowActionKind.NOTIFY: NotifyAction(),
            WorkflowActionKind.RUN_WORKFLOW: NotifyAction(),
        }

    async def execute(
        self,
        job: JobConfig,
        actions: list[ActionSpec],
        context: ActionContext,
    ) -> list[ActionResult]:
        results: list[ActionResult] = []
        for action in actions:
            handler = self.handlers.get(action.kind)
            if handler is None:
                raise RuntimeError(f"No action handler registered for {action.kind.value}")
            results.append(await handler.execute(job, action, context))
        return results


class ContractCallAction:
    async def execute(self, job: JobConfig, action: ActionSpec, context: ActionContext) -> ActionResult:
        if hasattr(context.adapter, "build_transaction"):
            tx_hash = await _sign_and_broadcast_contract_call(job, context)
            return ActionResult(action.kind, f"Broadcast {job.execution.function_name}", tx_hash)
        tx_hash = await _broadcast_mock_action(job, action, context)
        return ActionResult(action.kind, f"Mock {job.execution.function_name}", tx_hash)


class NativeTransferAction:
    async def execute(self, job: JobConfig, action: ActionSpec, context: ActionContext) -> ActionResult:
        amount = _amount_from_action_or_job(action, job)
        destination = str(action.params.get("destination") or job.wallet.destination)
        builder = getattr(context.adapter, "build_native_transfer", None)
        if callable(builder):
            tx_hash = await _sign_and_broadcast_prebuilt(job, context, await builder(job, _signer_address(job, context), destination, amount))
            return ActionResult(action.kind, f"Transferred native asset to {destination}", tx_hash)
        tx_hash = await _broadcast_mock_action(job, action, context)
        return ActionResult(action.kind, f"Mock native transfer to {destination}", tx_hash)


class Erc20TransferAction:
    async def execute(self, job: JobConfig, action: ActionSpec, context: ActionContext) -> ActionResult:
        token = str(action.params.get("token_contract") or job.execution.token_contract or "")
        if not token:
            raise RuntimeError("transfer_erc20 requires token_contract")
        amount = _amount_from_action_or_job(action, job)
        destination = str(action.params.get("destination") or job.wallet.destination)
        builder = getattr(context.adapter, "build_erc20_transfer", None)
        if callable(builder):
            tx_hash = await _sign_and_broadcast_prebuilt(
                job,
                context,
                await builder(job, _signer_address(job, context), token, destination, amount),
            )
            return ActionResult(action.kind, f"Transferred ERC20 to {destination}", tx_hash)
        tx_hash = await _broadcast_mock_action(job, action, context)
        return ActionResult(action.kind, f"Mock ERC20 transfer to {destination}", tx_hash)


class SweepAction:
    async def execute(self, job: JobConfig, action: ActionSpec, context: ActionContext) -> ActionResult:
        if not action.params.get("amount") and not job.execution.arguments:
            return ActionResult(action.kind, "Sweep skipped because no amount was configured")
        if job.execution.asset_kind == SweepAssetKind.ERC20:
            return await Erc20TransferAction().execute(job, action, context)
        return await NativeTransferAction().execute(job, action, context)


class WaitAction:
    async def execute(self, job: JobConfig, action: ActionSpec, context: ActionContext) -> ActionResult:
        seconds = int(action.params.get("seconds", 0) or 0)
        if seconds > 0:
            await asyncio.sleep(seconds)
        return ActionResult(action.kind, f"Waited {seconds} second(s)")


class NotifyAction:
    async def execute(self, job: JobConfig, action: ActionSpec, context: ActionContext) -> ActionResult:
        message = str(action.params.get("message") or f"{job.name}: {action.kind.value}")
        return ActionResult(action.kind, message)


async def _sign_and_broadcast_contract_call(job: JobConfig, context: ActionContext) -> str:
    signer_address = _signer_address(job, context)
    transaction = await context.adapter.build_transaction(job, signer_address)  # type: ignore[attr-defined]
    return await _sign_and_broadcast_prebuilt(job, context, transaction)


async def _sign_and_broadcast_prebuilt(
    job: JobConfig,
    context: ActionContext,
    transaction: dict[str, Any],
) -> str:
    if context.signer is None:
        raise RuntimeError("Real EVM execution requires a signer")
    if not job.wallet.private_key_ref:
        raise RuntimeError("Real EVM execution requires a private_key_ref")
    signed = context.signer.sign_transaction(transaction, job.wallet.private_key_ref)
    return await context.adapter.broadcast(signed.raw_transaction)


async def _broadcast_mock_action(
    job: JobConfig,
    action: ActionSpec,
    context: ActionContext,
) -> str:
    gas_limit = await context.adapter.estimate_gas(
        {
            "action": action.kind.value,
            "contract": job.contract.address if job.contract else None,
            "function": job.execution.function_name,
            "arguments": job.execution.arguments,
            "params": action.params,
        }
    )
    payload = await context.builder.build(job, gas_limit)
    return await context.broadcaster.broadcast(payload)


def _signer_address(job: JobConfig, context: ActionContext) -> str:
    if context.signer is None:
        raise RuntimeError("Real EVM execution requires a signer")
    if not job.wallet.private_key_ref:
        raise RuntimeError("Real EVM execution requires a private_key_ref")
    return context.signer.address_for_ref(job.wallet.private_key_ref)


def _amount_from_action_or_job(action: ActionSpec, job: JobConfig) -> int:
    value = action.params.get("amount")
    if value is None and job.execution.arguments:
        value = job.execution.arguments[-1]
    if value in (None, ""):
        raise RuntimeError(f"{action.kind.value} requires an amount argument")
    return int(value)
