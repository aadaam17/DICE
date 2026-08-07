from dice.adapters.mock import MockChainAdapter
from dice.adapters.profiles import get_profile
from dice.core.models import (
    ExecutionConfig,
    JobConfig,
    RpcConfig,
    SweepAssetKind,
    TriggerConfig,
    TriggerKind,
    WalletConfig,
)
from dice.core.workflow import ActionSpec, WorkflowActionKind
from dice.execution.actions import ActionContext, WorkflowActionDispatcher
from dice.execution.broadcaster import Broadcaster
from dice.execution.builder import TransactionBuilder


def _job() -> JobConfig:
    return JobConfig(
        id="job-0001",
        name="Action Test",
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
            arguments=["0x0000000000000000000000000000000000000000", "1000"],
            asset_kind=SweepAssetKind.NATIVE,
        ),
    )


async def test_mock_action_dispatcher_broadcasts_transfer():
    adapter = MockChainAdapter(get_profile("ethereum"))
    context = ActionContext(
        adapter=adapter,
        builder=TransactionBuilder(),
        broadcaster=Broadcaster(adapter),
    )

    results = await WorkflowActionDispatcher().execute(
        _job(),
        [ActionSpec(kind=WorkflowActionKind.TRANSFER_NATIVE)],
        context,
    )

    assert results[0].tx_hash is not None
    assert results[0].tx_hash.startswith("0x")


async def test_notify_action_does_not_broadcast():
    adapter = MockChainAdapter(get_profile("ethereum"))
    context = ActionContext(
        adapter=adapter,
        builder=TransactionBuilder(),
        broadcaster=Broadcaster(adapter),
    )

    results = await WorkflowActionDispatcher().execute(
        _job(),
        [ActionSpec(kind=WorkflowActionKind.NOTIFY, params={"message": "hello"})],
        context,
    )

    assert results[0].tx_hash is None
    assert results[0].message == "hello"


async def test_transfer_skips_when_amount_below_minimum():
    adapter = MockChainAdapter(get_profile("ethereum"))
    context = ActionContext(
        adapter=adapter,
        builder=TransactionBuilder(),
        broadcaster=Broadcaster(adapter),
    )
    job = _job()
    job.execution.min_amount = 2_000

    results = await WorkflowActionDispatcher().execute(
        job,
        [ActionSpec(kind=WorkflowActionKind.TRANSFER_NATIVE)],
        context,
    )

    assert results[0].skipped is True
    assert results[0].tx_hash is None
    assert "below minimum" in results[0].message


async def test_transfer_broadcasts_when_amount_meets_minimum():
    adapter = MockChainAdapter(get_profile("ethereum"))
    context = ActionContext(
        adapter=adapter,
        builder=TransactionBuilder(),
        broadcaster=Broadcaster(adapter),
    )
    job = _job()
    job.execution.min_amount = 1_000

    results = await WorkflowActionDispatcher().execute(
        job,
        [ActionSpec(kind=WorkflowActionKind.TRANSFER_NATIVE)],
        context,
    )

    assert results[0].skipped is False
    assert results[0].tx_hash is not None
