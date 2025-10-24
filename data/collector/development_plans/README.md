# Development Plans Collector

This collector gathers development plan documents from a variety of municipal sources.

It is expected that for each city, a collector for that city is implemented.

Currently, the following cities are supported:

- Boston

## Quick Start

```bash
cd data/collector
source .venv/bin/activate
uv sync
python development_plans/run.py --city <city>
```