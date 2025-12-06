# Cloud Run Deployment

This directory contains the infrastructure for deploying services to Google Cloud Run, a fully managed serverless platform.

## Overview

The Cloud Run deployment system provides:
- **Generic deployment infrastructure**: Reusable `CloudRunService` class for any service
- **Service-specific configurations**: Pre-configured settings in `config.py`
- **CLI integration**: Deploy via `workflow/deploy/run.py` with `--target cloudrun`
- **Automated image building**: Build and push Docker images to Artifact Registry

## Available Services

### NER Service (`ner-service`)

Named Entity Recognition service for extracting article references from development plan text.

**Endpoints**:
- `GET /health` - Health check (liveness probe)
- `GET /ready` - Readiness check (model loaded status)
- `POST /extract-article-references` - Extract article references from text

**Configuration**:
- Memory: 2Gi
- CPU: 2 vCPUs
- Max instances: 10
- Min instances: 0 (scale to zero for cost savings)
- Concurrency: 10 requests per instance
- Timeout: 300 seconds (5 minutes)
- Authentication: Required (not publicly accessible)

## Deployment

### Prerequisites

1. **GCP Project**: Ensure `GCP_PROJECT` and `GCP_REGION` environment variables are set
2. **Authentication**: Service account `spatially-pipeline-accessor-keys` must have permissions
3. **Artifact Registry**: Repository `workflow-images` must exist

### Deploy NER Service

```bash
# Full deployment (build image + push + deploy)
docker-compose run workflow python deploy/run.py \
  --target cloudrun \
  --action deploy \
  --service ner-service

# Deploy only (skip image build, use existing image)
docker-compose run workflow python deploy/run.py \
  --target cloudrun \
  --action deploy-only \
  --service ner-service

# Delete service
docker-compose run workflow python deploy/run.py \
  --target cloudrun \
  --action delete \
  --service ner-service
```

### Deployment Output

After successful deployment, you'll receive:
- Service URL (e.g., `https://ner-service-xxxx-uc.a.run.app`)
- Manual IAM setup commands
- Backend environment variable instructions

## Manual IAM Setup (One-Time)

**IMPORTANT**: These commands must be run manually for security. Do not automate IAM permission changes.

### 1. Grant GCS Access for Model Files

Allow Cloud Run service to read NER model from GCS bucket:

```bash
gcloud projects add-iam-policy-binding spatially-476017 \
  --member="serviceAccount:968366835427-compute@developer.gserviceaccount.com" \
  --role="roles/storage.objectViewer"
```

### 2. Grant Backend Invoke Permission

Allow backend compute service account to invoke the Cloud Run service:

```bash
gcloud run services add-iam-policy-binding ner-service \
  --region=us-central1 \
  --member="serviceAccount:968366835427-compute@developer.gserviceaccount.com" \
  --role="roles/run.invoker"
```

## Backend Integration

### Environment Variables

Add to backend deployment configuration:

```bash
# Enable Cloud Run mode
USE_CLOUDRUN_NER=true

# Service URL from deployment output
NER_SERVICE_URL=https://ner-service-xxxx-uc.a.run.app
```

### Code Usage

The `DevelopmentPlansNER` wrapper automatically switches between local model and Cloud Run based on `USE_CLOUDRUN_NER`:

```python
from app.utils.ner.development_plans_ner import DevelopmentPlansNER

# Initialize (singleton)
ner = DevelopmentPlansNER()

# Extract article references (async)
article_refs = await ner.extract_article_references(text)
# Returns: ["Article 50", "Section 32", ...]
```

## Monitoring

### View Logs

```bash
# Stream logs in real-time
gcloud run services logs tail ner-service --region us-central1

# Read recent logs
gcloud run services logs read ner-service --region us-central1 --limit 50
```

### Service Status

```bash
# Get service details
gcloud run services describe ner-service \
  --region us-central1 \
  --format yaml

# Get service URL
gcloud run services describe ner-service \
  --region us-central1 \
  --format 'value(status.url)'
```

### Metrics

View in Cloud Console:
- Cloud Run → ner-service → Metrics
- Request count, latency, error rate
- Container instance count
- CPU/memory utilization
- Cold start frequency

## Testing

### Local Testing

Test the service locally before deploying:

```bash
cd llm/development_plans/NER

# Build image
docker build -f Dockerfile.service -t ner-service .

# Run locally
docker run -p 8080:8080 \
  -e GCP_PROJECT=spatially-476017 \
  -e FINETUNE_GCS_BUCKET=spatially-us-central-1-model-training \
  -v ~/.config/gcloud:/root/.config/gcloud \
  ner-service

# Test endpoints
curl http://localhost:8080/health
curl http://localhost:8080/ready
curl -X POST http://localhost:8080/extract-article-references \
  -H "Content-Type: application/json" \
  -d '{"text": "According to Article 50, Section 32..."}'
```

### Integration Testing

Test the deployed service with authentication:

```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe ner-service \
  --region us-central1 \
  --format 'value(status.url)')

# Get ID token
TOKEN=$(gcloud auth print-identity-token)

# Test with authentication
curl -X POST $SERVICE_URL/extract-article-references \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "Article 50, Section 32"}'
```

## Cost Optimization

### Scale to Zero

The NER service is configured with `min_instances: 0`, which means:
- Service scales down to 0 when not in use
- No cost when idle
- Cold start penalty (~10-20s) on first request after idle period

### Cost Estimates

With current configuration (2Gi memory, 2 vCPUs):
- **Always-on (min_instances=1)**: ~$10-15/month
- **Scale to zero (min_instances=0)**: ~$0.05 per 1,000 requests
- **Heavy usage (1M requests/month)**: ~$50-100/month

### Reducing Costs

1. **Reduce resources**: Lower memory/CPU if acceptable performance
2. **Reduce max_instances**: Cap at lower number (currently 10)
3. **Enable request-based billing**: Only pay for actual request time
4. **Cache results**: Cache article references in backend to reduce calls

## Troubleshooting

### Cold Start Issues

**Problem**: First request takes 10-20 seconds

**Solutions**:
- Set `min_instances: 1` in `config.py` (increases cost)
- Use Cloud Storage FUSE for faster model loading
- Implement model caching in container

### Authentication Errors

**Problem**: Backend cannot invoke service (403 Forbidden)

**Solutions**:
- Verify IAM policy: `gcloud run services get-iam-policy ner-service --region us-central1`
- Ensure backend compute SA has `roles/run.invoker`
- Check `NER_SERVICE_URL` is correct in backend environment

### Model Loading Failures

**Problem**: Service fails to load NER model from GCS

**Solutions**:
- Verify GCS bucket name: `FINETUNE_GCS_BUCKET`
- Check service account has `roles/storage.objectViewer`
- Verify model exists at `ner_model_output/model/ner_model`

### Timeout Errors

**Problem**: Requests timeout (504)

**Solutions**:
- Increase timeout in `config.py` (currently 300s)
- Check Cloud Run logs for specific errors
- Reduce text length sent to service

## Architecture

### Service Flow

```
Backend Request
    ↓
Get Google Cloud ID Token
    ↓
HTTP POST to Cloud Run Service
    ↓
Cloud Run Service
    ├── Health Check (GET /health)
    ├── Readiness Check (GET /ready)
    └── Extract Entities (POST /extract-article-references)
           ↓
      Load Model from GCS (lazy loading)
           ↓
      Run Inference (BERT)
           ↓
      Return Article References
```

### Service Accounts

- **Deployment**: `spatially-pipeline-accessor-keys` (builds and deploys)
- **Runtime**: Default compute SA `968366835427-compute@developer.gserviceaccount.com` (runs container)
- **Backend**: Same compute SA (invokes Cloud Run service)

### Authentication

Cloud Run uses **ID tokens** (not access tokens) for service-to-service authentication:
1. Backend generates ID token using compute SA credentials
2. Token includes audience (Cloud Run service URL)
3. Cloud Run validates token before allowing request
4. Token automatically refreshed by `google-auth` library

## Adding New Services

To deploy a new Cloud Run service (e.g., OCR service):

1. **Create service code**: `llm/ocr/service/main.py` (FastAPI app)
2. **Create Dockerfile**: `llm/ocr/Dockerfile.service`
3. **Add to registry**: Update `workflow/registry/config.py`:
   ```python
   @staticmethod
   def ocr_service_image(gcp_region: str, gcp_project: str):
       # ... similar to ner_service_image
   ```
4. **Add configuration**: Update `workflow/deploy/cloudrun/config.py`:
   ```python
   @staticmethod
   def ocr_service_config(gcp_region: str, gcp_project: str) -> dict:
       # ... similar to ner_service_config
   ```
5. **Update CLI**: Add `"ocr-service"` to choices in `workflow/deploy/run.py`
6. **Deploy**: `docker-compose run workflow python deploy/run.py --target cloudrun --action deploy --service ocr-service`

The generic `CloudRunService` class handles all deployment logic automatically!

## References

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud Run Best Practices](https://cloud.google.com/run/docs/best-practices)
- [Service-to-Service Authentication](https://cloud.google.com/run/docs/authenticating/service-to-service)
- [Cloud Run Pricing](https://cloud.google.com/run/pricing)
