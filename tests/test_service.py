import asyncio

from dice.core.manager import JobManager
from dice.core.models import (
    ExecutionConfig,
    JobConfig,
    RpcConfig,
    TriggerConfig,
    TriggerKind,
    WalletConfig,
)
from dice.core.storage import JobStore
from dice.service.client import ServiceClient
from dice.service.server import DiceService


async def test_service_exposes_job_manager_snapshot(tmp_path):
    store = JobStore(tmp_path)
    manager = JobManager(store)
    job = JobConfig(
        id="job-0001",
        name="Daemon Manual",
        chain="ethereum",
        wallet=WalletConfig(name="Wallet", address="0xabc", destination="0xdef"),
        rpc=RpcConfig(http_url="mock://local"),
        trigger=TriggerConfig(kind=TriggerKind.MANUAL),
        execution=ExecutionConfig(function_name="claim"),
    )
    manager.create_job(job)
    service = DiceService(manager=manager, port=8876)

    await service.start()
    try:
        client = ServiceClient(port=8876)
        assert await asyncio.to_thread(client.ping)

        snapshot = await asyncio.to_thread(client.list_jobs)
        assert snapshot["jobs"][0]["id"] == "job-0001"

        report = await asyncio.to_thread(client.preflight_job, "job-0001")
        assert report["ok"] is True

        await asyncio.to_thread(client.start_job, "job-0001")
        await manager._tasks["job-0001"]

        snapshot = await asyncio.to_thread(client.list_jobs)
        assert snapshot["states"][0]["status"] == "completed"

        logs = await asyncio.to_thread(client.get_logs, "job-0001")
        assert any("completed" in line for line in logs)

        await asyncio.to_thread(client.delete_job, "job-0001")
        snapshot = await asyncio.to_thread(client.list_jobs)
        assert snapshot["jobs"] == []
    finally:
        await service.stop()
