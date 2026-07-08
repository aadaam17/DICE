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
