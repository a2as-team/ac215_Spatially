# Data Collectors

This directory contains various data collectors for the Spatially project. Each collector gathers specific types of urban planning and development data.

## Local Development

```bash
cd data/collector
source .venv/bin/activate
uv sync
```

## Quick Start 

You should already be in the `data` directory.

### Quick Start

To quickly run the collector (if you have not changed dependencies or the Dockerfile), you can simply launch the container:

```bash
docker compose -f docker-compose.dev.yml run --rm collector
```

Your code directory will be mounted into the container, so most code changes are immediately available without needing to rebuild the image.

### Rebuilding After Dependency or Dockerfile Changes

If you've updated the Dockerfile or installed new dependencies and need to rebuild, you can do everything in one line:

```bash
docker compose -f docker-compose.dev.yml build collector && docker image prune -f && docker compose -f docker-compose.dev.yml run --rm collector
```

- This command rebuilds the collector image, cleans up any dangling images, and starts the collector container fresh.
- Use `docker image prune -f` in the chain if you want to free up disk space and remove unused images.

Most of the time, rebuilding is only necessary after a dependency or Dockerfile change; for pure code changes you can just rerun the "Quick Start" command above.

## Available Collectors

- **census**: Collect census demographic data (ACS5)
- **development_plans**: Collect development plan documents
- **zoning_ordinance**: Collect zoning ordinance documents
- **reports**: Collect planning reports
- **paper**: Collect academic papers and research
