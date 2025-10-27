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

## Quick Start with Docker

```bash
cd llm/development_plans/NER

# Build the image
docker build -t development-plans-ner-trainer . && docker builder prune -f

# Run training with GCS data (default)
docker run -it --rm \
  -v $(pwd):/app \
  -v $(pwd)/../../../secrets:/secrets:ro \
  --env-file ../../../secrets/ac215-spatially-project.env \
  -e GOOGLE_APPLICATION_CREDENTIALS=/secrets/ac215-spatially-storage-accessor-keys.json \
  development-plans-ner-trainer

# Run with custom parameters
docker run -it --rm \
  -v $(pwd):/app \
  -v $(pwd)/../../../secrets:/secrets:ro \
  --env-file ../../../secrets/ac215-spatially-project.env \
  -e GOOGLE_APPLICATION_CREDENTIALS=/secrets/ac215-spatially-storage-accessor-keys.json \
  development-plans-ner-trainer \
  python run.py --epochs 10 --batch-size 16

# Run with local JSON file
docker run -it --rm \
  -v $(pwd):/app \
  -v $(pwd)/../../../secrets:/secrets:ro \
  --env-file ../../../secrets/ac215-spatially-project.env \
  -e GOOGLE_APPLICATION_CREDENTIALS=/secrets/ac215-spatially-storage-accessor-keys.json \
  development-plans-ner-trainer \
  python run.py --json-path tmp/sample-bpda-data.json
```

**Volume Mounts:**
- `$(pwd):/app` - Mount entire project directory (allows live code editing)
- `secrets/` - For GCP credentials (read-only)


## Prerequisites

### Environment Variables

The following environment variables must be set:

```bash
export GCP_PROJECT="your-project-id"
export GCS_BUCKET_NAME="your-bucket-name"
export WANDB_API_KEY="your-wandb-api-key"
```

**Getting your Wandb API Key:**
1. Sign up at [wandb.ai](https://wandb.ai)
2. Go to Settings → API Keys
3. Copy your API key

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

### Quick Start up

```bash
# Navigate to NER directory
cd llm/development_plans/NER

# Install dependencies
uv pip install -r pyproject.toml
```

## Usage

### Training from GCS Storage (Default)

By default, the trainer loads data from multiple JSON files in GCS - ideal for production:

```bash
# Set required environment variables
export GCP_PROJECT="your-project-id"
export GCS_BUCKET_NAME="your-bucket-name"
export WANDB_API_KEY="your-wandb-api-key"

# Train using data from GCS (default - no --json-path needed!)
python run.py

# With custom hyperparameters
python run.py --epochs 5 --batch-size 16

# With custom model
python run.py --epochs 5 --model-name bert-base-uncased
```

**GCS Configuration:**
- Training data should be stored in: `gs://{bucket}/development_plans/ner_training_data/`
- All JSON files in this path will be automatically downloaded and combined
- Supports multiple JSON files (automatically merged into a single dataset)

### Training from Local File

For development or testing, provide a local JSON file path:

```bash
# Use local file by specifying --json-path
python run.py --json-path tmp/sample-bpda-data.json

# With custom parameters
python run.py --json-path tmp/sample-bpda-data.json --epochs 3 --batch-size 4
```

**Smart Data Source Detection:**
- **No `--json-path`** → Uses GCS storage (production mode)
- **With `--json-path`** → Uses local file (development mode)

### Command-Line Options

```bash
python run.py --help
```

**Available Arguments:**
- `--json-path`: Path to local JSON file (optional - if omitted, uses GCS storage)
- `--batch-size`: Training batch size (default: 8)
- `--epochs`: Number of training epochs (default: 3)
- `--learning-rate`: Learning rate for optimizer (default: 2e-5)
- `--model-name`: Pretrained model from HuggingFace (default: nlpaueb/legal-bert-base-uncased)

**Wandb Integration:**
- Project name is automatically set to `development-plans-ner`
- Run names are auto-generated with format: `{model}-e{epochs}-bs{batch_size}-{timestamp}`
  - Example: `legal-bert-base-uncased-e5-bs16-20250126-143022`
- Runs are automatically tagged with: `ner`, `development-plans`, `token-classification`, `spatially`
- All runs viewable at: https://wandb.ai/your-username/development-plans-ner

### Programmatic Usage

**Training with GCS data (default):**
```python
from train import Trainer
import os

# Set GCP credentials
os.environ['GCP_PROJECT'] = 'your-project-id'
os.environ['GCS_BUCKET_NAME'] = 'your-bucket-name'
os.environ['WANDB_API_KEY'] = 'your-wandb-api-key'

trainer = Trainer(model_name="nlpaueb/legal-bert-base-uncased")
trainer.train(
    batch_size=16, 
    epochs=5, 
    learning_rate=3e-5,
    use_gcs=True  # Load from GCS
)
```

**Training with local file:**
```python
from train import Trainer
from pathlib import Path
import os

os.environ['WANDB_API_KEY'] = 'your-wandb-api-key'

trainer = Trainer(model_name="nlpaueb/legal-bert-base-uncased")
trainer.train(
    batch_size=16, 
    epochs=5, 
    learning_rate=3e-5,
    use_gcs=False,
    json_path=Path("tmp/sample-bpda-data.json")
)
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

1. **Data Loading**: 
   - **GCS Mode**: Downloads and combines multiple JSON files from `gs://{bucket}/development_plans/label_studio_annotations/`
   - **Local Mode**: Reads from a single local JSON file
2. **Smart Chunking**: Handle long documents by chunking while preserving entity boundaries
3. **Tokenization**: Convert text to model-ready tokens with BIO label alignment
4. **Training**: Fine-tune BERT model using AdamW optimizer
5. **Evaluation**: Validate on held-out test set (10% split)
6. **Model Saving**: Persist trained model to `tmp/ner_model/`

### Key Features

**Multi-File Support**: The trainer can now process multiple JSON files from GCS and automatically combine them into a single training dataset. This is particularly useful when:
- You have annotations split across multiple Label Studio exports
- You want to incrementally add more training data
- You're working with a team that produces separate annotation files

**Flexible Data Sources**: The same codebase supports both:
- Production training from GCS (recommended for reproducibility)
- Local development with sample files (faster iteration)

## Weights & Biases Tracking

All training runs are automatically logged to Weights & Biases with comprehensive tracking:

### What Gets Logged

**Configuration (logged at start):**
- Model name and architecture
- Hyperparameters (batch size, learning rate, epochs)
- Dataset split sizes (train/val)
- Number of entity labels
- Device information
- Data source (GCS or local)

**During Training:**
- Batch loss (every 10 steps)
- Epoch training loss (end of each epoch)
- Epoch validation loss (end of each epoch)
- Global step counter

**After Training:**
- Trained model artifacts (automatically uploaded)
- Full training configuration
- Timestamped checkpoints

**Tags Applied:**
- `ner`
- `development-plans`
- `token-classification`
- `spatially`

### Viewing Results

After training, view your results at:
- Dashboard: `https://wandb.ai/your-username/development-plans-ner`
- Direct link printed at end of training

### Run Naming Convention

Runs are automatically named with this format:
```
{model-name}-e{epochs}-bs{batch_size}-{timestamp}
```

Examples:
- `legal-bert-base-uncased-e3-bs8-20250126-143022`
- `bert-base-uncased-e5-bs16-20250126-151530`

This makes it easy to identify and compare experiments.

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
