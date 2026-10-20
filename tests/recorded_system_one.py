from types import SimpleNamespace


def choice(value: str, confidence: float) -> SimpleNamespace:
    return SimpleNamespace(choice=value, confidence=confidence)


def noul(value: float) -> SimpleNamespace:
    return SimpleNamespace(noul=value)


def score(value: float, confidence: float) -> SimpleNamespace:
    return SimpleNamespace(score=value, confidence=confidence)


class RecordedClient:
    def __init__(self, response: SimpleNamespace) -> None:
        self.calls: list[dict[str, object]] = []
        self.response = response

    def system_one(self, *, state: object, questions: object) -> SimpleNamespace:
        self.calls.append({"state": state, "questions": questions})
        return self.response


def marketing_response(
    *,
    next_best_offer: str = "winback",
    next_best_offer_confidence: float = 0.9,
    likely_to_redeem_promo: float = 0.33,
    campaign_priority: float = 2.0,
    campaign_priority_confidence: float = 0.8,
) -> SimpleNamespace:
    return SimpleNamespace(
        choices={
            "next_best_offer": choice(next_best_offer, next_best_offer_confidence),
        },
        nouls={"likely_to_redeem_promo": noul(likely_to_redeem_promo)},
        scores={
            "campaign_priority": score(
                campaign_priority,
                campaign_priority_confidence,
            ),
        },
    )
