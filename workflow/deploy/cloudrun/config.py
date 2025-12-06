"""
Cloud Run Service Configurations

Service-specific configurations for Cloud Run deployments.
"""
import os
import sys
from pathlib import Path

# Add registry to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from registry.config import RegistryConfig


class CloudRunConfig:
    """Configuration for Cloud Run services"""

    @staticmethod
    def ner_service_config(gcp_region: str, gcp_project: str) -> dict:
        """
        Configuration for NER inference service.

        Returns:
            Service configuration dict for CloudRunService class
        """
        image_config = RegistryConfig.ner_service_image(gcp_region, gcp_project)

        return {
            "name": "ner-service",
            "image_uri": image_config["image_uri"],
            "region": gcp_region,
            "project": gcp_project,
            "env_vars": {
                "GCP_PROJECT": gcp_project,
                "GCP_REGION": gcp_region,
                "FINETUNE_GCS_BUCKET": os.environ.get(
                    "FINETUNE_GCS_BUCKET",
                    "spatially-us-central-1-model-training"
                ),
                "MODEL_GCS_PATH": "ner_model_output/model/ner_model",
                "TOKENIZER_GCS_PATH": "ner_model_output/model/ner_tokenizer",
                "LOG_LEVEL": "INFO",
            },
            # Resource configuration
            "memory": "2Gi",           # NER model needs decent memory
            "cpu": "2",                 # 2 vCPUs for faster inference
            "max_instances": 10,        # Scale up to 10 instances
            "min_instances": 0,         # Scale to zero when not used (cost savings)
            "concurrency": 10,          # 10 concurrent requests per instance
            "timeout": 300,             # 5 min timeout for long texts
            "port": 8080,
            "allow_unauthenticated": False,  # Require authentication
        }

    @staticmethod
    def get_service_configs(gcp_region: str, gcp_project: str) -> dict:
        """
        Get all available Cloud Run service configurations.

        Args:
            gcp_region: GCP region
            gcp_project: GCP project ID

        Returns:
            Dict mapping service name to configuration
        """
        return {
            "ner-service": CloudRunConfig.ner_service_config(gcp_region, gcp_project),
            # Add more services here as needed
        }
