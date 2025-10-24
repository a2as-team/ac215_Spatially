# Development Plans Collector

This collector gathers development plan documents from a variety of municipal sources.

It is expected that for each city, a collector for that city is implemented.

Currently, the following cities are supported:

- Boston

## Quick Start

Using Docker:
```bash
docker compose run --rm collector
```

If you changed the code, you need to rebuild the container:
```bash
docker compose build collector && docker image prune -f && docker compose run --rm collector
```

Then you can run the collector:
```bash
cd data/collector
source .venv/bin/activate
uv sync
python development_plans/run.py --city <city>
```