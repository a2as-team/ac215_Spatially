# Workflow

## Overview

The workflow is a Docker container that orchestrates Vertex AI pipelines. It is used to:
- Build and publish collector/processor images to GCP Artifact Registry
- Define and run ML pipelines on Vertex AI
- Manage pipeline components and compositions

## Quick Start

```bash
docker compose run --rm workflow
```

## Building and Running Pipelines

### Rebuild After Dependency or Dockerfile Changes

```bash
docker compose build workflow && docker builder prune -f && docker compose run --rm workflow
```

- This rebuilds the workflow container and cleans up build cache to free up disk space
- `docker builder prune -f` removes old build cache (much more effective than `docker image prune`)

### Inside the Container

Once inside the workflow container:

**Publish images to GCP Artifact Registry:**
```bash
python registry/run.py
```

**Run a pipeline:**
```bash
# Run all collectors and processors
python /app/cli.py --city Boston --pipeline all

# Run just development plans pipeline
python /app/cli.py --city Boston --pipeline development_plans

# Run individual collector
python /app/cli.py --city Boston --pipeline collector-development-plans

# Run individual processor
python /app/cli.py --city Boston --pipeline processor-development-plans-label-studio
```