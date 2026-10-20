from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

import duckdb
from typesafe_sdk import TypeSafeClient

from jaffle_shop_core_v2.benchmark import (
    BenchmarkRow,
    LatencySummary,
    benchmark_marketing_calls,
    summarize_latencies,
)
from jaffle_shop_core_v2.customer_state import (
    DEFAULT_CUSTOMER_LIMIT,
    DEFAULT_RECENT_ORDER_LIMIT,
)
from jaffle_shop_core_v2.duckdb_io import (
    _require_sql_identifier,
    load_sample_customer_states,
)
from jaffle_shop_core_v2.keys import load_env_file, resolve_api_key
from jaffle_shop_core_v2.marketing import SystemOneClient

DEFAULT_DATABASE = "jaffle_shop.duckdb"
DEFAULT_OUTPUT_DIR = Path("article/artifacts")
RESPONSES_JSONL = "jev_responses.jsonl"
SUMMARY_JSON = "jev_latency_summary.json"
BENCHMARK_SCHEMA = "raw"
BENCHMARK_TABLE = "jev_benchmark_runs"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the Jev marketing benchmark for the Medium article experiment "
            "and write latency/response artifacts."
        )
    )
    parser.add_argument("--database", default=DEFAULT_DATABASE)
    parser.add_argument("--limit", type=int, default=DEFAULT_CUSTOMER_LIMIT)
    parser.add_argument("--recent-orders", type=int, default=DEFAULT_RECENT_ORDER_LIMIT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--env-file", default=".env")
    parser.add_argument(
        "--schema",
        default=BENCHMARK_SCHEMA,
        help="DuckDB schema for raw.jev_benchmark_runs",
    )
    parser.add_argument(
        "--table",
        default=BENCHMARK_TABLE,
        help="DuckDB table name for benchmark rows",
    )
    return parser.parse_args(argv)


def _marketing_fields(response: Mapping[str, Any]) -> tuple[str, float, float, float, float]:
    return (
        str(response["next_best_offer"]),
        float(response["next_best_offer_confidence"]),
        float(response["likely_to_redeem_promo"]),
        float(response["campaign_priority"]),
        float(response["campaign_priority_confidence"]),
    )


def write_responses_jsonl(path: Path, rows: list[BenchmarkRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            payload = {
                "customer_id": row.customer_id,
                "call_index": row.call_index,
                "latency_ms": round(row.latency_ms, 2),
                "customer_state": row.customer_state,
                "marketing_response": row.marketing_response,
            }
            handle.write(json.dumps(payload, default=str))
            handle.write("\n")


def write_summary_json(path: Path, summary: LatencySummary) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(summary.as_dict(), indent=2) + "\n",
        encoding="utf-8",
    )


def write_benchmark_table(
    conn: duckdb.DuckDBPyConnection,
    rows: list[BenchmarkRow],
    *,
    schema: str,
    table: str,
    run_at: datetime,
) -> None:
    schema_name = _require_sql_identifier(schema)
    table_name = _require_sql_identifier(table)
    conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
    conn.execute(
        f"""
        CREATE OR REPLACE TABLE {schema_name}.{table_name} (
            run_at TIMESTAMP,
            customer_id VARCHAR,
            call_index INTEGER,
            latency_ms DOUBLE,
            next_best_offer VARCHAR,
            next_best_offer_confidence DOUBLE,
            likely_to_redeem_promo DOUBLE,
            campaign_priority DOUBLE,
            campaign_priority_confidence DOUBLE
        )
        """
    )
    conn.executemany(
        f"""
        INSERT INTO {schema_name}.{table_name}
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                run_at,
                row.customer_id,
                row.call_index,
                round(row.latency_ms, 2),
                *_marketing_fields(row.marketing_response),
            )
            for row in rows
        ],
    )


def run_article_experiment(
    conn: duckdb.DuckDBPyConnection,
    client: SystemOneClient,
    *,
    limit: int,
    recent_order_limit: int,
    output_dir: Path,
    schema: str = BENCHMARK_SCHEMA,
    table: str = BENCHMARK_TABLE,
) -> dict[str, Any]:
    states = load_sample_customer_states(
        conn,
        limit=limit,
        recent_order_limit=recent_order_limit,
    )
    if not states:
        raise ValueError("No customers found. Seed and build the dbt marts first.")

    run_at = datetime.now(UTC)
    rows = benchmark_marketing_calls(states, client)
    summary = summarize_latencies([row.latency_ms for row in rows])

    output_dir.mkdir(parents=True, exist_ok=True)
    write_responses_jsonl(output_dir / RESPONSES_JSONL, rows)
    write_summary_json(output_dir / SUMMARY_JSON, summary)
    write_benchmark_table(conn, rows, schema=schema, table=table, run_at=run_at)

    return {
        "customer_count": len(rows),
        "output_dir": str(output_dir),
        "summary": summary.as_dict(),
        "schema": schema,
        "table": table,
        "run_at": run_at.isoformat(),
    }


def run(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    load_env_file(Path(args.env_file))
    api_key = resolve_api_key()
    conn = duckdb.connect(args.database)
    try:
        with TypeSafeClient(api_key=api_key) as client:
            result = run_article_experiment(
                conn,
                client,
                limit=args.limit,
                recent_order_limit=args.recent_orders,
                output_dir=args.output_dir,
                schema=args.schema,
                table=args.table,
            )
    finally:
        conn.close()

    summary = result["summary"]
    print(
        "Wrote "
        f"{result['customer_count']} benchmark rows to {result['output_dir']} "
        f"and {result['schema']}.{result['table']}"
    )
    print(
        "Latency ms: "
        f"total={summary['total_ms']} "
        f"p50={summary['p50_ms']} "
        f"p95={summary['p95_ms']} "
        f"cold={summary['cold_start_ms']} "
        f"warm_mean={summary['warm_mean_ms']}"
    )
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
