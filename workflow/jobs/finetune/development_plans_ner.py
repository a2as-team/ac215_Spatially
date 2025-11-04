#!/usr/bin/env python3
"""
Submit NER training job for development plans to Vertex AI.

Workflow:
1. Manually label data in Label Studio
2. Export annotations to GCS (development_plans/ner_training_data/)
3. Upload trainer package to GCS:
   cd workflow && python packages/run.py --packages ner-trainer
4. Run this script to train model on Vertex AI
5. Model is saved to GCS

Prerequisites:
1. Upload the trainer package to GCS:
   cd workflow && python packages/run.py --packages ner-trainer

2. Ensure labeled data exists in GCS:
   gs://{bucket}/development_plans/ner_training_data/

3. Set WANDB_API_KEY environment variable for Weights & Biases logging

Usage:
    python workflow/jobs/finetune/development_plans_ner.py --epochs 5
"""
import sys
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from jobs.base_job import BaseJob
from packages.config import PackageConfig
from utils.smart_arg_parser import SmartArgItem, SmartArgParser


class DevelopmentPlansNERJob(BaseJob):
    """Submit NER training jobs to Vertex AI."""

    def __init__(
        self,
        batch_size: int = 4,
        epochs: int = 3,
        learning_rate: float = 2e-5,
        model_name: str = "nlpaueb/legal-bert-base-uncased",
    ):
        super().__init__()
        self.batch_size = batch_size
        self.epochs = epochs
        self.learning_rate = learning_rate
        self.model_name = model_name

    def submit(
        self,
        machine_type: str = "n1-standard-4",
        accelerator_type: str = "NVIDIA_TESLA_T4",
        accelerator_count: int = 1,
        wandb_api_key: str = None,
        sync: bool = False,
    ):
        """Submit the training job to Vertex AI using Python package."""
        import google.cloud.aiplatform as aip
        import os

        # Get package configuration
        package_config = PackageConfig.ner_trainer_package()
        package_gcs_uri = f"gs://{package_config['bucket']}/{package_config['gcs_path']}"
        container_uri = package_config['container_uri']

        # Generate job name
        job_id = self.generate_uuid()
        timestamp = self.get_timestamp()
        model_short = self.model_name.split("/")[-1]
        display_name = f"ner-{model_short}-e{self.epochs}-{timestamp}-{job_id}"

        # Print configuration
        self.print_job_header("Vertex AI Python Package Training Job Configuration")
        print(f"Job name: {display_name}")
        print(f"Package URI: {package_gcs_uri}")
        print(f"Container URI: {container_uri}")
        print(f"Python module: run")
        print(f"Project: {self.GCP_PROJECT}")
        print(f"Region: {self.GCP_REGION}")
        print(f"Machine type: {machine_type}")
        print(f"Accelerator: {accelerator_type} x {accelerator_count}")
        print(f"Model: {self.model_name}")
        print(f"Batch size: {self.batch_size}")
        print(f"Epochs: {self.epochs}")
        print(f"Learning rate: {self.learning_rate}")
        print(f"Data source: {self.GCS_BUCKET_URI}/development_plans/ner_training_data/")
        print(f"Output location: {self.GCS_BUCKET_URI}/ner_model_output/")
        print("=" * 80)

        # Initialize Vertex AI
        aip.init(
            project=self.GCP_PROJECT,
            location=self.GCP_REGION,
            staging_bucket=self.GCS_BUCKET_URI
        )

        # Create custom Python package training job
        job = aip.CustomPythonPackageTrainingJob(
            display_name=display_name,
            python_package_gcs_uri=package_gcs_uri,
            python_module_name="run",
            container_uri=container_uri,
            project=self.GCP_PROJECT,
        )

        # Training arguments
        args = [
            f"--batch-size={self.batch_size}",
            f"--epochs={self.epochs}",
            f"--learning-rate={self.learning_rate}",
            f"--model-name={self.model_name}",
        ]

        # Environment variables
        environment_variables = {
            "GCP_PROJECT": self.GCP_PROJECT,
            "GCS_BUCKET_NAME": self.GCS_BUCKET_NAME,
        }

        # Add WANDB_API_KEY if provided
        if wandb_api_key:
            environment_variables["WANDB_API_KEY"] = wandb_api_key
        elif os.environ.get("WANDB_API_KEY"):
            environment_variables["WANDB_API_KEY"] = os.environ.get("WANDB_API_KEY")
            print("Using WANDB_API_KEY from environment")
        else:
            print("⚠️  Warning: WANDB_API_KEY not set. Training will fail.")

        print(f"\n🚀 Launching Python package training job on Vertex AI...")
        print(f"Sync mode: {sync} (wait for completion: {sync})")

        # Submit job
        job.run(
            args=args,
            replica_count=1,
            machine_type=machine_type,
            accelerator_type=accelerator_type,
            accelerator_count=accelerator_count,
            base_output_dir=f"{self.GCS_BUCKET_URI}/ner_model_output",
            environment_variables=environment_variables,
            sync=sync,
        )

        if sync:
            print(f"\n✅ Training job completed: {display_name}")
        else:
            print(f"\n✅ Training job submitted: {display_name}")
            print(f"\n📊 Monitor at:")
            print(f"https://console.cloud.google.com/vertex-ai/training/custom-jobs?project={self.GCP_PROJECT}")

        return job


def main():
    schema = {
        "batch_size": SmartArgItem(
            flags=["--batch-size"],
            prompt="Training batch size",
            arg_type=int,
            default=4,
            required=False,
        ),
        "epochs": SmartArgItem(
            flags=["--epochs"],
            prompt="Number of training epochs",
            arg_type=int,
            default=3,
            required=False,
        ),
        "learning_rate": SmartArgItem(
            flags=["--learning-rate"],
            prompt="Learning rate",
            arg_type=float,
            default=2e-5,
            required=False,
        ),
        "model_name": SmartArgItem(
            flags=["--model-name"],
            prompt="HuggingFace model name",
            arg_type=str,
            default="nlpaueb/legal-bert-base-uncased",
            required=False,
        ),
        "machine_type": SmartArgItem(
            flags=["--machine-type"],
            prompt="GCP machine type",
            arg_type=str,
            default="n1-standard-4",
            required=False,
        ),
        "accelerator_type": SmartArgItem(
            flags=["--accelerator-type"],
            prompt="GPU type",
            arg_type=str,
            default="NVIDIA_TESLA_T4",
            required=False,
        ),
        "accelerator_count": SmartArgItem(
            flags=["--accelerator-count"],
            prompt="Number of GPUs",
            arg_type=int,
            default=1,
            required=False,
        ),
        "wandb_api_key": SmartArgItem(
            flags=["--wandb-api-key"],
            prompt="Weights & Biases API key (optional, uses environment variable if not provided)",
            arg_type=str,
            default="",
            required=False,
        ),
        "sync": SmartArgItem(
            flags=["--sync"],
            prompt="Wait for job to complete",
            arg_type=bool,
            default=False,
            required=False,
        ),
    }

    parser = SmartArgParser(schema, description="Submit NER training job to Vertex AI")
    args = parser.parse()

    # Create and submit job
    job = DevelopmentPlansNERJob(
        batch_size=args["batch_size"],
        epochs=args["epochs"],
        learning_rate=args["learning_rate"],
        model_name=args["model_name"],
    )

    print(f"\n📦 Using Python package from GCS")
    print("⚠️  Make sure you've uploaded the package first:")
    print("    cd workflow && python packages/run.py --packages ner-trainer\n")

    job.submit(
        machine_type=args["machine_type"],
        accelerator_type=args["accelerator_type"],
        accelerator_count=args["accelerator_count"],
        wandb_api_key=args["wandb_api_key"] if args["wandb_api_key"] else None,
        sync=args["sync"],
    )


if __name__ == "__main__":
    main()
