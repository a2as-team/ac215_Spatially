# Development Plans NER (Named Entity Recognition)

This module trains a Named Entity Recognition model to extract key information from development plan documents using transformer-based token classification.

## Overview

The NER model identifies and extracts the following entities from development plan texts:

| Entity | Description |
|--------|-------------|
| `CONSTRUCTION_DETAILS` | Information about building specifications, dimensions, materials |
| `PROPERTY_USAGE` | Intended use of the property (residential, commercial, mixed-use, etc.) |
| `ZONING_DISTRICT` | Zoning classification or district designation |
| `ZONING_RELIEF` | Variances, special permits, or zoning relief requests |
| `ARTICLE_REFERENCE` | References to zoning articles or ordinances |
| `EXPECTED_IMPACT` | Anticipated effects on neighborhood, traffic, environment |
| `LOCATION_CONTEXT` | Geographic context and location descriptors |

## Architecture

- **Base Model**: `nlpaueb/legal-bert-base-uncased` (legal domain pre-trained BERT)
- **Task**: Token classification with BIO tagging scheme
- **Framework**: HuggingFace Transformers + PyTorch
- **Training Data Format**: Label Studio JSON exports

## Prerequisites

### Training Data

Training data should be annotated using Label Studio and exported as JSON. Place the exported file in `tmp/sample-bpda-data.json`.

**Data Format:**
```json
[
  {
    "data": {
      "text": "The project proposes a 5-story residential building..."
    },
    "annotations": [
      {
        "result": [
          {
            "value": {
              "start": 20,
              "end": 44,
              "labels": ["CONSTRUCTION_DETAILS"]
            }
          }
        ]
      }
    ]
  }
]
```

## Installation

### Local Setup

```bash
# Navigate to NER directory
cd llm/development_plans/NER

# Install dependencies
uv pip install -r pyproject.toml
```

## Usage

### Training Locally

```bash
# Ensure training data is available
ls tmp/sample-bpda-data.json

# Run training
python -c "from train import Trainer; trainer = Trainer(); trainer.train()"
```

**Training Parameters:**
- `batch_size`: Training batch size (default: 8)
- `epochs`: Number of training epochs (default: 3)
- `learning_rate`: Learning rate for AdamW optimizer (default: 2e-5)

**Example with custom parameters:**
```python
from train import Trainer

trainer = Trainer(model_name="nlpaueb/legal-bert-base-uncased")
trainer.train(batch_size=16, epochs=5, learning_rate=3e-5)
```

### Training with Docker

Build and run the Docker container:

```bash
# Build the image
docker build -t spatially-ner-trainer .

# Run training
docker run --rm \
  -v $(pwd)/tmp:/app/tmp \
  -v $(pwd)/models:/app/models \
  spatially-ner-trainer
```

### Training with Docker Compose

```bash
# From project root, run NER training
docker compose --profile model-training up ner-trainer

# Or as part of full pipeline
docker compose --profile full-pipeline up
```

## Project Structure

```
llm/development_plans/NER/
├── config/
│   ├── __init__.py
│   └── labels.py           # NER label definitions
├── tmp/
│   └── sample-bpda-data.json  # Training data (Label Studio export)
├── models/                 # Saved model checkpoints (created during training)
├── outputs/               # Training logs and outputs
├── train.py              # Main training script
├── Dockerfile           # Container definition
├── pyproject.toml      # Python dependencies
└── README.md          # This file
```

## Training Pipeline

The training process consists of the following steps:

1. **Data Loading**: Import Label Studio JSON annotations
2. **Smart Chunking**: Handle long documents by chunking while preserving entity boundaries
3. **Tokenization**: Convert text to model-ready tokens with BIO label alignment
4. **Training**: Fine-tune BERT model using AdamW optimizer
5. **Evaluation**: Validate on held-out test set (10% split)
6. **Model Saving**: Persist trained model to `tmp/ner_model/`

## Device Support

The trainer automatically selects the best available device:

1. **MPS** (Apple Silicon GPU) - if available
2. **CUDA** (NVIDIA GPU) - if available
3. **CPU** - fallback

To force a specific device:
```python
trainer = Trainer(device="cpu")
```

## Model Output

After training, the model and tokenizer are saved to:
- Model: `tmp/ner_model/`
- Tokenizer: `tmp/ner_tokenizer/`

These can be loaded for inference:
```python
from transformers import AutoModelForTokenClassification, AutoTokenizer

model = AutoModelForTokenClassification.from_pretrained("tmp/ner_model")
tokenizer = AutoTokenizer.from_pretrained("tmp/ner_tokenizer")
```

## Integration with Docker Compose

The NER trainer is integrated into the MLOps pipeline as Stage 3 (Model Training):

```yaml
services:
  ner-trainer:
    build:
      context: ./llm/development_plans/NER
    volumes:
      - ./llm/development_plans/NER/tmp:/app/tmp
      - ./llm/models:/app/models
    profiles:
      - model-training
      - full-pipeline
```

The trained models are persisted to `./llm/models/` where they can be accessed by the backend API for inference.

## Notes

- Long documents are automatically chunked to fit within model's max token length (512 for BERT)
- Entity boundaries are preserved during chunking
- BIO tagging scheme is used (B-ENTITY, I-ENTITY, O)
- Special tokens are masked with label `-100` during training
- Training uses dynamic padding for efficiency
