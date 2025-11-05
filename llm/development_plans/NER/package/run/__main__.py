#!/usr/bin/env python3
"""
Training script for NER model.
Supports loading training data from either local files or GCS storage.
"""
import sys
import logging
from trainer.train import Trainer
from pathlib import Path
from utils.smart_arg_parser import SmartArgItem, SmartArgParser


def main():
    # Configure logging to use stdout instead of stderr
    # This prevents logs from appearing as errors in GCP
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )

    # Redirect stderr to stdout for library logs
    sys.stderr = sys.stdout
    # Define argument schema
    schema = {
        "json_path": SmartArgItem(
            flags=["--json-path"],
            prompt="Path to local JSON file (leave empty to use GCS)",
            arg_type=str,
            default=None,
            required=False
        ),
        "batch_size": SmartArgItem(
            flags=["--batch-size"],
            prompt="Training batch size",
            arg_type=int,
            default=4,
            required=False
        ),
        "epochs": SmartArgItem(
            flags=["--epochs"],
            prompt="Number of training epochs",
            arg_type=int,
            default=1,
            required=False
        ),
        "learning_rate": SmartArgItem(
            flags=["--learning-rate"],
            prompt="Learning rate for optimizer",
            arg_type=float,
            default=2e-5,
            required=False
        ),
        "model_name": SmartArgItem(
            flags=["--model-name"],
            prompt="Pretrained model name from HuggingFace",
            arg_type=str,
            default="nlpaueb/legal-bert-base-uncased",
            required=False
        ),
    }

    # Parse arguments
    parser = SmartArgParser(schema, description="Train NER model for development plans")
    args = parser.parse()

    print("=" * 80)
    print("NER Model Training")
    print("=" * 80)
    data_source = 'GCS Storage' if args["json_path"] is None else f'Local file: {args["json_path"]}'
    print(f"Data source: {data_source}")
    print(f"Model: {args['model_name']}")
    print(f"Batch size: {args['batch_size']}")
    print(f"Epochs: {args['epochs']}")
    print(f"Learning rate: {args['learning_rate']}")
    print(f"Device: auto")
    print("=" * 80)

    # Initialize trainer
    trainer = Trainer(device=None, model_name=args["model_name"])

    # Train the model
    trainer.train(
        batch_size=args["batch_size"],
        epochs=args["epochs"],
        learning_rate=args["learning_rate"],
        json_path=Path(args["json_path"]) if args["json_path"] else None,
    )

    import os
    aip_model_dir = os.environ.get("AIP_MODEL_DIR")

    print("\n" + "=" * 80)
    print("✅ Training completed!")
    print(f"Local: tmp/ner_model, tmp/ner_tokenizer")
    if aip_model_dir:
        print(f"GCS: {aip_model_dir}ner_model")
        print(f"GCS: {aip_model_dir}ner_tokenizer")
    print("View results at: https://wandb.ai")
    print("=" * 80)


if __name__ == "__main__":
    main()
