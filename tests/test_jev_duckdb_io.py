import duckdb

from jaffle_shop_core_v2.duckdb_io import load_sample_customer_states
from tests.jaffle_fixtures import seed_marts


def test_load_sample_customer_states_limits_and_omits_names() -> None:
    connection = duckdb.connect(":memory:")
    seed_marts(connection)

    states = load_sample_customer_states(connection, limit=1, recent_order_limit=1)

    assert len(states) == 1
    state = states[0]
    assert state["profile"]["customer_id"] == "c-high"
    assert "customer_name" not in state["profile"]
    assert [order["order_id"] for order in state["recent_orders"]] == ["o2"]
    assert state["recent_orders"][0]["items"] == [
        {"product_name": "tangaroo", "product_type": "beverage"}
    ]
