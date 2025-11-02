"""
Vertex AI Job Submission Scripts

This module contains scripts for submitting various jobs to Vertex AI.
Jobs are organized by type:

- finetune/: Fine-tuning jobs for ML models
  - development_plans_ner: NER model fine-tuning for development plans

Each job uses Docker containers from Artifact Registry and can be
triggered manually or via GitHub Actions.

Common utilities:
- base_job.BaseJob: Base class with common GCP configuration and helpers
"""
