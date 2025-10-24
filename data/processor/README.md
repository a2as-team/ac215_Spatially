# Data Processor

This directory contains the data processor for the Spatially project. It is responsible for putting data into the database or Google Cloud Storage. It is also responsible for processing the data to be inputtable to label studio.

## Local Development

```bash
cd data/processor
source .venv/bin/activate
uv sync
```

## Quick Start

```bash
docker compose run --rm processor
```

### Rebuilding After Dependency or Dockerfile Changes 

```bash
docker compose build processor && docker image prune -f && docker compose run --rm processor
```