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
docker compose run --rm collector
```

### Quick Start without docker compose

This will be necessary since we will use vertex ai to run the collector. Vertex ai does not have any idea of how the docker compose file is structured.

```bash
cd data/collector
docker build --platform linux/amd64 -t data-collector -f Dockerfile . && docker builder prune -f
docker run --platform linux/amd64 -it --rm \
  -v $(pwd):/app \
  -v $(pwd)/../../secrets:/secrets:ro \
  --env-file ../../secrets/ac215-spatially-project.env \
  -e GOOGLE_APPLICATION_CREDENTIALS=/secrets/ac215-spatially-storage-accessor-keys.json \
  data-collector
```

Your code directory will be mounted into the container, so most code changes are immediately available without needing to rebuild the image.

### Rebuilding After Dependency or Dockerfile Changes

If you've updated the Dockerfile or installed new dependencies and need to rebuild, you can do everything in one line:

```bash
docker compose build collector && docker builder prune -f && docker compose run --rm collector
```

- This command rebuilds the collector image, cleans up build cache to free up disk space, and starts the collector container fresh.
- `docker builder prune -f` removes old build cache (much more effective than `docker image prune`)

Most of the time, rebuilding is only necessary after a dependency or Dockerfile change; for pure code changes you can just rerun the "Quick Start" command above.

## Available Collectors

- **census**: Collect census demographic data (ACS5)
- **development_plans**: Collect development plan documents
- **zoning_ordinance**: Collect zoning ordinance documents
- **reports**: Collect planning reports
- **paper**: Collect academic papers and research

### Running a Collector

```bash
python development_plans/run.py --city boston
```