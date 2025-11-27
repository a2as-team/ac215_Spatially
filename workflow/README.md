# Workflow

## Overview

The workflow is a Docker container that orchestrates Vertex AI pipelines and Kubernetes deployments. It is used to:
- Build and publish collector/processor images to GCP Artifact Registry
- Define and run ML pipelines on Vertex AI
- Manage pipeline components and compositions
- Deploy the backend to Google Kubernetes Engine (GKE)

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

**Publish packages to GCS:**
```bash
python packages/run.py
```

**Run a pipeline:**
```bash
# Run all collectors and processors
python /app/cli.py --city boston --pipeline all

# Run just development plans pipeline
python /app/cli.py --city boston --pipeline development_plans

# Run individual collector
python /app/cli.py --city boston --pipeline collector-development-plans

# Run individual processor
python /app/cli.py --city boston --pipeline processor-development-plans-label-studio
```

## Kubernetes Deployment

Deploy the backend to GKE with auto-scaling, HTTPS, and automatic DNS.

**Full deployment (creates cluster + deploys app + sets up ingress):**
```bash
python deploy/run.py --action deploy
```

**Delete cluster:**
```bash
python deploy/run.py --action delete
```

### What the deployment does:
1. Creates GKE cluster with autoscaling
2. Builds and pushes backend image to Artifact Registry
3. Creates Kubernetes secrets (DB, GCP, Cloudflare)
4. Deploys backend with HPA (Horizontal Pod Autoscaler)
5. Sets up NGINX Ingress Controller
6. Installs cert-manager for automatic TLS certificates
7. Configures ExternalDNS for automatic Cloudflare DNS records
8. Result: `https://zoning-api.teamspatially.com` is live

### Required environment variables:
| Variable | Description |
|----------|-------------|
| `GCP_PROJECT` | GCP project ID |
| `GCP_REGION` | GCP region (default: us-central1) |
| `POSTGRE_HOST` | Database host |
| `POSTGRE_USER` | Database username |
| `POSTGRE_PASSWORD` | Database password |
| `APP_DB_NAME` | Database name |
| `CLOUDFLARE_API_TOKEN` | Cloudflare API token |
| `CERT_EMAIL` | Email for Let's Encrypt |
| `DOMAIN_FILTER` | Domain (e.g., teamspatially.com) |

See `deploy/README.md` for more details.