from dice.execution.simulation import transaction_cost


def test_transaction_cost_uses_gas_price():
    simulation = transaction_cost(
        {"gas": 21_000, "gasPrice": 1_000_000_000},
        "ETH",
    )

    assert simulation.gas_limit == 21_000
    assert simulation.fee_per_gas_wei == 1_000_000_000
    assert simulation.max_cost_wei == 21_000_000_000_000
    assert simulation.max_cost_native == "0.000021"
    assert simulation.native_symbol == "ETH"


def test_transaction_cost_prefers_max_fee_per_gas():
    simulation = transaction_cost(
        {"gas": 50_000, "gasPrice": 1, "maxFeePerGas": 2_000_000_000},
        "ETH",
    )

    assert simulation.fee_per_gas_wei == 2_000_000_000
    assert simulation.max_cost_native == "0.0001"
