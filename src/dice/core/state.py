from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from dice.core.models import JobStatus


@dataclass(slots=True)
class JobRuntimeState:
    job_id: str
    status: JobStatus
    message: str = ""
    last_updated: datetime = field(default_factory=lambda: datetime.now(UTC))
    tx_hash: str | None = None

    def transition(self, status: JobStatus, message: str = "", tx_hash: str | None = None) -> None:
        self.status = status
        self.message = message
        self.tx_hash = tx_hash or self.tx_hash
        self.last_updated = datetime.now(UTC)

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "message": self.message,
            "last_updated": self.last_updated.isoformat(),
            "tx_hash": self.tx_hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JobRuntimeState":
        return cls(
            job_id=data["job_id"],
            status=JobStatus(data["status"]),
            message=data.get("message", ""),
            last_updated=datetime.fromisoformat(data["last_updated"]),
            tx_hash=data.get("tx_hash"),
        )
