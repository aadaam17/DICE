from __future__ import annotations

import asyncio
from dataclasses import dataclass
from collections.abc import Callable
from typing import Any, Protocol

from dice.adapters.base import ChainAdapter
from dice.core.amounts import decimals_for_asset, runtime_amount_to_units
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
    skipped: bool = False


@dataclass(slots=True)
class ActionContext:
    adapter: ChainAdapter
    builder: TransactionBuilder
    broadcaster: Broadcaster
    signer: PrivateKeySigner | None = None
    mark: Callable[[str], None] | None = None


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
        destination = str(action.params.get("destination") or job.wallet.destination)
        sweep_builder = getattr(context.adapter, "build_native_sweep_transfer", None)
        if callable(sweep_builder) and not _has_configured_amount(action, job):
            _mark(context, "building fast native sweep transaction")
            transaction = await sweep_builder(job, _signer_address(job, context), destination)
            amount = int(transaction.get("value", 0) or 0)
            _mark(context, f"fast native sweep amount resolved: {amount}")
            if amount <= 0:
                return ActionResult(action.kind, "Skipped native sweep because transferable amount is zero", skipped=True)
            if _below_minimum(job, amount):
                return ActionResult(
                    action.kind,
                    f"Skipped native sweep because amount {amount} is below minimum {job.execution.min_amount}",
                    skipped=True,
                )
            tx_hash = await _sign_and_broadcast_prebuilt(job, context, transaction)
            return ActionResult(action.kind, f"Swept native asset to {destination}", tx_hash)

        amount = await _amount_from_action_or_job(action, job, context, destination)
        if amount <= 0:
            return ActionResult(action.kind, "Skipped native transfer because amount is zero", skipped=True)
        if _below_minimum(job, amount):
            return ActionResult(
                action.kind,
                f"Skipped native transfer because amount {amount} is below minimum {job.execution.min_amount}",
                skipped=True,
            )
        builder = getattr(context.adapter, "build_native_transfer", None)
        if callable(builder):
            _mark(context, "building native transfer transaction")
            transaction = await builder(job, _signer_address(job, context), destination, amount)
            _mark(context, "native transfer transaction built")
            tx_hash = await _sign_and_broadcast_prebuilt(job, context, transaction)
            return ActionResult(action.kind, f"Transferred native asset to {destination}", tx_hash)
        tx_hash = await _broadcast_mock_action(job, action, context)
        return ActionResult(action.kind, f"Mock native transfer to {destination}", tx_hash)


class Erc20TransferAction:
    async def execute(self, job: JobConfig, action: ActionSpec, context: ActionContext) -> ActionResult:
        token = str(action.params.get("token_contract") or job.execution.token_contract or "")
        if not token:
            raise RuntimeError("transfer_erc20 requires token_contract")
        amount = await _amount_from_action_or_job(action, job, context)
        if amount <= 0:
            return ActionResult(action.kind, "Skipped ERC20 transfer because amount is zero", skipped=True)
        if _below_minimum(job, amount):
            return ActionResult(
                action.kind,
                f"Skipped ERC20 transfer because amount {amount} is below minimum {job.execution.min_amount}",
                skipped=True,
            )
        destination = str(action.params.get("destination") or job.wallet.destination)
        builder = getattr(context.adapter, "build_erc20_transfer", None)
        if callable(builder):
            _mark(context, "building ERC20 transfer transaction")
            transaction = await builder(job, _signer_address(job, context), token, destination, amount)
            _mark(context, "ERC20 transfer transaction built")
            tx_hash = await _sign_and_broadcast_prebuilt(
                job,
                context,
                transaction,
            )
            return ActionResult(action.kind, f"Transferred ERC20 to {destination}", tx_hash)
        tx_hash = await _broadcast_mock_action(job, action, context)
        return ActionResult(action.kind, f"Mock ERC20 transfer to {destination}", tx_hash)


class SweepAction:
    async def execute(self, job: JobConfig, action: ActionSpec, context: ActionContext) -> ActionResult:
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
        raise RuntimeError(f"Real {job.chain} execution requires a signer")
    if not job.wallet.private_key_ref:
        raise RuntimeError(f"Real {job.chain} execution requires a private_key_ref")
    _mark(context, "signing transaction")
    signed = context.signer.sign_transaction(transaction, job.wallet.private_key_ref)
    _mark(context, "transaction signed")
    _mark(context, "broadcasting transaction")
    tx_hash = await context.adapter.broadcast(signed.raw_transaction)
    _mark(context, "transaction broadcast accepted")
    return tx_hash


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
        raise RuntimeError(f"Real {job.chain} execution requires a signer")
    if not job.wallet.private_key_ref:
        raise RuntimeError(f"Real {job.chain} execution requires a private_key_ref")
    if job.chain == "solana":
        return context.signer.solana_address_for_ref(job.wallet.private_key_ref)
    return context.signer.address_for_ref(job.wallet.private_key_ref)


async def _amount_from_action_or_job(
    action: ActionSpec,
    job: JobConfig,
    context: ActionContext,
    destination: str | None = None,
) -> int:
    value = action.params.get("amount")
    if value is None and job.execution.arguments:
        value = job.execution.arguments[-1]
    if value in (None, ""):
        return await _balance_amount_for_job(job, context, destination)
    decimals = await _decimals_for_job(job, context)
    amount = runtime_amount_to_units(value, decimals)
    _mark(context, f"configured amount converted: {amount}")
    return amount


async def _balance_amount_for_job(
    job: JobConfig,
    context: ActionContext,
    destination: str | None = None,
) -> int:
    source = _source_address(job, context)
    _mark(context, "reading sweep balance")
    if job.execution.asset_kind == SweepAssetKind.ERC20:
        if not job.execution.token_contract:
            raise RuntimeError("ERC20 sweep requires token_contract")
        balance_getter = getattr(context.adapter, "get_erc20_balance", None)
        if not callable(balance_getter):
            raise RuntimeError("This adapter cannot read ERC20 balances")
        balance = int(await balance_getter(job.execution.token_contract, source))
        _mark(context, f"ERC20 sweep balance resolved: {balance}")
        return balance

    transferable_getter = getattr(context.adapter, "get_native_transferable_balance", None)
    if callable(transferable_getter) and destination:
        balance = int(await transferable_getter(job, source, destination))
        _mark(context, f"native transferable balance resolved: {balance}")
        return balance
    balance_getter = getattr(context.adapter, "get_native_balance", None)
    if not callable(balance_getter):
        raise RuntimeError("This adapter cannot read native balances")
    balance = int(await balance_getter(source))
    _mark(context, f"native balance resolved: {balance}")
    return balance


def _source_address(job: JobConfig, context: ActionContext) -> str:
    if context.signer and job.wallet.private_key_ref:
        return _signer_address(job, context)
    trigger_address = job.trigger.params.get("address")
    if trigger_address:
        return str(trigger_address)
    return job.wallet.address


async def _decimals_for_job(job: JobConfig, context: ActionContext) -> int:
    if job.execution.asset_kind == SweepAssetKind.ERC20 and job.execution.token_contract:
        decimals_getter = getattr(context.adapter, "get_erc20_decimals", None)
        if callable(decimals_getter):
            decimals = int(await decimals_getter(job.execution.token_contract))
            _mark(context, f"ERC20 decimals resolved from token contract: {decimals}")
            return decimals
    decimals = decimals_for_asset(
        job.execution.asset_kind,
        job.execution.token_symbol,
        job.execution.token_decimals,
        job.chain,
    )
    _mark(context, f"asset decimals resolved: {decimals}")
    return decimals


def _below_minimum(job: JobConfig, amount: int) -> bool:
    return job.execution.min_amount is not None and amount < job.execution.min_amount


def _has_configured_amount(action: ActionSpec, job: JobConfig) -> bool:
    return action.params.get("amount") not in (None, "") or bool(job.execution.arguments)


def _mark(context: ActionContext, message: str) -> None:
    if context.mark is not None:
        context.mark(message)
