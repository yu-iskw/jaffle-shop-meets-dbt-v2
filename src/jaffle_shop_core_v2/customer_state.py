from datetime import date, datetime
from decimal import Decimal
from typing import Any, Mapping, Sequence

PROFILE_FIELDS = (
    "customer_id",
    "count_lifetime_orders",
    "first_ordered_at",
    "last_ordered_at",
    "lifetime_spend",
    "customer_type",
)

DEFAULT_CUSTOMER_LIMIT = 20
DEFAULT_RECENT_ORDER_LIMIT = 10


def _json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def build_customer_state(
    profile: Mapping[str, Any],
    orders: Sequence[Mapping[str, Any]],
    *,
    recent_order_limit: int = DEFAULT_RECENT_ORDER_LIMIT,
) -> dict[str, Any]:
    compact_profile = {
        field: _json_safe(profile[field])
        for field in PROFILE_FIELDS
        if field in profile
    }
    ranked = sorted(orders, key=lambda order: order["ordered_at"], reverse=True)
    recent_orders = []
    for order in ranked[:recent_order_limit]:
        recent_orders.append(
            {
                "order_id": order["order_id"],
                "ordered_at": _json_safe(order["ordered_at"]),
                "items": [
                    {
                        "product_name": item["product_name"],
                        "product_type": item["product_type"],
                    }
                    for item in order["items"]
                ],
            }
        )
    return {"profile": compact_profile, "recent_orders": recent_orders}
