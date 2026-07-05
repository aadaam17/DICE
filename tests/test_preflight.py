import pytest

from dice.core.manager import JobManager
from dice.core.models import (
    ExecutionConfig,
    JobConfig,
    RpcConfig,
    TriggerConfig,
    TriggerKind,
    WalletConfig,
)
from dice.core.preflight import PreflightRunner, PreflightStatus
from dice.core.secrets import SecretStore
from dice.core.storage import JobStore


def manual_job(rpc_url: str = "mock://local") -> JobConfig:
    return JobConfig(
        id="job-0001",
        name="Manual",
        chain="ethereum",
        wallet=WalletConfig(name="Wallet", address="0xabc", destination="0xdef"),
        rpc=RpcConfig(http_url=rpc_url),
        trigger=TriggerConfig(kind=TriggerKind.MANUAL),
        execution=ExecutionConfig(function_name="claim"),
    )


@pytest.mark.asyncio
async def test_preflight_passes_for_mock_job(tmp_path):
    manager = JobManager(JobStore(tmp_path))
    job = manual_job()
    manager.create_job(job)

    report = await manager.preflight(job.id)

    assert report.ok
    assert any(check.name == "RPC connection" for check in report.checks)
    assert any("preflight pass" in line for line in manager.get_logs(job.id))


@pytest.mark.asyncio
async def test_preflight_reports_validation_errors(tmp_path):
    job = manual_job()
    job.chain = "unknown"

    report = await PreflightRunner(SecretStore(tmp_path / "secrets")).run(job)

    assert not report.ok
    assert any(check.status == PreflightStatus.FAIL for check in report.checks)
    assert any("Unsupported chain" in check.message for check in report.checks)
