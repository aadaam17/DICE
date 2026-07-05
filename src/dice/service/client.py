from __future__ import annotations

import asyncio
import json
import socket
from collections.abc import Callable
from typing import Any

from dice.core.models import JobConfig
from dice.core.state import JobRuntimeState

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765

StateListener = Callable[[JobRuntimeState], None]


class ServiceUnavailableError(ConnectionError):
    """Raised when the daemon control socket is unavailable."""


class ServiceClient:
    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, timeout: float = 20.0) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout

    def ping(self) -> bool:
        response = self.request("ping")
        return response.get("ok") is True

    def status(self) -> dict[str, Any]:
        return self.request("status")

    def list_jobs(self) -> dict[str, Any]:
        return self.request("list_jobs")

    def list_job_types(self) -> list[dict[str, object]]:
        response = self.request("list_job_types")
        return list(response.get("job_types", []))

    def create_job(self, job: JobConfig) -> dict[str, Any]:
        return self.request("create_job", job=job.to_dict())

    def import_private_key(self, job_id: str, label: str, private_key: str) -> str:
        response = self.request(
            "import_private_key",
            job_id=job_id,
            label=label,
            private_key=private_key,
        )
        return str(response["private_key_ref"])

    def next_job_id(self) -> str:
        try:
            response = self.request("next_job_id")
            return str(response["job_id"])
        except RuntimeError as exc:
            if "Unknown command: next_job_id" not in str(exc):
                raise
            return self._next_job_id_from_snapshot()

    def start_job(self, job_id: str) -> dict[str, Any]:
        return self.request("start_job", job_id=job_id)

    def preflight_job(self, job_id: str) -> dict[str, Any]:
        response = self.request("preflight_job", job_id=job_id)
        return dict(response["report"])

    def stop_job(self, job_id: str) -> dict[str, Any]:
        return self.request("stop_job", job_id=job_id)

    def delete_job(self, job_id: str) -> dict[str, Any]:
        return self.request("delete_job", job_id=job_id)

    def get_logs(self, job_id: str) -> list[str]:
        response = self.request("get_logs", job_id=job_id)
        return list(response.get("logs", []))

    def request(self, command: str, **payload: Any) -> dict[str, Any]:
        message = {"command": command, **payload}
        try:
            with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
                file = sock.makefile("rwb")
                file.write(json.dumps(message).encode("utf-8") + b"\n")
                file.flush()
                raw = file.readline()
        except OSError as exc:
            raise ServiceUnavailableError(str(exc)) from exc

        if not raw:
            raise ServiceUnavailableError("DICE daemon closed the connection without a response")

        response = json.loads(raw.decode("utf-8"))
        if response.get("ok") is False:
            raise RuntimeError(response.get("error", "DICE daemon request failed"))
        return response

    def _next_job_id_from_snapshot(self) -> str:
        snapshot = self.list_jobs()
        numbers: list[int] = []
        for job in snapshot.get("jobs", []):
            job_id = str(job.get("id", ""))
            if job_id.startswith("job-"):
                try:
                    numbers.append(int(job_id.split("-", maxsplit=1)[1]))
                except ValueError:
                    continue
        return f"job-{max(numbers, default=0) + 1:04d}"


class RemoteJobManager:
    """TUI-facing adapter that makes the daemon look like a local JobManager."""

    is_remote = True

    def __init__(self, client: ServiceClient | None = None) -> None:
        self.client = client or ServiceClient()
        self.jobs: dict[str, JobConfig] = {}
        self.states: dict[str, JobRuntimeState] = {}
        self._listeners: list[StateListener] = []

    def add_listener(self, listener: StateListener) -> None:
        self._listeners.append(listener)

    def load_jobs(self) -> list[JobConfig]:
        response = self.client.list_jobs()
        jobs = [JobConfig.from_dict(item) for item in response.get("jobs", [])]
        states = [JobRuntimeState.from_dict(item) for item in response.get("states", [])]
        self.jobs = {job.id: job for job in jobs}
        self.states = {state.job_id: state for state in states}
        return jobs

    def available_job_types(self) -> list[dict[str, object]]:
        return self.client.list_job_types()

    def create_job(self, job: JobConfig) -> JobConfig:
        self.client.create_job(job)
        self.load_jobs()
        self._publish()
        return job

    def import_private_key(self, job_id: str, label: str, private_key: str) -> str:
        return self.client.import_private_key(job_id, label, private_key)

    def next_id(self) -> str:
        return self.client.next_job_id()

    async def start(self, job_id: str) -> None:
        await asyncio.to_thread(self.client.start_job, job_id)
        await asyncio.to_thread(self.load_jobs)
        self._publish()

    async def preflight(self, job_id: str) -> dict[str, Any]:
        return await asyncio.to_thread(self.client.preflight_job, job_id)

    async def stop(self, job_id: str) -> None:
        await asyncio.to_thread(self.client.stop_job, job_id)
        await asyncio.to_thread(self.load_jobs)
        self._publish()

    async def delete(self, job_id: str) -> None:
        await asyncio.to_thread(self.client.delete_job, job_id)
        await asyncio.to_thread(self.load_jobs)
        self._publish()

    def get_logs(self, job_id: str) -> list[str]:
        return self.client.get_logs(job_id)

    async def stop_all(self) -> None:
        return None

    def _publish(self) -> None:
        for state in self.states.values():
            for listener in self._listeners:
                listener(state)


def service_is_available(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> bool:
    try:
        return ServiceClient(host, port, timeout=0.5).ping()
    except (RuntimeError, ServiceUnavailableError):
        return False
