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

### Run Training

```bash
# From project root
docker compose run --rm llm_development_plans_trainer
```

### Rebuild and Run (after code changes)

```bash
# From project root
docker compose build llm_development_plans_trainer && \
  docker image prune -f && \
  docker compose run --rm llm_development_plans_trainer
```

## Using the Trained Model (Inference)

Once trained, the model is automatically used by the development plans processor to extract entities.

### Quick Test

Test the NER predictor with sample text:

```bash
cd llm/development_plans/NER
python test_predictor.py
```

### Integration

The NER model is integrated into `data/processor/development_plans/ner_json_processor.py`:

```bash
cd data/processor/development_plans
python run.py --city boston
```

This will:
1. Load `.ner.json` files from GCS
2. Download and cache the trained NER model
3. Extract entities from each text chunk
4. Store results in PostgreSQL with pgvector embeddings

### Model Location

- **GCS Bucket**: `spatially-us-central-1-model-training`
- **Path**: `ner_model_output/model/`
- **Files**: `ner_model/` (model weights) and `ner_tokenizer/` (tokenizer config)
