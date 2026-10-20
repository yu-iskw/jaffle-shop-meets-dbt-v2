import json
from types import SimpleNamespace

from jaffle_shop_core_v2.marketing import (
    MARKETING_QUESTIONS,
    market_customer,
    market_customer_json,
)
from tests.recorded_system_one import RecordedClient, choice, noul, score


def _marketing_client() -> RecordedClient:
    return RecordedClient(
        SimpleNamespace(
            choices={"next_best_offer": choice("beverage_upsell", 0.77)},
            nouls={"likely_to_redeem_promo": noul(0.64)},
            scores={"campaign_priority": score(1.4, 0.71)},
        )
    )


def test_market_customer_maps_recorded_answers() -> None:
    client = _marketing_client()
    state = {
        "profile": {
            "customer_id": "c-high",
            "count_lifetime_orders": 8,
            "customer_type": "returning",
        },
        "recent_orders": [],
    }

    row = market_customer(state, client)

    assert row == {
        "customer_id": "c-high",
        "next_best_offer": "beverage_upsell",
        "next_best_offer_confidence": 0.77,
        "likely_to_redeem_promo": 0.64,
        "campaign_priority": 1.4,
        "campaign_priority_confidence": 0.71,
    }
    assert client.calls[0]["questions"] == MARKETING_QUESTIONS


def test_market_customer_json_round_trips_through_udf_shape() -> None:
    client = _marketing_client()
    state = {"profile": {"customer_id": "c-high"}, "recent_orders": []}

    payload = market_customer_json(json.dumps(state), client)

    assert json.loads(payload)["next_best_offer"] == "beverage_upsell"
    assert json.loads(payload)["customer_id"] == "c-high"
