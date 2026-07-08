from __future__ import annotations

import asyncio
from collections.abc import Callable

from dice.adapters.factory import create_adapter
from dice.core.logging import JobLogStore
from dice.core.models import JobConfig, JobStatus
from dice.core.preflight import PreflightReport, PreflightRunner, PreflightStatus
from dice.core.registry import JobTypeMetadata, load_builtin_plugins, registry
from dice.core.secrets import SecretStore, WalletSecret
from dice.core.state import JobRuntimeState
from dice.core.storage import JobStore
from dice.core.validation import ensure_valid_job
from dice.execution.executor import ExecutionEngine
from dice.watcher.runner import Watcher
from dice.watcher.triggers import TriggerEvaluator

StateListener = Callable[[JobRuntimeState], None]


class JobManager:
    def __init__(
        self,
        store: JobStore | None = None,
        log_store: JobLogStore | None = None,
        secret_store: SecretStore | None = None,
    ) -> None:
        self.store = store or JobStore()
        self.log_store = log_store or JobLogStore()
        self.secret_store = secret_store or SecretStore()
        self.jobs: dict[str, JobConfig] = {}
        self.states: dict[str, JobRuntimeState] = {}
        self.logs: dict[str, list[str]] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._listeners: list[StateListener] = []
        load_builtin_plugins()

    def add_listener(self, listener: StateListener) -> None:
        self._listeners.append(listener)

    def load_jobs(self) -> list[JobConfig]:
        self.jobs.clear()
        self.states.clear()
        for job in self.store.list_jobs():
            self.jobs[job.id] = job
            self.states[job.id] = JobRuntimeState(job.id, JobStatus.LOADED, "Loaded")
            self._log(job.id, "Loaded")
        return list(self.jobs.values())

    def next_id(self) -> str:
        return self.store.next_id()

    async def start_enabled(self) -> None:
        await asyncio.gather(
            *(self.start(job.id) for job in self.jobs.values() if job.enabled),
            return_exceptions=True,
        )

    def snapshot(self) -> dict[str, object]:
        return {
            "jobs": [job.to_dict() for job in sorted(self.jobs.values(), key=lambda item: item.id)],
            "states": [state.to_dict() for state in self.states.values()],
            "running": sorted(
                job_id for job_id, task in self._tasks.items() if not task.done()
            ),
            "job_types": [metadata.to_dict() for metadata in self.available_job_types()],
        }

    def create_job(self, job: JobConfig) -> JobConfig:
        validation = ensure_valid_job(job)
        plugin_type = registry.get(job.job_type)
        if job.workflow is None:
            job.workflow = plugin_type.default_workflow()
        plugin = plugin_type(job)
        plugin_errors = plugin.validate()
        if plugin_errors:
            from dice.core.validation import JobValidationError

            raise JobValidationError(plugin_errors)
        self.store.save(job)
        self.jobs[job.id] = job
        self.states[job.id] = JobRuntimeState(job.id, JobStatus.SAVED, "Saved")
        self._log(job.id, "Saved")
        for warning in validation.warnings:
            self._log(job.id, f"warning: {warning}")
        self._publish(job.id)
        return job

    def available_job_types(self) -> list[JobTypeMetadata]:
        return registry.list()

    def import_private_key(self, job_id: str, label: str, private_key: str) -> str:
        ref = self.secret_store.store_private_key(job_id, label, private_key)
        self._log(job_id, f"Imported private key as {ref}")
        return ref

    def import_wallet(self, wallet_id: str, label: str, address: str | None, private_key: str) -> str:
        return self.secret_store.store_wallet(wallet_id, label, address, private_key)

    def list_wallets(self) -> list[WalletSecret]:
        return self.secret_store.list_wallets()

    async def delete(self, job_id: str) -> None:
        if job_id not in self.jobs and job_id not in self.states:
            raise KeyError(f"Unknown job: {job_id}")
        private_key_ref = self.jobs[job_id].wallet.private_key_ref if job_id in self.jobs else None
        await self.stop(job_id)
        self.store.delete(job_id)
        self.jobs.pop(job_id, None)
        self.states.pop(job_id, None)
        self._tasks.pop(job_id, None)
        self.logs.pop(job_id, None)
        self.log_store.delete(job_id)
        if (
            private_key_ref
            and private_key_ref == f"secret://wallets/{job_id}"
            and not self._secret_ref_is_used(private_key_ref)
        ):
            self.secret_store.delete(private_key_ref)

    def get_logs(self, job_id: str) -> list[str]:
        stored = self.log_store.read(job_id)
        return stored or self.logs.get(job_id, [])

    async def preflight(self, job_id: str) -> PreflightReport:
        if job_id not in self.jobs:
            raise KeyError(f"Unknown job: {job_id}")
        report = await PreflightRunner(self.secret_store).run(self.jobs[job_id])
        for check in report.checks:
            self._log(job_id, f"preflight {check.status.value}: {check.name}: {check.message}")
        self._publish(job_id)
        return report

    async def start(self, job_id: str) -> None:
        if job_id not in self.jobs:
            raise KeyError(f"Unknown job: {job_id}")
        if job_id in self._tasks and not self._tasks[job_id].done():
            self._log(job_id, "Start requested but job is already running")
            return
        job = self.jobs[job_id]
        report = await self.preflight(job_id)
        if not report.ok:
            failures = [
                check.message for check in report.checks if check.status == PreflightStatus.FAIL
            ]
            self._transition(job_id, JobStatus.ERROR, "Preflight failed: " + "; ".join(failures))
            return
        self.states[job_id] = JobRuntimeState(job.id, JobStatus.RUNNING, "Starting")
        self._publish(job_id)
        self._tasks[job_id] = asyncio.create_task(self._run_job(job))

    async def stop(self, job_id: str) -> None:
        if job_id not in self.jobs and job_id not in self.states:
            return
        task = self._tasks.get(job_id)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._transition(job_id, JobStatus.STOPPED, "Stopped")

    async def stop_all(self) -> None:
        await asyncio.gather(*(self.stop(job_id) for job_id in list(self._tasks)), return_exceptions=True)

    async def _run_job(self, job: JobConfig) -> None:
        adapter = create_adapter(job)
        watcher = Watcher(TriggerEvaluator(adapter))
        executor = ExecutionEngine(adapter, self.secret_store)
        try:
            await adapter.connect()
            async for event in watcher.wait_until_triggered(job):
                if event == "waiting":
                    self._transition(job.id, JobStatus.WAITING, "Watching")
                if event == "triggered":
                    self._transition(job.id, JobStatus.TRIGGERED, "Trigger detected")
            self._transition(job.id, JobStatus.BROADCASTING, "Broadcasting")
            tx_hash = await executor.execute(job)
            self._transition(job.id, JobStatus.CONFIRMED, "Confirmed", tx_hash=tx_hash)
            self._transition(job.id, JobStatus.COMPLETED, "Completed", tx_hash=tx_hash)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self._transition(job.id, JobStatus.ERROR, str(exc))
        finally:
            await adapter.close()

    def _transition(
        self,
        job_id: str,
        status: JobStatus,
        message: str,
        tx_hash: str | None = None,
    ) -> None:
        state = self.states.setdefault(job_id, JobRuntimeState(job_id, status))
        state.transition(status, message, tx_hash)
        self._log(job_id, f"{status.value}: {message}")
        self._publish(job_id)

    def _publish(self, job_id: str) -> None:
        state = self.states[job_id]
        for listener in self._listeners:
            listener(state)

    def _log(self, job_id: str, message: str) -> None:
        line = self.log_store.append(job_id, message)
        self.logs.setdefault(job_id, []).append(line)

    def _secret_ref_is_used(self, private_key_ref: str) -> bool:
        return any(job.wallet.private_key_ref == private_key_ref for job in self.jobs.values())
