import json
from pathlib import Path

import duckdb

from jaffle_shop_core_v2.article_experiment import (
    RESPONSES_JSONL,
    SUMMARY_JSON,
    run_article_experiment,
)
from jaffle_shop_core_v2.duckdb_io import load_sample_customer_states
from tests.jaffle_fixtures import seed_marts
from tests.recorded_system_one import RecordedClient, marketing_response


def test_run_article_experiment_writes_artifacts_and_benchmark_table(
    tmp_path: Path,
) -> None:
    conn = duckdb.connect(":memory:")
    seed_marts(conn)
    assert len(load_sample_customer_states(conn, limit=2)) == 2
    output_dir = tmp_path / "artifacts"

    result = run_article_experiment(
        conn,
        RecordedClient(marketing_response(next_best_offer="loyalty_reward")),
        limit=2,
        recent_order_limit=10,
        output_dir=output_dir,
    )

    assert result["customer_count"] == 2
    assert (output_dir / RESPONSES_JSONL).is_file()
    assert (output_dir / SUMMARY_JSON).is_file()

    summary = json.loads((output_dir / SUMMARY_JSON).read_text(encoding="utf-8"))
    assert summary["call_count"] == 2

    table_count = conn.execute("SELECT count(*) FROM raw.jev_benchmark_runs").fetchone()
    assert table_count == (2,)

    conn.close()
