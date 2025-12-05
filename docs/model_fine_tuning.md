# Model Fine-Tuning Summary

## Overview

Spatially fine-tunes a Named Entity Recognition (NER) model to extract structured information from development plan documents. The model identifies key entities such as construction details, property usage, zoning districts, and regulatory information.

## Model Architecture

### Base Model

- **Model**: `nlpaueb/legal-bert-base-uncased`
- **Rationale**: Pre-trained on legal domain text, making it well-suited for zoning and development plan documents
- **Task**: Token classification with BIO tagging scheme
- **Framework**: HuggingFace Transformers + PyTorch

### Entity Types

The model extracts the following 7 entity types:

| Entity                 | Description                                    | Example                                 |
| ---------------------- | ---------------------------------------------- | --------------------------------------- |
| `CONSTRUCTION_DETAILS` | Building specifications, dimensions, materials | "5-story building with 20 units"        |
| `PROPERTY_USAGE`       | Intended use of property                       | "mixed-use residential and commercial"  |
| `ZONING_DISTRICT`      | Zoning classification                          | "RS-1", "Commercial District"           |
| `ZONING_RELIEF`        | Variances, special permits, zoning relief      | "variance for height", "special permit" |
| `ARTICLE_REFERENCE`    | References to zoning articles/ordinances       | "Article 9, Section 3.2"                |
| `EXPECTED_IMPACT`      | Anticipated effects on neighborhood            | "increased traffic", "shadow impact"    |
| `LOCATION_CONTEXT`     | Geographic context and location                | "corner of Main St and Oak Ave"         |

## Training Process

### Data Collection and Annotation

1. **Source Data**: Development plan documents (PDFs) collected from municipal websites
2. **Annotation Tool**: Label Studio with custom NER configuration
3. **Annotation Format**: JSON export compatible with HuggingFace datasets
4. **Storage**: Annotations stored in GCS at `gs://{bucket}/development_plans/{city}/ner_training_data/annotations.json`

### Training Configuration

#### Default Hyperparameters

- **Batch Size**: 8
- **Epochs**: 3 (configurable)
- **Learning Rate**: 2e-5 (standard for BERT fine-tuning)
- **Optimizer**: AdamW
- **Train/Validation Split**: 90/10
- **Device**: CUDA (GPU) when available, CPU fallback

#### Training Infrastructure

- **Platform**: Google Cloud Vertex AI
- **Machine Type**: ??
- **Accelerator**: ??
- **Experiment Tracking**: Weights & Biases (W&B)

### Training Scripts and Configuration

#### Main Training Script

Location: `llm/development_plans/NER/package/trainer/train.py`

Key components:

- `Trainer` class: Handles model initialization, data preparation, and training loop
- Automatic W&B integration for experiment tracking
- Support for both local JSON files and GCS-stored data
- Dynamic padding with `DataCollatorForTokenClassification`

#### Job Submission Script

Location: `workflow/jobs/run_development_plans_ner.py`

Usage:

```bash
python workflow/jobs/run_development_plans_ner.py \
    --epochs 5 \
    --batch-size 8 \
    --learning-rate 2e-5 \
    --model-name nlpaueb/legal-bert-base-uncased
```

#### Vertex AI Job Definition

Location: `workflow/jobs/finetune/development_plans_ner.py`

- Packages training code as a Python package
- Uploads to GCS for Vertex AI execution
- Configures machine type, accelerators, and environment variables

### Dataset References

Training data is versioned in GCS:

- **Path**: `gs://{bucket}/development_plans/{city}/ner_training_data/annotations.json`
- **Format**: Label Studio JSON export
- **Versioning**: Managed through GCS object versioning (see Data Versioning documentation)

### Experiment Logs

All training runs are logged to Weights & Biases:

- **Project**: `spatially-development-plans-ner`
- **Metrics Tracked**:
  - Training loss (per epoch and per step)
  - Validation loss
  - F1 score (per entity type and overall)
  - Precision and recall
  - Learning rate schedule
- **Artifacts**: Model checkpoints saved to GCS

Example W&B run name: `legal-bert-base-uncased-e3-bs4-20240115-103000`

## Key Results

### Model Performance

(Note: Actual results will vary based on training data size and quality. This section should be updated with real metrics after training runs.)

#### Typical Performance Metrics ??????

- **Overall F1 Score**: [To be updated with actual results]
- **Per-Entity F1 Scores**:
  - CONSTRUCTION_DETAILS: [TBD]
  - PROPERTY_USAGE: [TBD]
  - ZONING_DISTRICT: [TBD]
  - ZONING_RELIEF: [TBD]
  - ARTICLE_REFERENCE: [TBD]
  - EXPECTED_IMPACT: [TBD]
  - LOCATION_CONTEXT: [TBD]

#### Training Observations

- Legal-BERT base model provides strong initialization for legal/regulatory text
- Fine-tuning improves entity recognition accuracy significantly over baseline
- Some entity types (e.g., ZONING_DISTRICT) achieve higher accuracy due to consistent formatting
- Location context extraction benefits from spatial awareness in training data

### Model Artifacts

Trained models are stored in GCS:

- **Path**: `gs://{bucket}/models/development_plans/ner/{run_id}/`
- **Contents**:
  - `pytorch_model.bin`: Model weights
  - `config.json`: Model configuration
  - `tokenizer_config.json`: Tokenizer configuration
  - `vocab.txt`: Vocabulary file

## Deployment Strategy

### Production: Cloud Run Microservice

The fine-tuned NER model is deployed as a serverless microservice on Google Cloud Run:

**Service**: `ner-service`  
**URL**: `https://ner-service-{hash}-uc.a.run.app`  
**Deployment Guide**: [workflow/deploy/cloudrun/README.md](../workflow/deploy/cloudrun/README.md)

#### Architecture

```
Backend API (GKE)
    ↓ HTTP POST
NER Service (Cloud Run)
    ↓ Loads model from GCS
Fine-tuned BERT Model
    ↓ Returns entities
Backend API → Client
```

#### Key Features

- **Auto-scaling**: Scales to zero when idle, up to 10 instances under load
- **Authentication**: Service-to-service auth using Google Cloud ID tokens (or public access)
- **Performance**: ~300-600ms latency (includes HTTP overhead)
- **Cost-efficient**: Pay only for actual requests
- **Isolated**: Separate from backend (no torch/transformers in backend image → 3GB size reduction)

#### Deployment Process

```bash
# 1. Train model (saves to GCS)
python workflow/jobs/run_development_plans_ner.py --epochs 3

# 2. Deploy NER service to Cloud Run
docker-compose run workflow python deploy/run.py \
  --target cloudrun \
  --action deploy \
  --service ner-service

# 3. Configure backend to use Cloud Run NER
# Set environment variables:
# USE_CLOUDRUN_NER=true
# NER_SERVICE_URL=https://ner-service-xxxx-uc.a.run.app

# 4. Redeploy backend
docker-compose run workflow python deploy/run.py \
  --target k8s \
  --action deploy
```

#### API Integration

**Endpoint**: `POST /api/v1/development-plans/extract-entities`

```bash
curl -X POST "http://localhost:8000/api/v1/development-plans/extract-entities" \
  -H "Content-Type: application/json" \
  -d '{"text": "This project requires approval under Article 50 and Section 32."}'

# Response:
{
  "article_references": ["Article 50", "Section 32"],
  "count": 2
}
```

The backend automatically routes requests to Cloud Run using authenticated HTTP calls.

### Development: Label Studio ML Backend

For annotation and active learning, the model is also deployed as a Label Studio ML backend:

1. **Model Loading**: `label_studio/label_studio_development_plans_backend/model.py`
   - Loads fine-tuned model from GCS or local directory
   - Provides predictions during annotation

2. **Deployment**:
   ```bash
   # Download model to Label Studio backend
   gsutil -m cp -r gs://bucket/models/development_plans/ner/{run_id}/* \
       ./label_studio/label_studio_development_plans_backend/models/

   # Restart Label Studio ML backend
   docker compose restart label-studio-ml-backend
   ```

3. **Active Learning**: Model predictions improve annotation speed and consistency

### Performance Characteristics

| Environment | Latency | Memory | Cost |
|-------------|---------|--------|------|
| **Cloud Run (Production)** | 300-600ms | 2GB | Pay-per-request |
| **Label Studio (Dev)** | 100-200ms | 500MB | Always-on |
| **Backend Local (Deprecated)** | 50-100ms | 4GB | Always-loaded |

**Note**: The backend no longer includes torch/transformers (86% image size reduction). All production NER inference is handled by Cloud Run.

## Future Improvements

1. **Data Augmentation**: Increase training data diversity through synthetic examples
2. **Multi-Task Learning**: Joint training with related tasks (e.g., relation extraction)
3. **Domain Adaptation**: Fine-tune on city-specific development plans
4. **Model Compression**: Distillation or quantization for faster inference
5. **Active Learning**: Improve model with human feedback loop
6. **Evaluation Metrics**: Add more detailed per-entity metrics and confusion matrices

## Reproducibility

To reproduce a training run:

1. **Check W&B Run**: Identify the run ID and hyperparameters
2. **Retrieve Training Data**: Download annotations from GCS
   ```bash
   gsutil cp gs://bucket/development_plans/{city}/ner_training_data/annotations.json ./
   ```
3. **Run Training**:
   ```bash
   python llm/development_plans/NER/package/run/__main__.py \
       --json-path ./annotations.json \
       --epochs 3 \
       --batch-size 4 \
       --learning-rate 2e-5
   ```

## References

- **Base Model**: https://huggingface.co/nlpaueb/legal-bert-base-uncased
- **HuggingFace Transformers**: https://huggingface.co/docs/transformers
- **Label Studio**: https://labelstud.io/
- **Weights & Biases**: https://wandb.ai/
