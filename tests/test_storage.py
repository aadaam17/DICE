from dice.core.models import (
    ExecutionConfig,
    JobConfig,
    RpcConfig,
    TriggerConfig,
    TriggerKind,
    WalletConfig,
)
from dice.core.storage import JobStore


def test_job_store_round_trips_job(tmp_path):
    store = JobStore(tmp_path)
    job = JobConfig(
        id=store.next_id(),
        name="Test Job",
        chain="ethereum",
        wallet=WalletConfig(
            name="Wallet",
            address="0xabc",
            destination="0xdef",
            private_key_ref="secret://wallet",
        ),
        rpc=RpcConfig(http_url="mock://local"),
        trigger=TriggerConfig(kind=TriggerKind.MANUAL),
        execution=ExecutionConfig(function_name="claim"),
    )

    store.save(job)
    loaded = store.load(job.id)

    assert loaded.id == "job-0001"
    assert loaded.name == "Test Job"
    assert loaded.wallet.private_key_ref == "secret://wallet"
    assert loaded.trigger.kind == TriggerKind.MANUAL
