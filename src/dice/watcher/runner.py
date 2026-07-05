from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from dice.core.models import JobConfig
from dice.watcher.triggers import TriggerEvaluator


class Watcher:
    def __init__(self, evaluator: TriggerEvaluator, poll_interval: float = 1.0) -> None:
        self.evaluator = evaluator
        self.poll_interval = poll_interval

    async def wait_until_triggered(self, job: JobConfig) -> AsyncIterator[str]:
        while True:
            if await self.evaluator.should_execute(job.trigger):
                yield "triggered"
                return
            yield "waiting"
            await asyncio.sleep(self.poll_interval)
