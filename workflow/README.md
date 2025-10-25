# Workflow

## Overview

The workflow is a Docker container that contains the code for the workflow. It is used to publish the images to the container registry.

## Quick Start

```bash
docker compose up workflow
```

## Development

```bash
docker compose build workflow && docker image prune -f && docker compose run --rm workflow
```