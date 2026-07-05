from __future__ import annotations

import json
from pathlib import Path

from dice.core.models import JobConfig, JobStatus


class JobStore:
    def __init__(self, root: Path = Path("storage/jobs")) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def list_jobs(self) -> list[JobConfig]:
        jobs: list[JobConfig] = []
        for path in sorted(self.root.glob("*.json")):
            jobs.append(self.load(path.stem))
        return jobs

    def load(self, job_id: str) -> JobConfig:
        path = self._path(job_id)
        data = json.loads(path.read_text(encoding="utf-8"))
        job = JobConfig.from_dict(data)
        job.status = JobStatus.LOADED
        return job

    def save(self, job: JobConfig) -> None:
        job.status = JobStatus.SAVED
        path = self._path(job.id)
        temp_path = path.with_suffix(".json.tmp")
        temp_path.write_text(json.dumps(job.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
        temp_path.replace(path)

    def delete(self, job_id: str) -> None:
        self._path(job_id).unlink(missing_ok=True)

    def next_id(self) -> str:
        existing: list[int] = []
        for path in self.root.glob("job-*.json"):
            try:
                existing.append(int(path.stem.split("-")[1]))
            except (IndexError, ValueError):
                continue
        next_number = max(existing, default=0) + 1
        return f"job-{next_number:04d}"

    def _path(self, job_id: str) -> Path:
        return self.root / f"{job_id}.json"
