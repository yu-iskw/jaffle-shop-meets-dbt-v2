import json
from types import SimpleNamespace

import duckdb

from jaffle_shop_core_v2.marketing import register_jev_market_customer
from tests.recorded_system_one import RecordedClient, choice, noul, score


def test_duckdb_udf_calls_jev_mapper_from_sql() -> None:
    client = RecordedClient(
        SimpleNamespace(
            choices={"next_best_offer": choice("winback", 0.9)},
            nouls={"likely_to_redeem_promo": noul(0.33)},
            scores={"campaign_priority": score(2.0, 0.8)},
        )
    )
    conn = duckdb.connect(":memory:")
    register_jev_market_customer(conn, client)
    state = json.dumps({"profile": {"customer_id": "c1"}, "recent_orders": []})
    offer = conn.execute(
        "SELECT json_extract_string(jev_market_customer(?), '$.next_best_offer')",
        [state],
    ).fetchone()
    assert offer == ("winback",)
