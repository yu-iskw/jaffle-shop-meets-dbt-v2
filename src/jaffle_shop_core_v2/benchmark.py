from __future__ import annotations

import json
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Callable, Mapping, Sequence

from jaffle_shop_core_v2.marketing import SystemOneClient, market_customer_json


@dataclass(frozen=True)
class BenchmarkRow:
    customer_id: str
    call_index: int
    latency_ms: float
    customer_state: Mapping[str, Any]
    marketing_response: Mapping[str, Any]


@dataclass(frozen=True)
class LatencySummary:
    call_count: int
    total_ms: float
    min_ms: float
    mean_ms: float
    p50_ms: float
    p95_ms: float
    max_ms: float
    cold_start_ms: float | None
    warm_mean_ms: float | None

    def as_dict(self) -> dict[str, float | int | None]:
        return {
            "call_count": self.call_count,
            "total_ms": round(self.total_ms, 2),
            "min_ms": round(self.min_ms, 2),
            "mean_ms": round(self.mean_ms, 2),
            "p50_ms": round(self.p50_ms, 2),
            "p95_ms": round(self.p95_ms, 2),
            "max_ms": round(self.max_ms, 2),
            "cold_start_ms": (
                round(self.cold_start_ms, 2)
                if self.cold_start_ms is not None
                else None
            ),
            "warm_mean_ms": (
                round(self.warm_mean_ms, 2)
                if self.warm_mean_ms is not None
                else None
            ),
        }


def percentile(values: Sequence[float], p: float) -> float:
    if not values:
        raise ValueError("values must not be empty")
    if p < 0 or p > 1:
        raise ValueError("p must be between 0 and 1")
    sorted_values = sorted(values)
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (len(sorted_values) - 1) * p
    low = int(rank)
    high = min(low + 1, len(sorted_values) - 1)
    weight = rank - low
    return sorted_values[low] * (1 - weight) + sorted_values[high] * weight


def summarize_latencies(latencies_ms: Sequence[float]) -> LatencySummary:
    if not latencies_ms:
        raise ValueError("latencies_ms must not be empty")
    cold_start_ms = latencies_ms[0]
    warm_latencies = latencies_ms[1:]
    warm_mean_ms = (
        sum(warm_latencies) / len(warm_latencies) if warm_latencies else None
    )
    return LatencySummary(
        call_count=len(latencies_ms),
        total_ms=sum(latencies_ms),
        min_ms=min(latencies_ms),
        mean_ms=sum(latencies_ms) / len(latencies_ms),
        p50_ms=percentile(latencies_ms, 0.5),
        p95_ms=percentile(latencies_ms, 0.95),
        max_ms=max(latencies_ms),
        cold_start_ms=cold_start_ms,
        warm_mean_ms=warm_mean_ms,
    )


def time_json_call(fn: Callable[[str], str], state_json: str) -> tuple[float, Mapping[str, Any]]:
    started = perf_counter()
    response_json = fn(state_json)
    latency_ms = (perf_counter() - started) * 1000
    response = json.loads(response_json)
    if not isinstance(response, dict):
        raise TypeError("marketing response must be a JSON object")
    return latency_ms, response


def benchmark_marketing_calls(
    states: Sequence[Mapping[str, Any]],
    client: SystemOneClient,
) -> list[BenchmarkRow]:
    if not states:
        raise ValueError("states must not be empty")

    rows: list[BenchmarkRow] = []
    for call_index, state in enumerate(states):
        customer_id = str(state["profile"]["customer_id"])
        latency_ms, response = time_json_call(
            lambda payload: market_customer_json(payload, client),
            json.dumps(state),
        )
        rows.append(
            BenchmarkRow(
                customer_id=customer_id,
                call_index=call_index,
                latency_ms=latency_ms,
                customer_state=state,
                marketing_response=response,
            )
        )
    return rows
