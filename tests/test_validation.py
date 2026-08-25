import pytest

from dice.core.models import (
    ExecutionConfig,
    JobConfig,
    RpcConfig,
    RunMode,
    SweepAssetKind,
    TriggerConfig,
    TriggerKind,
    WalletConfig,
)
from dice.core.validation import JobValidationError, validate_job


def test_validation_rejects_unsupported_chain():
    job = JobConfig(
        id="job-0001",
        name="Bad Chain",
        chain="unknown",
        wallet=WalletConfig(
            name="Wallet",
            address="0x0000000000000000000000000000000000000000",
            destination="0x0000000000000000000000000000000000000000",
        ),
        rpc=RpcConfig(http_url="mock://local"),
        trigger=TriggerConfig(kind=TriggerKind.MANUAL),
        execution=ExecutionConfig(function_name="claim"),
    )

    result = validate_job(job)

    assert not result.ok
    assert "Unsupported chain: unknown" in result.errors


def test_manager_raises_for_invalid_job(tmp_path):
    from dice.core.manager import JobManager
    from dice.core.storage import JobStore

    manager = JobManager(JobStore(tmp_path))
    job = JobConfig(
        id="job-0001",
        name="",
        chain="ethereum",
        wallet=WalletConfig(name="Wallet", address="0xabc", destination="0xdef"),
        rpc=RpcConfig(http_url=""),
        trigger=TriggerConfig(kind=TriggerKind.MANUAL),
        execution=ExecutionConfig(function_name="claim"),
    )

    with pytest.raises(JobValidationError):
        manager.create_job(job)


def test_validation_rejects_negative_minimum_amount():
    job = JobConfig(
        id="job-0001",
        name="Bad Minimum",
        chain="ethereum",
        wallet=WalletConfig(
            name="Wallet",
            address="0x0000000000000000000000000000000000000000",
            destination="0x0000000000000000000000000000000000000000",
        ),
        rpc=RpcConfig(http_url="mock://local"),
        trigger=TriggerConfig(kind=TriggerKind.MANUAL),
        execution=ExecutionConfig(function_name="claim", min_amount=-1),
    )

    result = validate_job(job)

    assert not result.ok
    assert "Minimum amount cannot be negative" in result.errors


def test_job_round_trips_run_mode():
    job = JobConfig(
        id="job-0001",
        name="Continuous",
        chain="ethereum",
        wallet=WalletConfig(
            name="Wallet",
            address="0x0000000000000000000000000000000000000000",
            destination="0x0000000000000000000000000000000000000000",
        ),
        rpc=RpcConfig(http_url="mock://local"),
        trigger=TriggerConfig(kind=TriggerKind.MANUAL),
        execution=ExecutionConfig(function_name="claim"),
        run_mode=RunMode.CONTINUOUS,
        repeat_delay_seconds=3,
        poll_interval_seconds=0.25,
    )

    loaded = JobConfig.from_dict(job.to_dict())

    assert loaded.run_mode == RunMode.CONTINUOUS
    assert loaded.repeat_delay_seconds == 3
    assert loaded.poll_interval_seconds == 0.25


def test_validation_rejects_negative_poll_interval():
    job = JobConfig(
        id="job-0001",
        name="Bad Poll",
        chain="ethereum",
        wallet=WalletConfig(
            name="Wallet",
            address="0x0000000000000000000000000000000000000000",
            destination="0x0000000000000000000000000000000000000000",
        ),
        rpc=RpcConfig(http_url="mock://local"),
        trigger=TriggerConfig(kind=TriggerKind.MANUAL),
        execution=ExecutionConfig(function_name="claim"),
        poll_interval_seconds=-1,
    )

    result = validate_job(job)

    assert not result.ok
    assert "Poll interval cannot be negative" in result.errors


def test_job_round_trips_token_decimals():
    job = JobConfig(
        id="job-0001",
        name="Token",
        chain="ethereum",
        wallet=WalletConfig(
            name="Wallet",
            address="0x0000000000000000000000000000000000000000",
            destination="0x0000000000000000000000000000000000000000",
        ),
        rpc=RpcConfig(http_url="mock://local"),
        trigger=TriggerConfig(kind=TriggerKind.MANUAL),
        execution=ExecutionConfig(
            function_name="transfer",
            asset_kind=SweepAssetKind.ERC20,
            token_contract="0x0000000000000000000000000000000000000001",
            token_symbol="USDC",
            token_decimals=6,
        ),
    )

    loaded = JobConfig.from_dict(job.to_dict())

    assert loaded.execution.token_decimals == 6


def test_solana_native_addresses_are_accepted():
    job = JobConfig(
        id="job-0001",
        name="Solana",
        chain="solana",
        wallet=WalletConfig(
            name="Wallet",
            address="11111111111111111111111111111111",
            destination="11111111111111111111111111111111",
        ),
        rpc=RpcConfig(http_url="https://api.mainnet-beta.solana.com"),
        trigger=TriggerConfig(kind=TriggerKind.MANUAL),
        execution=ExecutionConfig(function_name="sweep"),
    )

    result = validate_job(job)

    assert result.ok
    assert not any("EVM address" in warning for warning in result.warnings)


def test_solana_token_transfer_is_allowed_with_mint():
    job = JobConfig(
        id="job-0001",
        name="Solana SPL",
        chain="solana",
        wallet=WalletConfig(
            name="Wallet",
            address="11111111111111111111111111111111",
            destination="11111111111111111111111111111111",
        ),
        rpc=RpcConfig(http_url="https://api.mainnet-beta.solana.com"),
        trigger=TriggerConfig(kind=TriggerKind.MANUAL),
        execution=ExecutionConfig(
            function_name="transfer",
            asset_kind=SweepAssetKind.ERC20,
            token_contract="So11111111111111111111111111111111111111112",
            token_symbol="SPL",
        ),
    )

    result = validate_job(job)

    assert result.ok
