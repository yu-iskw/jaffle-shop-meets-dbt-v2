import json

from jaffle_shop_core_v2.benchmark import (
    benchmark_marketing_calls,
    percentile,
    summarize_latencies,
    time_json_call,
)
from tests.recorded_system_one import RecordedClient, marketing_response


def test_percentile_interpolates_between_values() -> None:
    assert percentile([10.0, 20.0, 30.0, 40.0], 0.5) == 25.0
    assert percentile([10.0, 20.0, 30.0, 40.0], 0.95) == 38.5


def test_summarize_latencies_reports_cold_and_warm_means() -> None:
    summary = summarize_latencies([1000.0, 200.0, 300.0, 400.0])

    assert summary.call_count == 4
    assert summary.cold_start_ms == 1000.0
    assert summary.warm_mean_ms == 300.0
    assert summary.p50_ms == 350.0
    assert summary.total_ms == 1900.0


def test_time_json_call_returns_latency_and_response() -> None:
    state = {"profile": {"customer_id": "c1"}, "recent_orders": []}

    latency_ms, response = time_json_call(
        lambda payload: json.dumps(
            {
                "customer_id": "c1",
                "next_best_offer": "hold",
                "next_best_offer_confidence": 0.5,
                "likely_to_redeem_promo": 0.1,
                "campaign_priority": 1.0,
                "campaign_priority_confidence": 0.6,
            }
        ),
        json.dumps(state),
    )

    assert latency_ms >= 0
    assert response["next_best_offer"] == "hold"


def test_benchmark_marketing_calls_preserves_customer_order() -> None:
    client = RecordedClient(marketing_response(next_best_offer="offer-1"))
    states = [
        {"profile": {"customer_id": "c-high"}, "recent_orders": []},
        {"profile": {"customer_id": "c-low"}, "recent_orders": []},
    ]

    rows = benchmark_marketing_calls(states, client)

    assert [row.customer_id for row in rows] == ["c-high", "c-low"]
    assert rows[0].call_index == 0
    assert rows[1].call_index == 1
    assert rows[0].marketing_response["next_best_offer"] == "offer-1"
    assert len(client.calls) == 2
