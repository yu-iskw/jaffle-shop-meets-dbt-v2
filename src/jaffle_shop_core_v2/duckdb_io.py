import re
from typing import Any

import duckdb

from jaffle_shop_core_v2.customer_state import (
    DEFAULT_CUSTOMER_LIMIT,
    DEFAULT_RECENT_ORDER_LIMIT,
    PROFILE_FIELDS,
    build_customer_state,
)

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_PROFILE_SQL = ", ".join(PROFILE_FIELDS)
_SAMPLE_PROFILE_SQL = ", ".join(f"s.{field}" for field in PROFILE_FIELDS)


def _require_sql_identifier(name: str) -> str:
    if not _IDENTIFIER.match(name):
        raise ValueError(f"Invalid SQL identifier: {name!r}")
    return f'"{name}"'


def load_sample_customer_states(
    conn: duckdb.DuckDBPyConnection,
    *,
    limit: int = DEFAULT_CUSTOMER_LIMIT,
    recent_order_limit: int = DEFAULT_RECENT_ORDER_LIMIT,
) -> list[dict[str, Any]]:
    result = conn.execute(
        f"""
        WITH sample AS (
            SELECT {_PROFILE_SQL}
            FROM customers
            WHERE count_lifetime_orders > 0
            ORDER BY count_lifetime_orders DESC, customer_id
            LIMIT ?
        ),
        recent_orders AS (
            SELECT
                o.order_id,
                o.customer_id,
                o.ordered_at
            FROM sample AS s
            JOIN orders AS o
                ON o.customer_id = s.customer_id
            QUALIFY dense_rank() OVER (
                PARTITION BY o.customer_id
                ORDER BY o.ordered_at DESC
            ) <= ?
        )
        SELECT
            {_SAMPLE_PROFILE_SQL},
            r.order_id,
            r.ordered_at,
            oi.product_name,
            p.product_type
        FROM sample AS s
        JOIN recent_orders AS r
            ON r.customer_id = s.customer_id
        JOIN order_items AS oi
            ON oi.order_id = r.order_id
        JOIN products AS p
            ON p.product_id = oi.product_id
        ORDER BY s.count_lifetime_orders DESC, s.customer_id, r.ordered_at DESC
        """,
        [limit, recent_order_limit],
    )
    columns = [column[0] for column in result.description]
    grouped: dict[str, dict[str, Any]] = {}
    for row in result.fetchall():
        record = dict(zip(columns, row, strict=True))
        customer_id = record["customer_id"]
        if customer_id not in grouped:
            grouped[customer_id] = {
                "profile": {field: record[field] for field in PROFILE_FIELDS},
                "orders": {},
            }
        orders = grouped[customer_id]["orders"]
        order_id = record["order_id"]
        if order_id not in orders:
            orders[order_id] = {
                "order_id": order_id,
                "ordered_at": record["ordered_at"],
                "items": [],
            }
        orders[order_id]["items"].append(
            {
                "product_name": record["product_name"],
                "product_type": record["product_type"],
            }
        )

    return [
        build_customer_state(
            bundle["profile"],
            list(bundle["orders"].values()),
            recent_order_limit=recent_order_limit,
        )
        for bundle in grouped.values()
    ]
