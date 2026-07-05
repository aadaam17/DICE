from dice.core.manager import JobManager
from dice.core.models import (
    ExecutionConfig,
    JobConfig,
    JobStatus,
    RpcConfig,
    TriggerConfig,
    TriggerKind,
    WalletConfig,
)
from dice.core.storage import JobStore


async def test_manual_job_completes(tmp_path):
    manager = JobManager(JobStore(tmp_path))
    job = JobConfig(
        id="job-0001",
        name="Manual",
        chain="ethereum",
        wallet=WalletConfig(name="Wallet", address="0xabc", destination="0xdef"),
        rpc=RpcConfig(http_url="mock://local"),
        trigger=TriggerConfig(kind=TriggerKind.MANUAL),
        execution=ExecutionConfig(function_name="claim"),
    )
    manager.create_job(job)

    await manager.start(job.id)
    await manager._tasks[job.id]

    assert manager.states[job.id].status == JobStatus.COMPLETED
    assert manager.states[job.id].tx_hash is not None
    assert any("completed" in line for line in manager.get_logs(job.id))


async def test_unknown_job_start_raises(tmp_path):
    manager = JobManager(JobStore(tmp_path))

    try:
        await manager.start("job-9999")
    except KeyError as exc:
        assert "Unknown job" in str(exc)
    else:
        raise AssertionError("Expected KeyError")
