import pytest

from dice.core.amounts import decimal_amount_to_units, decimals_for_asset, units_to_decimal_amount
from dice.core.models import SweepAssetKind


def test_decimal_amount_to_native_units():
    assert decimal_amount_to_units("0.001", 18) == 1_000_000_000_000_000


def test_decimal_amount_to_token_units():
    assert decimal_amount_to_units("1.5", 6) == 1_500_000


def test_units_to_decimal_amount():
    assert units_to_decimal_amount(1_500_000, 6) == "1.5"


def test_rejects_too_many_decimal_places():
    with pytest.raises(ValueError):
        decimal_amount_to_units("0.0000001", 6)


def test_solana_native_decimals():
    decimals = decimals_for_asset(SweepAssetKind.NATIVE, chain="solana")

    assert decimals == 9
    assert decimal_amount_to_units("0.1", decimals) == 100_000_000
