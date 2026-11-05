# One-command rebuild: `make all` (requires uv and quarto installed)
.PHONY: all setup data build site preview clean

all: data build site

setup:
	uv sync

data: data/clean/endomondo_workouts.parquet
	uv run python scripts/download_heartsteps.py

data/raw/endomondo/endomondoMeta.json.gz:
	uv run python scripts/download_endomondo.py

data/clean/endomondo_workouts.parquet: data/raw/endomondo/endomondoMeta.json.gz scripts/flatten_endomondo.py
	uv run python scripts/flatten_endomondo.py

build: data
	cd dbt && uv run dbt build

site:
	cd site && uv run quarto render

preview:
	cd site && uv run quarto preview

clean:
	rm -rf dbt/target site/_site
