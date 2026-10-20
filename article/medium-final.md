# Calling Typed AI from SQL: Jev, dbt, and DuckDB

**Subtitle:** A small Jaffle Shop experiment — wiring pattern, not a benchmark.

---

I wanted to see whether typed AI could live where analysts already work: inside SQL and dbt, not in a separate notebook or microservice.

This post walks through a minimal integration on the Jaffle Shop demo dataset: a Python UDF registered through **dbt-duckdb**, calling **Jev** (TypeSafe [System One](https://docs.typesafe.ai/)), and materializing structured marketing fields into a normal dbt mart.

The dataset has about 100 customers. I scored the top 20 by order count. That is enough to prove the wiring works. It is not enough to prove the model is correct or that per-row inference belongs in production.

---

## What we are proving (and what we are not)

**Proving:**

- A dbt SQL model can call a Python UDF that hits a typed AI API.
- Answers come back as structured fields (choice, score, NOUL) — not free text to parse later.
- The result is a table you can query, test, and join like any other mart.

**Not proving:**

- Campaign ROI or model accuracy on real traffic.
- Warehouse-scale throughput (one HTTP call per row).
- That you need only one dbt installation.

Keep that framing in mind for everything below.

---

## Architecture

The pipeline has two dbt environments on purpose.

1. **dbt Fusion** builds everyday Jaffle Shop marts into local DuckDB (`make build-dbt-v2`).
2. **dbt-duckdb** loads a plugin, registers `jev_market_customer(state_json)` on the connection, and builds one marketing mart (`make build-jev-udf`).

Fusion’s DuckDB adapter cannot register Python UDFs today. A sidecar dbt-duckdb environment is the pragmatic trade-off: keep Fusion for normal transforms; reach for dbt-duckdb when you need SQL-callable Python.

```
  dbt Fusion (marts)          dbt-duckdb (UDF mart)
        |                              |
        v                              v
   DuckDB tables  ──────────>  jev_market_customer()
                                      |
                                      v
                               TypeSafe API (Jev)
                                      |
                                      v
                        int_customer_marketing_actions
```

---

## Step 1: Register the UDF via a dbt-duckdb plugin

In `profiles-jev/profiles.yml`:

```yaml
module_paths:
  - src
plugins:
  - module: jaffle_shop_core_v2.jev_plugin
```

The plugin initializes a TypeSafe client and registers a scalar function on each DuckDB connection:

```python
def register_jev_market_customer(conn, client):
    def jev_market_customer(state_json: str) -> str:
        return market_customer_json(state_json, client)

    conn.create_function(
        "jev_market_customer",
        jev_market_customer,
        side_effects=True,
    )
```

`side_effects=True` is important. DuckDB must know this function leaves the database — every invocation is a network round trip.

Behind the UDF, Python asks Jev three typed questions in a single `system_one` call:

- **choice** — next best marketing action (`winback`, `loyalty_reward`, `hold`, …)
- **NOUL** — likelihood to redeem a promo
- **score** — campaign priority for the week

The SDK returns structured objects. We serialize them to JSON for SQL to parse.

---

## Step 2: Build customer state in SQL, call the UDF

Model `int_customer_marketing_actions` is disabled by default (`enable_jev_udf_models: false`). When enabled, it:

1. Samples the top N customers by `count_lifetime_orders` (default 20).
2. Assembles a JSON document: profile fields plus recent order line items.
3. Calls `jev_market_customer(customer_state)` once per row.
4. Extracts typed columns with `json_extract`.

The heart of the model:

```sql
select
    customer_id,
    jev_market_customer(customer_state) as marketing_json
from customer_state
```

Downstream columns include `next_best_offer`, `likely_to_redeem_promo`, and `campaign_priority`. dbt tests guard the shape: `not_null`, `unique`, `accepted_values` on the offer enum, bounds on confidences.

Example rows (top 5 by `campaign_priority`):

| customer_id | next_best_offer | confidence | priority |
| --- | --- | ---: | ---: |
| 3483e39a… | loyalty_reward | 0.93 | 1.70 |
| 5fccc95a… | loyalty_reward | 0.93 | 1.67 |
| 2609004e… | loyalty_reward | 0.91 | 1.67 |
| 9ff834d1… | loyalty_reward | 0.91 | 1.67 |
| d31efffd… | loyalty_reward | 0.89 | 1.66 |

On this slice Jev mostly labeled heavy buyers as `loyalty_reward`. That anecdote is not the point. The point is the output is a **table in the warehouse**, not a Slack message or a CSV export from a notebook.

---

## One row in, one row out

We deliberately omit `customer_name` from the JSON state sent to the API.

**Input** (trimmed):

```json
{
  "profile": {
    "customer_id": "3483e39a-260f-4974-9366-50c2d833307f",
    "count_lifetime_orders": 231,
    "customer_type": "returning",
    "lifetime_spend": 1396.02
  },
  "recent_orders": [
    {
      "ordered_at": "2025-08-31T00:00:00",
      "items": [{"product_name": "tangaroo", "product_type": "beverage"}]
    },
    {
      "ordered_at": "2025-08-30T00:00:00",
      "items": [{"product_name": "tangaroo", "product_type": "beverage"}]
    }
  ]
}
```

**Output:**

```json
{
  "next_best_offer": "loyalty_reward",
  "next_best_offer_confidence": 0.91,
  "likely_to_redeem_promo": 0.71,
  "campaign_priority": 1.64,
  "campaign_priority_confidence": 0.47
}
```

No regex. No “extract the JSON from the assistant message.” The types are part of the contract.

---

## Latency on N = 20

I measured wall time with a small harness (`make experiment-jev-article`) after building the mart. Calls run sequentially (`threads: 1` in the Jev profile).

| Metric | Milliseconds |
| --- | ---: |
| Total (20 rows) | 3,176 |
| Cold start (first row) | 308 |
| Warm mean (rows 2–20) | 151 |
| p50 | 152 |
| p95 | 213 |
| min / max | 93 / 308 |

Latency is dominated by the TypeSafe API, not DuckDB. Roughly **150 ms per warm call** extrapolates to about three seconds for twenty customers. Fine for a demo. Not a design for scoring millions of rows inside `SELECT`.

---

## Reproduce it

Prerequisites: Python with [uv](https://github.com/astral-sh/uv), a local DuckDB file from Jaffle Shop seeds, and `JEV_API_KEY` (or `TYPESAFE_API_KEY`) in `.env`.

```bash
make build-dbt-v2              # Fusion: staging + marts
make build-jev-udf             # dbt-duckdb: marketing mart via UDF
make experiment-jev-article    # optional: latency JSON + response capture
```

The experiment step writes `article/artifacts/jev_responses.jsonl` and `jev_latency_summary.json`, and loads `raw.jev_benchmark_runs` for SQL analysis.

Full instructions and tests (`make test-jev`) are in the repo README.

**Repository:** [github.com/yu-iskw/jaffle-shop-meets-dbt-v2](https://github.com/yu-iskw/jaffle-shop-meets-dbt-v2)

---

## Limitations worth saying out loud

**Small sample.** Twenty customers from a toy shop. Use this to learn the pattern, not to pick campaigns.

**Two dbt environments.** Operational overhead is real. Worth it only when SQL-callable UDFs are the goal.

**One API call per row.** Production patterns batch customers, pre-compute scores in Python, or run inference on a schedule — then load results as tables.

**Duplicate API work.** Building the mart and running the benchmark harness both call Jev unless you instrument the UDF path directly. I kept them separate so the article has clean latency numbers without modifying the plugin.

---

## Closing thought

The interesting question is not whether customer `3483e39a…` should get `loyalty_reward`. It is whether **typed AI belongs in the analytics layer at all**.

My answer after this experiment: yes, as a **materialized side path**. Version the questions in Python, register a UDF, land answers in a mart, test them in dbt — and keep inference off the critical path of every ad-hoc query.

If you are already on dbt and DuckDB, Jev plus a dbt-duckdb plugin is a small, honest way to try that pattern without standing up a new service.

---

*Thanks for reading. Questions and PRs welcome on the repo.*
