from datetime import date, datetime

from jaffle_shop_core_v2.customer_state import build_customer_state


def test_build_customer_state_omits_customer_name() -> None:
    profile = {
        "customer_id": "abc",
        "customer_name": "Ada Lovelace",
        "count_lifetime_orders": 3,
        "first_ordered_at": date(2023, 1, 2),
        "last_ordered_at": date(2024, 6, 11),
        "lifetime_spend": 42.5,
        "customer_type": "returning",
    }

    state = build_customer_state(profile, orders=[])

    assert "customer_name" not in state["profile"]
    assert state["profile"]["customer_id"] == "abc"
    assert state["profile"]["count_lifetime_orders"] == 3
    assert state["profile"]["first_ordered_at"] == "2023-01-02"
    assert state["profile"]["last_ordered_at"] == "2024-06-11"
    assert state["profile"]["lifetime_spend"] == 42.5
    assert state["profile"]["customer_type"] == "returning"


def test_build_customer_state_keeps_only_the_most_recent_orders() -> None:
    profile = {
        "customer_id": "abc",
        "count_lifetime_orders": 12,
        "first_ordered_at": datetime(2022, 1, 1, 8, 0, 0),
        "last_ordered_at": datetime(2024, 6, 11, 12, 0, 0),
        "lifetime_spend": 100.0,
        "customer_type": "returning",
    }
    orders = [
        {
            "order_id": f"o{i}",
            "ordered_at": datetime(2024, 1, i, 10, 0, 0),
            "items": [{"product_name": f"item-{i}", "product_type": "jaffle"}],
        }
        for i in range(1, 13)
    ]

    state = build_customer_state(profile, orders, recent_order_limit=10)

    assert [order["order_id"] for order in state["recent_orders"]] == [
        f"o{i}" for i in range(12, 2, -1)
    ]
    assert state["recent_orders"][0]["items"] == [
        {"product_name": "item-12", "product_type": "jaffle"}
    ]
