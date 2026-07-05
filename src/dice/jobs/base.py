from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from dice.core.models import JobConfig, JobStatus
from dice.core.registry import JobTypeMetadata
from dice.core.workflow import WorkflowSpec


@dataclass(slots=True)
class JobRuntime:
    status: JobStatus = JobStatus.CREATED
    message: str = ""


class JobPlugin(ABC):
    def __init__(self, config: JobConfig) -> None:
        self.config = config
        self.runtime = JobRuntime()

    @classmethod
    @abstractmethod
    def metadata(cls) -> JobTypeMetadata:
        """Return registry metadata for the plugin."""

    @classmethod
    @abstractmethod
    def default_workflow(cls) -> WorkflowSpec:
        """Return the default workflow template for this plugin."""

    def validate(self) -> list[str]:
        if self.config.workflow is None:
            return ["Job requires a workflow"]
        return []

    async def start(self) -> None:
        self.runtime.status = JobStatus.RUNNING

    async def stop(self) -> None:
        self.runtime.status = JobStatus.STOPPED

    async def pause(self) -> None:
        self.runtime.status = JobStatus.STOPPED
        self.runtime.message = "Paused"

    async def resume(self) -> None:
        self.runtime.status = JobStatus.RUNNING
        self.runtime.message = "Resumed"

    async def execute(self) -> None:
        self.runtime.status = JobStatus.COMPLETED

    def serialize(self) -> dict[str, Any]:
        return self.config.to_dict()

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> "JobPlugin":
        return cls(JobConfig.from_dict(data))

    def status(self) -> JobRuntime:
        return self.runtime
