from __future__ import annotations

from dice.adapters.base import ChainProfile


PROFILES: dict[str, ChainProfile] = {
    "ethereum": ChainProfile(
        key="ethereum",
        name="Ethereum",
        chain_id=1,
        native_symbol="ETH",
        explorer_url="https://etherscan.io",
    ),
    "bnb": ChainProfile(
        key="bnb",
        name="BNB Chain",
        chain_id=56,
        native_symbol="BNB",
        explorer_url="https://bscscan.com",
    ),
    "arbitrum": ChainProfile(
        key="arbitrum",
        name="Arbitrum One",
        chain_id=42161,
        native_symbol="ETH",
        explorer_url="https://arbiscan.io",
    ),
    "base": ChainProfile(
        key="base",
        name="Base",
        chain_id=8453,
        native_symbol="ETH",
        explorer_url="https://basescan.org",
    ),
    "optimism": ChainProfile(
        key="optimism",
        name="Optimism",
        chain_id=10,
        native_symbol="ETH",
        explorer_url="https://optimistic.etherscan.io",
    ),
    "polygon": ChainProfile(
        key="polygon",
        name="Polygon",
        chain_id=137,
        native_symbol="POL",
        explorer_url="https://polygonscan.com",
    ),
}


def get_profile(key: str) -> ChainProfile:
    try:
        return PROFILES[key]
    except KeyError as exc:
        supported = ", ".join(sorted(PROFILES))
        raise ValueError(f"Unsupported chain '{key}'. Supported chains: {supported}") from exc
