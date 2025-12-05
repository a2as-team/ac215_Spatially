# Backend Deployment Notes - Cloud Run NER Migration

## Changes Made

### 1. Removed Heavy Dependencies from backend/pyproject.toml
- ✅ Removed `torch>=2.0.0` (~2GB)
- ✅ Removed `transformers>=4.30.0` (~1GB)

**Result**: Backend Docker image is now ~3GB smaller, leading to faster builds and deployments.

## Deployment Requirements

### Environment Variables

The backend requires these environment variables to use the Cloud Run NER service:

```bash
# Enable Cloud Run mode (REQUIRED)
USE_CLOUDRUN_NER=true

# Cloud Run NER service URL (REQUIRED)
# Get this from: gcloud run services describe ner-service --region us-central1 --format 'value(status.url)'
NER_SERVICE_URL=https://ner-service-xxxx-uc.a.run.app
```

### Kubernetes Deployment (GKE)

The environment variables are automatically set by `workflow/deploy/k8s/secrets.py` when you provide:

```bash
export USE_CLOUDRUN_NER=true
export NER_SERVICE_URL=https://ner-service-xxxx-uc.a.run.app
```

Then deploy normally:
```bash
docker-compose run workflow python deploy/run.py --target k8s --action setup-secrets
```

### Cloud Run Deployment

Not applicable - the backend itself would be deployed differently, but it would need these env vars.

## Local Development

### Option 1: Use Cloud Run (Recommended for Production-like Testing)

```bash
# In docker-compose.yml backend service, add:
environment:
  - USE_CLOUDRUN_NER=true
  - NER_SERVICE_URL=https://ner-service-xxxx-uc.a.run.app
```

**Advantages**: 
- Smaller image
- Faster startup
- Production parity
- Backend compute service account automatically authenticates

### Option 2: Use Local Model (For Offline Development)

If you need to develop without Cloud Run access:

1. Temporarily add back to `pyproject.toml`:
```toml
dependencies = [
    # ... existing deps ...
    "transformers>=4.30.0",
    "torch>=2.0.0",
]
```

2. Don't set `USE_CLOUDRUN_NER` (or set it to `false`)

3. Ensure the LLM model files are available at `/llm/development_plans/NER/package`

**Note**: This is NOT recommended for production deployments due to image size.

## How It Works

The `DevelopmentPlansNER` class automatically switches between modes:

```python
# From backend/app/utils/ner/development_plans_ner.py

if os.environ.get("USE_CLOUDRUN_NER", "false").lower() == "true":
    # Use Cloud Run HTTP client (no torch/transformers needed)
    self.client = CloudRunNERClient()
else:
    # Use local model (requires torch/transformers)
    self.predictor = NERPredictor(...)
```

## IAM Permissions Required

The backend compute service account needs permission to invoke the Cloud Run NER service:

```bash
# One-time setup (must be run manually)
gcloud run services add-iam-policy-binding ner-service \
  --region=us-central1 \
  --member="serviceAccount:968366835427-compute@developer.gserviceaccount.com" \
  --role="roles/run.invoker"
```

See `workflow/deploy/cloudrun/README.md` for complete IAM setup instructions.

## Verification

### 1. Check Environment Variables

```bash
# In the backend pod/container
kubectl exec -it <backend-pod> -- env | grep NER
# Should show:
# USE_CLOUDRUN_NER=true
# NER_SERVICE_URL=https://ner-service-xxxx-uc.a.run.app
```

### 2. Test the Endpoint

```bash
curl -X POST http://localhost:8000/v1/development-plans/extract-entities \
  -H "Content-Type: application/json" \
  -d '{"text": "This project requires approval under Article 50 and Section 32."}'

# Expected response:
# {
#   "article_references": ["Article 50", "Section 32"],
#   "count": 2
# }
```

### 3. Check Logs

Look for this log message on backend startup:
```
DevelopmentPlansNER using Cloud Run service
```

(If it says "using local model", the env var is not set correctly)

## Troubleshooting

### Error: "NER_SERVICE_URL environment variable not set"

**Solution**: Ensure `NER_SERVICE_URL` is set in your deployment configuration.

### Error: "Failed to get authentication token"

**Possible causes**:
1. Backend compute service account doesn't have `run.invoker` role
2. GOOGLE_APPLICATION_CREDENTIALS not properly configured

**Solution**: Run IAM setup commands from `workflow/deploy/cloudrun/README.md`

### Error: "NER service unavailable after 3 attempts"

**Possible causes**:
1. Cloud Run service is not deployed or crashed
2. Service URL is incorrect
3. Network connectivity issues

**Solution**: Check Cloud Run service status:
```bash
gcloud run services describe ner-service --region us-central1
```

## Rollback Plan

If you need to rollback to local NER model:

1. Add torch and transformers back to `pyproject.toml`
2. Rebuild backend image
3. Remove or set `USE_CLOUDRUN_NER=false`
4. Redeploy

## Performance Comparison

| Metric | Local Model | Cloud Run |
|--------|-------------|-----------|
| Backend Image Size | ~5GB | ~2GB |
| Backend Memory Usage | ~4GB | ~500MB |
| Backend Startup Time | ~60s (model loading) | ~5s |
| Inference Latency | 200-500ms | 300-600ms (includes HTTP) |
| Scalability | Limited by backend pods | Independent scaling |
| Cost Efficiency | Higher (always loaded) | Lower (scale to zero) |

## Next Steps

1. ✅ Deploy NER service to Cloud Run (see `workflow/deploy/cloudrun/README.md`)
2. ✅ Set IAM permissions (manual step)
3. ✅ Update backend deployment config with env vars
4. ✅ Rebuild and redeploy backend
5. ✅ Verify with test requests
6. Monitor Cloud Run metrics and backend logs

---

**Last Updated**: 2025-12-05
**Migration Status**: ✅ Complete

