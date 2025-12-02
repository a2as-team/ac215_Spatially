# Kubernetes Deployment

Automated deployment pipeline for the Spatially backend on Google Kubernetes Engine (GKE).

## Architecture

```
workflow/deploy/
├── gke/                    # GKE-specific (cloud provider)
│   └── cluster.py          # Cluster creation/deletion
├── k8s/                    # Kubernetes resources (portable)
│   ├── deployment.yaml     # Backend pods
│   ├── service.yaml        # ClusterIP service
│   ├── hpa.yaml            # Horizontal Pod Autoscaler
│   ├── ingress.yaml        # HTTPS routing
│   ├── cluster-issuer.yaml # Let's Encrypt config
│   ├── external-dns.yaml   # Cloudflare DNS automation
│   ├── secrets.py          # K8s secrets management
│   └── ingress.py          # Ingress/TLS setup
├── scripts/
│   └── gke_deploy.py       # Deployment orchestrator
└── run.py                  # CLI entry point
```

## Features

- **Auto-scaling**: HPA (pods) + Cluster Autoscaler (nodes)
- **Health checks**: Liveness and readiness probes
- **HTTPS**: Automatic TLS via cert-manager + Let's Encrypt
- **DNS automation**: ExternalDNS + Cloudflare
- **Portable**: `k8s/` folder works on any Kubernetes cluster (GKE, EKS, AKS)

## Usage

### Local (via Docker)

```bash
# Full deployment
docker-compose run workflow python deploy/run.py --action deploy

# Delete cluster
docker-compose run workflow python deploy/run.py --action delete
```

### CI/CD (GitHub Actions)

Push to `prod` branch or manually trigger the workflow.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GCP_PROJECT` | GCP project ID |
| `GCP_REGION` | GCP region (default: us-central1) |
| `GKE_ZONE` | GKE zone (default: us-central1-a) |
| `POSTGRE_HOST` | Database host |
| `POSTGRE_USER` | Database username |
| `POSTGRE_PASSWORD` | Database password |
| `APP_DB_NAME` | Database name |
| `CLOUDFLARE_API_TOKEN` | Cloudflare API token for DNS |
| `CERT_EMAIL` | Email for Let's Encrypt notifications |
| `DOMAIN_FILTER` | Domain to manage (e.g., teamspatially.com) |

## Deployment Flow

1. Create/verify GKE cluster
2. Build and push backend image to Artifact Registry
3. Create Kubernetes secrets
4. Deploy backend (Deployment + Service + HPA)
5. Install NGINX Ingress Controller
6. Install cert-manager
7. Install ExternalDNS (Cloudflare)
8. Create ClusterIssuer (Let's Encrypt)
9. Deploy Ingress (triggers DNS + TLS certificate)

Result: `https://zoning-api.teamspatially.com` is live with auto-scaling and auto-renewed TLS.

For monitoring the capability of hpa,

```bash
python -c "from deploy.gke.cluster import GKECluster; GKECluster().get_credentials()"
kubectl get hpa spatially-backend-hpa --watch
kubectl get pods -l app=spatially-backend --watch
```