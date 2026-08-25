from dice.adapters.evm import EVMChainAdapter
from dice.adapters.factory import create_adapter
from dice.adapters.mock import MockChainAdapter
from dice.adapters.solana import SolanaChainAdapter
from dice.core.models import (
    ExecutionConfig,
    JobConfig,
    RpcConfig,
    TriggerConfig,
    TriggerKind,
    WalletConfig,
)


def _job(rpc_url: str, chain: str = "ethereum") -> JobConfig:
    return JobConfig(
        id="job-0001",
        name="Adapter",
        chain=chain,
        wallet=WalletConfig(
            name="Wallet",
            address="0x0000000000000000000000000000000000000000",
            destination="0x0000000000000000000000000000000000000000",
        ),
        rpc=RpcConfig(http_url=rpc_url),
        trigger=TriggerConfig(kind=TriggerKind.MANUAL),
        execution=ExecutionConfig(function_name="claim"),
    )


def test_mock_rpc_uses_mock_adapter():
    assert isinstance(create_adapter(_job("mock://local")), MockChainAdapter)


def test_http_rpc_uses_evm_adapter():
    assert isinstance(create_adapter(_job("http://localhost:8545")), EVMChainAdapter)


def test_solana_rpc_uses_solana_adapter():
    assert isinstance(
        create_adapter(_job("https://api.mainnet-beta.solana.com", chain="solana")),
        SolanaChainAdapter,
    )
