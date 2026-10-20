# Medium draft: Jev inside dbt with a DuckDB Python UDF

## Working title

Calling typed AI from SQL: a small Jaffle Shop experiment with Jev, dbt, and DuckDB

## Hook

What if marketing decisions lived where analysts already work — in SQL — instead of a separate notebook or microservice?

## What we are proving (and what we are not)

- **Proving:** a practical pattern for registering a Python UDF in dbt-duckdb, building per-customer JSON state in SQL, and materializing typed Jev answers as tables.
- **Not proving:** model accuracy, campaign ROI, or warehouse-scale throughput. Jaffle Shop has ~100 customers; this demo scores the top 20.

## Architecture

1. `make build-dbt-v2` — Fusion builds Jaffle Shop marts in local DuckDB.
2. `profiles-jev/profiles.yml` — dbt-duckdb loads `jaffle_shop_core_v2.jev_plugin`.
3. `jev_plugin.py` — registers `jev_market_customer(state_json)` on the DuckDB connection.
4. `int_customer_marketing_actions.sql` — assembles customer state JSON and calls the UDF once per row.
5. TypeSafe `system_one` returns structured fields: choice, NOUL, score.

Include Mermaid diagram from README.

## Sample input (trimmed)

```json
{
  "profile": {
    "customer_id": "c-123",
    "count_lifetime_orders": 8,
    "customer_type": "returning",
    "lifetime_spend": 142.5
  },
  "recent_orders": [
    {
      "order_id": "o-9",
      "ordered_at": "2024-06-01T10:00:00",
      "items": [
        {"product_name": "jaffle-1", "product_type": "jaffle"}
      ]
    }
  ]
}
```

Note: `customer_name` is intentionally omitted from state.

## Sample output (from `jev_responses.jsonl`)

Paste one anonymized row from `article/artifacts/jev_responses.jsonl` after running the harness.

## Latency table (from harness)

Sample run on 2026-09-18 (`make experiment-jev-article`, N=20):

| Metric | Value (ms) |
|--------|------------|
| Customers scored | 20 |
| Total wall time | 3,137.8 |
| Cold start (call 1) | 319.8 |
| Warm mean (calls 2–19) | 148.3 |
| p50 | 153.8 |
| p95 | 218.0 |
| min / max | 99.1 / 319.8 |

Explain: latency is dominated by the TypeSafe API round trip, not DuckDB. `threads: 1` keeps calls sequential.

## Repro steps

```bash
cp .env.example .env   # add JEV_API_KEY
make build-dbt-v2
make build-jev-udf
make experiment-jev-article
```

Query helpers:

- `analyses/jev_marketing_results.sql`
- `analyses/jev_latency_summary.sql`

## Honest limitations

- Two dbt environments: Fusion for everyday builds, dbt-duckdb for UDFs.
- One API call per customer row — fine for a demo, not a production per-row pattern.
- Small sample size — good for an integration walkthrough, not for benchmarking model quality.

## Closing

The interesting part is not the scores on toy data. It is that typed AI output can be versioned, tested, and queried like any other dbt model once you accept the sidecar UDF environment.
