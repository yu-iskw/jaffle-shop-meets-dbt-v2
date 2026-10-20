import json
from typing import Any, Mapping, Protocol


class SystemOneClient(Protocol):
    def system_one(self, *, state: object, questions: Mapping[str, object]) -> Any: ...


MARKETING_QUESTIONS: dict[str, dict[str, Any]] = {
    "next_best_offer": {
        "type": "choice",
        "instructions": (
            "Which marketing action should the shop take for this customer next?"
        ),
        "criteria": {
            "winback": "Has gone quiet and should be invited back",
            "beverage_upsell": "Buys food but drinks are a good add-on",
            "jaffle_feature": "Would respond to a featured or new jaffle",
            "loyalty_reward": "Frequent buyer who should get a thank-you offer",
            "hold": "Do not message; wait or already well served",
        },
    },
    "likely_to_redeem_promo": {
        "type": "noul",
        "instructions": (
            "This customer is likely to redeem a limited-time discount if we send one"
        ),
    },
    "campaign_priority": {
        "type": "score",
        "instructions": "How high a priority is this customer for this week's campaign spend?",
        "criteria": ["low", "medium", "high"],
    },
}


def market_customer(
    state: Mapping[str, Any], client: SystemOneClient
) -> dict[str, Any]:
    response = client.system_one(state=state, questions=MARKETING_QUESTIONS)
    offer = response.choices["next_best_offer"]
    priority = response.scores["campaign_priority"]
    return {
        "customer_id": state["profile"]["customer_id"],
        "next_best_offer": offer.choice,
        "next_best_offer_confidence": offer.confidence,
        "likely_to_redeem_promo": response.nouls["likely_to_redeem_promo"].noul,
        "campaign_priority": priority.score,
        "campaign_priority_confidence": priority.confidence,
    }


def market_customer_json(state_json: str, client: SystemOneClient) -> str:
    return json.dumps(market_customer(json.loads(state_json), client))


def register_jev_market_customer(conn: Any, client: SystemOneClient) -> None:
    def jev_market_customer(state_json: str) -> str:
        return market_customer_json(state_json, client)

    conn.create_function(
        "jev_market_customer",
        jev_market_customer,
        side_effects=True,
    )
