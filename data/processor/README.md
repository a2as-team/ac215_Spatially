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

### Quick Start without docker compose

This will be necessary since we will use vertex ai to run the processor. Vertex ai does not have any idea of how the docker compose file is structured.

```bash
cd data/processor
docker build --platform linux/amd64 -t data-processor -f Dockerfile . && docker builder prune -f
docker run --platform linux/amd64 -it --rm \
  -v $(pwd):/app \
  -v $(pwd)/../../secrets:/secrets:ro \
  --env-file ../../secrets/ac215-spatially-project.env \
  -e GOOGLE_APPLICATION_CREDENTIALS=/secrets/ac215-spatially-storage-accessor-keys.json \
  data-processor
```

Your code directory will be mounted into the container, so most code changes are immediately available without needing to rebuild the image.

### Rebuilding After Dependency or Dockerfile Changes

If you've updated the Dockerfile or installed new dependencies and need to rebuild, you can do everything in one line:

```bash
docker compose build processor && docker builder prune -f && docker compose run --rm processor
```

- This command rebuilds the processor image, cleans up build cache to free up disk space, and starts the processor container fresh.
- `docker builder prune -f` removes old build cache (much more effective than `docker image prune`)

Most of the time, rebuilding is only necessary after a dependency or Dockerfile change; for pure code changes you can just rerun the "Quick Start" command above.