from __future__ import annotations

from dice.adapters.base import ChainAdapter
from dice.adapters.evm import EVMChainAdapter
from dice.adapters.mock import MockChainAdapter
from dice.adapters.profiles import get_profile
from dice.adapters.solana import SolanaChainAdapter
from dice.core.models import JobConfig


def create_adapter(job: JobConfig) -> ChainAdapter:
    profile = get_profile(job.chain)
    if job.rpc.http_url.startswith("mock://"):
        return MockChainAdapter(profile)
    if profile.key == "solana":
        return SolanaChainAdapter(profile=profile, rpc=job.rpc)
    return EVMChainAdapter(profile=profile, rpc=job.rpc)
