from dice.core.manager import JobManager
from dice.core.models import ExecutionConfig, JobConfig, RpcConfig, TriggerConfig, TriggerKind, WalletConfig
from dice.core.registry import load_builtin_plugins, registry
from dice.core.storage import JobStore


def test_builtin_plugins_are_discoverable():
    load_builtin_plugins()
    keys = {metadata.key for metadata in registry.list()}

    assert {
        "stake_sweep",
        "token_sweep",
        "scheduled_transfer",
        "wallet_watch",
        "contract_call",
        "balance_trigger",
        "event_trigger",
        "custom_workflow",
    }.issubset(keys)


def test_manager_assigns_default_workflow_for_plugin_jobs(tmp_path):
    manager = JobManager(JobStore(tmp_path))
    job = JobConfig(
        id="job-0001",
        name="Contract Call",
        chain="ethereum",
        wallet=WalletConfig(
            name="Wallet",
            address="0x0000000000000000000000000000000000000000",
            destination="0x0000000000000000000000000000000000000000",
        ),
        rpc=RpcConfig(http_url="mock://local"),
        trigger=TriggerConfig(kind=TriggerKind.MANUAL),
        execution=ExecutionConfig(function_name="claim"),
        job_type="contract_call",
    )

    manager.create_job(job)

    assert manager.jobs["job-0001"].workflow is not None
    assert manager.jobs["job-0001"].workflow.actions[0].kind.value == "call_contract"
