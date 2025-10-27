#!/usr/bin/env python3
"""
Training script for NER model.
Supports loading training data from either local files or GCS storage.
"""
from train import Trainer
from pathlib import Path
from utils.smart_arg_parser import SmartArgItem, SmartArgParser


def main():
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
            default=3,
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
        "gradient_accumulation_steps": SmartArgItem(
            flags=["--gradient-accumulation-steps"],
            prompt="Number of steps to accumulate gradients",
            arg_type=int,
            default=4,
            required=False
        ),
    }
    
    # Parse arguments
    parser = SmartArgParser(schema, description="Train NER model for development plans")
    args = parser.parse()
    
    # Automatically determine data source
    use_gcs = args["json_path"] is None
    
    print("=" * 80)
    print("NER Model Training")
    print("=" * 80)
    print(f"Data source: {'GCS Storage' if use_gcs else f'Local file: {args['json_path']}'}")
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
        use_gcs=use_gcs,
        json_path=Path(args["json_path"]) if args["json_path"] else None,
        gradient_accumulation_steps=args["gradient_accumulation_steps"],
    )
    
    print("\n" + "=" * 80)
    print("✅ Training completed!")
    print("Model saved to: tmp/ner_model")
    print("Tokenizer saved to: tmp/ner_tokenizer")
    print("View results at: https://wandb.ai")
    print("=" * 80)


if __name__ == "__main__":
    main()
