from __future__ import annotations

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

    async def execute(self, job: JobConfig) -> str:
        if job.workflow and job.workflow.actions:
            context = ActionContext(
                adapter=self.adapter,
                signer=self.signer,
                builder=self.builder,
                broadcaster=self.broadcaster,
            )
            results = await self.dispatcher.execute(job, job.workflow.actions, context)
            for result in reversed(results):
                if result.tx_hash:
                    return result.tx_hash
            return "no-transaction"

        if hasattr(self.adapter, "build_transaction"):
            if self.signer is None:
                raise RuntimeError("Real EVM execution requires a signer")
            if not job.wallet.private_key_ref:
                raise RuntimeError("Real EVM execution requires a private_key_ref")
            signer_address = self.signer.address_for_ref(job.wallet.private_key_ref)
            transaction = await self.adapter.build_transaction(job, signer_address)  # type: ignore[attr-defined]
            signed = self.signer.sign_transaction(transaction, job.wallet.private_key_ref)
            return await self.adapter.broadcast(signed.raw_transaction)

        gas_limit = await self.adapter.estimate_gas(
            {
                "contract": job.contract.address if job.contract else None,
                "function": job.execution.function_name,
                "arguments": job.execution.arguments,
            }
        )
        payload = await self.builder.build(job, gas_limit)
        return await self.broadcaster.broadcast(payload)
