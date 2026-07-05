from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path


class JobLogStore:
    def __init__(self, root: Path = Path("logs")) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def append(self, job_id: str, message: str) -> str:
        line = f"{datetime.now(UTC).isoformat()} {message}"
        self._path(job_id).open("a", encoding="utf-8").write(line + "\n")
        return line

    def read(self, job_id: str, limit: int = 200) -> list[str]:
        path = self._path(job_id)
        if not path.exists():
            return []
        lines = path.read_text(encoding="utf-8").splitlines()
        return lines[-limit:]

    def delete(self, job_id: str) -> None:
        self._path(job_id).unlink(missing_ok=True)

    def _path(self, job_id: str) -> Path:
        return self.root / f"{job_id}.log"
