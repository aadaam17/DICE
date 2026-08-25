from __future__ import annotations

from collections.abc import Callable

from dice.adapters.base import ChainAdapter
from dice.core.models import JobConfig
from dice.core.secrets import SecretStore
from dice.execution.actions import ActionContext, WorkflowActionDispatcher
from dice.execution.broadcaster import Broadcaster
from dice.execution.builder import TransactionBuilder
from dice.execution.signer import PrivateKeySigner


class ExecutionEngine:
    def __init__(self, adapter: ChainAdapter, secret_store: SecretStore | None = None) -> None:
        self.adapter = adapter
        self.signer = PrivateKeySigner(secret_store) if secret_store else None
        self.builder = TransactionBuilder()
        self.broadcaster = Broadcaster(adapter)
        self.dispatcher = WorkflowActionDispatcher()

    async def execute(self, job: JobConfig, mark: Callable[[str], None] | None = None) -> str:
        if job.workflow and job.workflow.actions:
            context = ActionContext(
                adapter=self.adapter,
                signer=self.signer,
                builder=self.builder,
                broadcaster=self.broadcaster,
                mark=mark,
            )
            if mark:
                mark("workflow action dispatch started")
            results = await self.dispatcher.execute(job, job.workflow.actions, context)
            if mark:
                mark("workflow action dispatch finished")
            for result in reversed(results):
                if result.tx_hash:
                    return result.tx_hash
            return "no-transaction"

        if hasattr(self.adapter, "build_transaction"):
            if self.signer is None:
                raise RuntimeError(f"Real {job.chain} execution requires a signer")
            if not job.wallet.private_key_ref:
                raise RuntimeError(f"Real {job.chain} execution requires a private_key_ref")
            signer_address = self.signer.address_for_ref(job.wallet.private_key_ref)
            if mark:
                mark("building contract transaction")
            transaction = await self.adapter.build_transaction(job, signer_address)  # type: ignore[attr-defined]
            if mark:
                mark("contract transaction built")
                mark("signing transaction")
            signed = self.signer.sign_transaction(transaction, job.wallet.private_key_ref)
            if mark:
                mark("transaction signed")
                mark("broadcasting transaction")
            tx_hash = await self.adapter.broadcast(signed.raw_transaction)
            if mark:
                mark("transaction broadcast accepted")
            return tx_hash

        if mark:
            mark("estimating mock gas")
        gas_limit = await self.adapter.estimate_gas(
            {
                "contract": job.contract.address if job.contract else None,
                "function": job.execution.function_name,
                "arguments": job.execution.arguments,
            }
        )
        if mark:
            mark("mock gas estimated")
        payload = await self.builder.build(job, gas_limit)
        if mark:
            mark("mock payload built")
        tx_hash = await self.broadcaster.broadcast(payload)
        if mark:
            mark("mock transaction broadcast")
        return tx_hash
