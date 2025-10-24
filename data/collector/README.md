# Data Collectors

This directory contains various data collectors for the Spatially project. Each collector gathers specific types of urban planning and development data.

## Local Development

```bash
cd data/collector
source .venv/bin/activate
uv sync
```

## Quick Start 

You should already be in data directory

```bash
docker compose -f docker-compose.dev.yml run --rm collector

```
The folder is mounted into the container so you don't need to rebuild the container everytime you make a change.

However you would need to rebuild the container if you make changes to the Dockerfile or installed new dependencies.

```bash
docker compose -f docker-compose.dev.yml build collector && docker image prune -f

```

You would need to prune it if you want to free up space.

## Available Collectors

- **census**: Collect census demographic data (ACS5)
- **development_plans**: Collect development plan documents
- **zoning_ordinance**: Collect zoning ordinance documents
- **reports**: Collect planning reports
- **paper**: Collect academic papers and research
