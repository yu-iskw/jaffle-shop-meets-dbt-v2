UV_CACHE_DIR := .uv-cache
DBT_VENV := .venv-dbt-v2
DBT_PYTHON := $(DBT_VENV)/bin/python
DBT := $(DBT_VENV)/bin/dbt
DBT_CHARTS_VERSION ?= 0.7.1
DCT ?= dct
DCT_BOARD := charts/jaffle_shop_overview.yml
DCT_RENDER_DIR := renders

.DEFAULT_GOAL := help

.PHONY: help venv-dbt-v2 install-dbt-v2 setup-dbt-v2 build-dbt-v2 docs-generate-dbt-v2 docs-serve-dbt-v2 clean-dbt-v2 setup-dbt-charts validate-dbt-charts render-dbt-charts serve-dbt-charts clean-dbt-charts

help:
	@printf '%s\n' \
		'Available targets:' \
		'  make setup-dbt-v2  Create the isolated dbt v2 environment with uv' \
		'  make build-dbt-v2  Build the project against the local DuckDB database' \
		'  make docs-generate-dbt-v2  Generate a static dbt docs v2 site in target/docs' \
		'  make docs-serve-dbt-v2     Serve dbt docs v2 locally at http://127.0.0.1:8580' \
		'  make clean-dbt-v2  Remove dbt v2 environment, cache, database, and build artifacts' \
		'  make setup-dbt-charts     Install the isolated dbt Charts command-line tool' \
		'  make validate-dbt-charts  Validate the Jaffle Shop dbt Charts board' \
		'  make render-dbt-charts    Write HTML and PNG renders to renders/' \
		'  make serve-dbt-charts     Serve the interactive board at http://127.0.0.1:3000' \
		'  make clean-dbt-charts     Remove generated dbt Charts renders'

venv-dbt-v2:
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv venv --allow-existing --python 3.13 $(DBT_VENV)

install-dbt-v2: venv-dbt-v2
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv pip sync --python $(DBT_PYTHON) requirements-dbt-v2.txt

setup-dbt-v2: install-dbt-v2
	@$(DBT) --version

build-dbt-v2: setup-dbt-v2
	$(DBT) build --profiles-dir .

docs-generate-dbt-v2: setup-dbt-v2
	$(DBT) docs generate --profiles-dir . --output-dir target/docs

docs-serve-dbt-v2: setup-dbt-v2
	$(DBT) docs serve --target-path target --no-open

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
