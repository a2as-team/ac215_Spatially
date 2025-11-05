from pathlib import Path


class PackageConfig:
    """Configuration for trainer packages to be uploaded to GCS."""

    @staticmethod
    def bucket_name():
        """GCS bucket name for trainer packages."""
        return f"spatially-model-packages"

    @staticmethod
    def pytorch_container_uri():
        """PyTorch container URI for trainer packages."""
        return "us-docker.pkg.dev/vertex-ai/training/pytorch-gpu.2-2.py310:latest"
    
    @staticmethod
    def pytorch_container_environment_variables():
        """PyTorch container environment variables for trainer packages."""
        return {
            "PJRT_DEVICE": "CUDA",
            "XLA_USE_BF16": "0",
            "USE_TORCH_XLA": "false",
        }

    @staticmethod
    def ner_trainer_package():
        """NER trainer package configuration."""
        project_root = Path(__file__).parent.parent
        package_dir = project_root / "llm" / "development_plans" / "NER" / "package"

        return {
            "name": "ner-trainer",
            "package_dir": package_dir,
            "gcs_path": "ner-trainer.tar.gz",
            "container_uri": PackageConfig.pytorch_container_uri(),
            "bucket": PackageConfig.bucket_name(),
        }

    @staticmethod
    def packages():
        """Return all trainer packages to be uploaded."""
        return [
            PackageConfig.ner_trainer_package(),
            # Add more packages here as you create them:
            # PackageConfig.classification_trainer_package(gcp_project),
            # PackageConfig.segmentation_trainer_package(gcp_project),
        ]
