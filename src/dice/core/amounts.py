from __future__ import annotations

from decimal import Decimal, InvalidOperation

from dice.core.models import SweepAssetKind


NATIVE_DECIMALS = 18
SOLANA_NATIVE_DECIMALS = 9

COMMON_TOKEN_DECIMALS: dict[str, int] = {
    "USDC": 6,
    "USDT": 6,
    "DAI": 18,
    "LINK": 18,
    "WETH": 18,
    "WBTC": 8,
}


def decimals_for_asset(
    asset_kind: SweepAssetKind,
    token_symbol: str | None = None,
    token_decimals: int | None = None,
    chain: str | None = None,
    fallback: int = NATIVE_DECIMALS,
) -> int:
    if asset_kind == SweepAssetKind.NATIVE:
        if chain == "solana":
            return SOLANA_NATIVE_DECIMALS
        return NATIVE_DECIMALS
    if token_decimals is not None:
        return token_decimals
    if token_symbol:
        return COMMON_TOKEN_DECIMALS.get(token_symbol.upper(), fallback)
    return fallback


def decimal_amount_to_units(value: object, decimals: int) -> int:
    text = str(value).strip()
    if not text:
        raise ValueError("Amount is required")
    try:
        amount = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid amount: {value}") from exc
    if amount < 0:
        raise ValueError("Amount cannot be negative")
    units = amount * (Decimal(10) ** decimals)
    if units != units.to_integral_value():
        raise ValueError(f"Amount has more than {decimals} decimal places")
    return int(units)


def units_to_decimal_amount(value: int, decimals: int) -> str:
    amount = Decimal(value) / (Decimal(10) ** decimals)
    text = format(amount.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def runtime_amount_to_units(value: object, decimals: int) -> int:
    return decimal_amount_to_units(value, decimals)
