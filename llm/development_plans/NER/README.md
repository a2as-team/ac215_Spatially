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
docker compose run --rm llm_development_plans_trainer
```

```bash
cd llm/development_plans/NER
```

# Rebuild and run the container
```bash
docker compose build llm_development_plans_trainer && docker image prune -f && docker compose run --rm llm_development_plans_trainer
```
