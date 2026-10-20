UV_CACHE_DIR := .uv-cache
DBT_VENV := .venv-dbt-v2
DBT := $(DBT_VENV)/bin/dbt
DBT_DUCKDB_VENV := .venv-dbt-duckdb
DBT_DUCKDB := $(DBT_DUCKDB_VENV)/bin/dbt
DBT_CHARTS_VERSION ?= 0.7.1
DCT ?= dct
DCT_BOARD := charts/jaffle_shop_overview.yml
DCT_RENDER_DIR := renders

.DEFAULT_GOAL := help

.PHONY: help venv-dbt-v2 install-dbt-v2 setup-dbt-v2 build-dbt-v2 docs-generate-dbt-v2 docs-serve-dbt-v2 clean-dbt-v2 setup-dbt-charts validate-dbt-charts render-dbt-charts serve-dbt-charts clean-dbt-charts test-jev setup-dbt-duckdb build-jev-udf experiment-jev-article clean-dbt-duckdb

help:
	@printf '%s\n' \
		'Available targets:' \
		'  make setup-dbt-v2  Create the isolated dbt v2 environment with uv' \
		'  make build-dbt-v2  Build the project against the local DuckDB database' \
		'  make docs-generate-dbt-v2  Generate a static dbt docs v2 site in target/docs' \
		'  make docs-serve-dbt-v2     Serve dbt docs v2 locally at http://127.0.0.1:8580' \
		'  make clean-dbt-v2  Remove dbt v2 environment, cache, database, and build artifacts' \
		'  make test-jev             Run Jev unit tests' \
		'  make setup-dbt-duckdb     Create the isolated dbt-core + dbt-duckdb environment' \
		'  make build-jev-udf        Build int_customer_marketing_actions via jev_market_customer()' \
		'  make experiment-jev-article  Benchmark Jev latency and write article/artifacts' \
		'  make setup-dbt-charts     Install the isolated dbt Charts command-line tool' \
		'  make validate-dbt-charts  Validate the Jaffle Shop dbt Charts board' \
		'  make render-dbt-charts    Write HTML and PNG renders to renders/' \
		'  make serve-dbt-charts     Serve the interactive board at http://127.0.0.1:3000' \
		'  make clean-dbt-charts     Remove generated dbt Charts renders'

venv-dbt-v2 install-dbt-v2:
	UV_CACHE_DIR=$(UV_CACHE_DIR) UV_PROJECT_ENVIRONMENT=$(DBT_VENV) uv sync --python 3.13 --frozen --no-default-groups --group dbt-v2

setup-dbt-v2: install-dbt-v2
	@$(DBT) --version

build-dbt-v2: setup-dbt-v2
	$(DBT) build --profiles-dir .

docs-generate-dbt-v2: setup-dbt-v2
	$(DBT) docs generate --profiles-dir . --output-dir target/docs

docs-serve-dbt-v2: setup-dbt-v2
	$(DBT) docs serve --target-path target --no-open

test-jev:
	uv run --no-default-groups --group jev --group dev pytest tests -q

setup-dbt-duckdb:
	UV_CACHE_DIR=$(UV_CACHE_DIR) UV_PROJECT_ENVIRONMENT=$(DBT_DUCKDB_VENV) uv sync --python 3.12 --frozen --no-default-groups --group dbt-duckdb
	@$(DBT_DUCKDB) --version
	$(DBT_DUCKDB) deps --profiles-dir profiles-jev

build-jev-udf:
	@if [ ! -x "$(DBT_DUCKDB)" ]; then $(MAKE) setup-dbt-duckdb; fi
	$(DBT_DUCKDB) build --profiles-dir profiles-jev --select int_customer_marketing_actions --vars '{enable_jev_udf_models: true}'

experiment-jev-article:
	PYTHONPATH=src uv run --no-default-groups --group jev python -m jaffle_shop_core_v2.article_experiment --database jaffle_shop.duckdb

clean-dbt-duckdb:
	rm -rf -- .venv-dbt-duckdb

clean-dbt-v2:
	rm -rf -- .venv-dbt-v2 .uv-cache jaffle_shop.duckdb jaffle_shop.duckdb.wal target dbt_packages logs

setup-dbt-charts:
	uv tool install --python 3.13 --reinstall dbt-charts==$(DBT_CHARTS_VERSION)

validate-dbt-charts:
	$(DCT) validate $(DCT_BOARD)

render-dbt-charts: validate-dbt-charts
	mkdir -p $(DCT_RENDER_DIR)
	$(DCT) render $(DCT_BOARD) --format html --output $(DCT_RENDER_DIR)/jaffle_shop_overview.html
	$(DCT) render $(DCT_BOARD) --format png --output $(DCT_RENDER_DIR)/jaffle_shop_overview.png

serve-dbt-charts:
	$(DCT) serve --host 127.0.0.1 --port 3000

clean-dbt-charts:
	rm -rf -- renders
