"""
Configuration for NER Cloud Run Service

Environment-based configuration using Pydantic settings.
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class ServiceConfig(BaseSettings):
    """
    Configuration for the NER Cloud Run service.

    All settings can be overridden via environment variables.
    """

    # GCP Configuration
    gcp_project: str = os.environ.get("GCP_PROJECT", "")
    gcp_region: str = os.environ.get("GCP_REGION", "us-central1")

    # Model Storage Configuration
    finetune_gcs_bucket: str = os.environ.get(
        "FINETUNE_GCS_BUCKET",
        "spatially-us-central-1-model-training"
    )
    model_gcs_path: str = os.environ.get(
        "MODEL_GCS_PATH",
        "ner_model_output/model/ner_model"
    )
    tokenizer_gcs_path: str = os.environ.get(
        "TOKENIZER_GCS_PATH",
        "ner_model_output/model/ner_tokenizer"
    )

    # Service Configuration
    port: int = int(os.environ.get("PORT", "8080"))
    log_level: str = os.environ.get("LOG_LEVEL", "INFO")

    # Application metadata
    service_name: str = "ner-service"
    version: str = "1.0.0"

    class Config:
        case_sensitive = False
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global config instance
config = ServiceConfig()
