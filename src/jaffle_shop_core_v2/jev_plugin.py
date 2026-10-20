from dbt.adapters.duckdb.plugins import BasePlugin
from duckdb import DuckDBPyConnection
from typesafe_sdk import TypeSafeClient

from jaffle_shop_core_v2.keys import resolve_api_key
from jaffle_shop_core_v2.marketing import register_jev_market_customer


class Plugin(BasePlugin):
    def initialize(self, plugin_config: dict) -> None:
        _ = plugin_config
        self._client = TypeSafeClient(api_key=resolve_api_key())

    def configure_connection(self, conn: DuckDBPyConnection) -> None:
        register_jev_market_customer(conn, self._client)
