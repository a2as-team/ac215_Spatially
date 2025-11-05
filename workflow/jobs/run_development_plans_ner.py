#!/usr/bin/env python3
"""
Submit NER training job for development plans to Vertex AI.

Workflow:
1. Manually label data in Label Studio
2. Export annotations to GCS (development_plans/ner_training_data/)
3. Upload trainer package to GCS:
   python packages/run.py --packages ner-trainer
4. Run this script to train model on Vertex AI
5. Model is saved to GCS

Prerequisites:
1. Upload the trainer package to GCS:
   python packages/run.py --packages ner-trainer

2. Ensure labeled data exists in GCS:
   gs://{bucket}/development_plans/ner_training_data/

3. WANDB_API_KEY must be set in environment (loaded from secrets/ac215-spatially-project.env)

Usage:
    python jobs/run_development_plans_ner.py --epochs 5
"""
import sys
from pathlib import Path

# Add workflow directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from jobs.finetune.development_plans_ner import DevelopmentPlansNERJob
from utils.smart_arg_parser import SmartArgItem, SmartArgParser


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
        "sync": SmartArgItem(
            flags=["--sync"],
            prompt="Wait for job to complete (default: False)",
            arg_type=bool,
            default=False,
            required=False,
        ),
    }

    parser = SmartArgParser(schema, description="Submit NER training job to Vertex AI")
    args = parser.parse()

    # Create job instance with training parameters
    # Machine type and accelerator settings use defaults from DevelopmentPlansNERJob
    job = DevelopmentPlansNERJob(
        batch_size=args["batch_size"],
        epochs=args["epochs"],
        learning_rate=args["learning_rate"],
        model_name=args["model_name"],
    )

    print(f"\n📦 Using Python package from GCS")
    print("⚠️  Make sure you've uploaded the package first:")
    print("    python packages/run.py --packages ner-trainer\n")

    # Run the job (creates and runs in one step)
    job.run_job(sync=args["sync"])


if __name__ == "__main__":
    main()
