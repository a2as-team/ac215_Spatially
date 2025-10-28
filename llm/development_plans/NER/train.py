from pathlib import Path
from typing import Dict
from utils.gcp_storage import GCPStorage
import os
from transformers import (
    AutoTokenizer,
    AutoModelForTokenClassification,
    DataCollatorForTokenClassification,
)
from config.labels import NER_LABELS
from datasets import Dataset
import json
import torch
from torch.utils.data import DataLoader
from torch.optim import AdamW
from tqdm.auto import tqdm
import wandb
from datetime import datetime


class Trainer:
    NULL_LABEL = "O"

    def __init__(
        self, device=None, model_name: str = "nlpaueb/legal-bert-base-uncased"
    ):
        self.model_name = model_name
        self.label_to_id = {v: i for i, v in enumerate(NER_LABELS)}
        self.id_to_label = {i: v for v, i in self.label_to_id.items()}
        self.label_to_id[self.NULL_LABEL] = len(self.label_to_id)
        if self.NULL_LABEL not in self.label_to_id:
            self.label_to_id[self.NULL_LABEL] = 0  # Make sure "O" = 0
        # we also
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForTokenClassification.from_pretrained(
            self.model_name, num_labels=len(self.label_to_id)
        )
        # Respect the input device if provided, else select 'mps' (Mac), then 'cuda', then cpu
        if device is not None:
            self.device = torch.device(device)
        elif torch.backends.mps.is_available():
            print("Using MPS device")
            self.device = torch.device("mps")
        elif torch.cuda.is_available():
            print("Using CUDA device")
            self.device = torch.device("cuda")
        else:
            print("Using CPU device")
            self.device = torch.device("cpu")
        self.model.to(self.device)
        self.gcp_project = os.environ.get("GCP_PROJECT")
        if not self.gcp_project:
            raise ValueError("GCP_PROJECT environment variable not set")
        self.bucket_name = os.environ.get("GCS_BUCKET_NAME")
        if not self.bucket_name:
            raise ValueError("GCS_BUCKET_NAME environment variable not set")
        self.gcp_storage = GCPStorage(gcp_project=self.gcp_project, bucket_name=self.bucket_name)
        # Validate WANDB_API_KEY is set (wandb.init() will use it automatically)
        if not os.environ.get("WANDB_API_KEY"):
            raise ValueError("WANDB_API_KEY environment variable not set")
    
    @classmethod
    def label_studio_annotation_gcs_storage_path(cls) -> str:
        """
        Return the label studio annotation GCS storage path.
        """
        return "development_plans/ner_training_data/"
    
    def import_gcs_annotation_data(self) -> Dataset:
        """
        Import the annotation data from GCS and combine all JSON files into a single dataset.
        Returns a Hugging Face Dataset with tokens and labels.
        """
        print("📥 Downloading annotation files from GCS...")
        files = self.gcp_storage.list_files(self.label_studio_annotation_gcs_storage_path())

        if not files:
            raise ValueError(f"No files found in GCS path: {self.label_studio_annotation_gcs_storage_path()}")

        print(f"Found {len(files)} JSON files in GCS")

        all_json_data = []
        for file in files:
            print(f"  - Downloading {file}")
            json_blob = self.gcp_storage.get_blob(file)
            json_data = json.loads(json_blob.download_as_text())

            # Transform Label Studio annotation object to expected format
            # Input format: {"id": X, "result": [...], "task": {"data": {"text": "..."}}}
            # Expected format: {"data": {"text": "..."}, "annotations": [{"result": [...]}]}
            if isinstance(json_data, dict) and "task" in json_data and "result" in json_data:
                transformed = {
                    "data": json_data["task"]["data"],
                    "annotations": [{"result": json_data["result"]}]
                }
                all_json_data.append(transformed)
            elif isinstance(json_data, list):
                # If it's a list, transform each item
                for item in json_data:
                    if isinstance(item, dict) and "task" in item and "result" in item:
                        transformed = {
                            "data": item["task"]["data"],
                            "annotations": [{"result": item["result"]}]
                        }
                        all_json_data.append(transformed)
                    else:
                        # Assume it's already in the correct format
                        all_json_data.append(item)
            else:
                # Assume it's already in the correct format
                all_json_data.append(json_data)

        print(f"✅ Downloaded {len(all_json_data)} annotation entries from {len(files)} files")

        # Process all the combined data
        return self.import_label_studio_data_from_json_data(all_json_data)
    
            
    def import_label_studio_data_from_single_json(
        self, json_path: Path = Path("tmp/sample-bpda-data.json")
    ) -> Dataset:
        """Load a Label Studio JSON file from local path and convert it to a Hugging Face Dataset."""
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return self.import_label_studio_data_from_json_data(data)
    
    def import_label_studio_data_from_json_data(self, data: list) -> Dataset:
        """
        Convert Label Studio JSON data to a Hugging Face Dataset.
        Args:
            data: List of Label Studio annotation entries
        Returns:
            Dataset with tokens and labels
        """
        # Step 1. Smart chunking (handles long or short texts)
        # this will handle long texts by smartly chunking them into smaller segments
        chunked_dataset = self.preprocess_label_studio_data_for_long_text(json_data=data)

        # Step 2. Convert each chunk to tokens + labels
        examples = [
            self.process_one_label_studio_entry(entry) for entry in chunked_dataset
        ]
        # examples would be a list of dictionaries with keys "tokens" and "labels"
        # each item in the list is a chunk of the original text
        examples = [ex for ex in examples if ex is not None]
        print(f"Prepared {len(examples)} examples from {len(chunked_dataset)} chunks")

        return Dataset.from_list(examples)

    def preprocess_label_studio_data_for_long_text(
        self, json_path: Path = None, json_data: list = None
    ) -> Dataset:
        """
        Load a Label Studio JSON file or data and convert it to a Hugging Face Dataset.
        Handles long documents by smartly chunking them into multiple smaller segments
        that respect entity boundaries and token limits.
        
        Args:
            json_path: Optional path to a local JSON file
            json_data: Optional JSON data already loaded (list of Label Studio entries)
        """
        if json_data is not None:
            data = json_data
        elif json_path is not None:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            raise ValueError("Either json_path or json_data must be provided")

        processed_examples = []

        for entry in tqdm(data, desc="Preprocessing long Label Studio entries"):
            text = entry["data"].get("text", "")
            if not text.strip():
                continue

            # Extract entity spans
            entities = []
            try:
                results = entry["annotations"][0]["result"]
            except (KeyError, IndexError):
                continue

            for r in results:
                if "value" not in r or "labels" not in r["value"]:
                    continue
                val = r["value"]
                entities.append(
                    {
                        "start": val["start"],
                        "end": val["end"],
                        # we assume that there is only one label per entity
                        "label": val["labels"][0],
                    }
                )

            # Tokenize entire text once to get offsets
            encoding = self.tokenizer(
                text,
                return_offsets_mapping=True,  # offset_mapping gives you the start and end tokens for each word
                add_special_tokens=False,
                # the truncation is False because we want to keep the entire text
                truncation=False,
            )
            offsets = encoding[
                "offset_mapping"
            ]  # we will get a long list of start and end indices for each word
            num_tokens = len(offsets)
            token_spans = [(s, e) for (s, e) in offsets if s is not None]

            max_tokens = (
                self.tokenizer.model_max_length
            )  # this is the maximum number of tokens that the model can handle
            # we will smartly chunk the text into smaller segments that are maximum max_tokens length
            chunk_start_tok = 0
            print(f"This model accepts maximum {max_tokens} as an input")
            print(f"We have {num_tokens} tokens in our text")
            if num_tokens > max_tokens:
                print(f"We will need to chunk the text into smaller segments")

            while chunk_start_tok < num_tokens:
                # reserve room for [CLS] and [SEP]
                chunk_end_tok = min(chunk_start_tok + max_tokens - 2, num_tokens)
                chunk_start_char = token_spans[chunk_start_tok][0]
                chunk_end_char = (
                    token_spans[chunk_end_tok - 1][1]
                    if chunk_end_tok <= num_tokens
                    else len(text)
                )

                # extend if an entity crosses the chunk boundary
                for ent in entities:
                    if ent["start"] < chunk_end_char < ent["end"]:
                        chunk_end_char = ent["end"]
                        for i, (s, e) in enumerate(token_spans):
                            if e >= chunk_end_char:
                                chunk_end_tok = i + 1
                                break

                # extract the chunk text
                chunk_text = text[chunk_start_char:chunk_end_char]

                # adjust entity spans relative to this chunk
                chunk_entities = []
                for ent in entities:
                    if (
                        ent["start"] >= chunk_start_char
                        and ent["end"] <= chunk_end_char
                    ):
                        chunk_entities.append(
                            {
                                "start": ent["start"] - chunk_start_char,
                                "end": ent["end"] - chunk_start_char,
                                "label": ent["label"],
                            }
                        )

                if chunk_text.strip():
                    processed_examples.append(
                        {"text": chunk_text, "entities": chunk_entities}
                    )

                chunk_start_tok = chunk_end_tok
            print(
                f"✅ Created {len(processed_examples)} chunks from {len(data)} documents"
            )
            print(
                f"This means we have splite the 1 whole document into {len(processed_examples)} chunks"
            )

        print(
            f"✅ In total, we have created {len(processed_examples)} chunks from {len(data)} documents"
        )
        return Dataset.from_list(processed_examples)

    def process_one_label_studio_entry(self, entry: Dict) -> Dict:
        """
        Process one pre-chunked example from preprocess_label_studio_data_for_long_text().
        Expects a dict like:
        {
            "text": "...",
            "entities": [
                {"start": 0, "end": 12, "label": "ORG"},
                {"start": 35, "end": 39, "label": "PROJECT"}
            ]
        }
        Returns:
            {
                "tokens": [...],
                "labels": [...]
            }
        """

        text = entry.get("text")
        entities = entry.get("entities", [])
        if not text:
            print("⚠️ Skipping entry with no text.")
            return None

        # Tokenize with offsets to align character spans
        encoding = self.tokenizer(
            text,
            return_offsets_mapping=True,
            add_special_tokens=False,
        )
        tokens = self.tokenizer.convert_ids_to_tokens(encoding["input_ids"])
        offsets = encoding["offset_mapping"]

        # Default all tokens to "O"
        labels = [self.NULL_LABEL] * len(tokens)

        # Assign BIO labels based on entity spans
        for ent in entities:
            ent_start, ent_end, ent_label = ent["start"], ent["end"], ent["label"]
            for i, (start, end) in enumerate(offsets):
                if start is None or end is None:
                    continue
                if start >= ent_start and end <= ent_end:
                    prefix = "B-" if start == ent_start else "I-"
                    label_tag = prefix + ent_label
                    labels[i] = (
                        label_tag if label_tag in self.label_to_id else self.NULL_LABEL
                    )

        return {"tokens": tokens, "labels": labels}

    def add_labels_in_model_format(self, batch: Dict) -> Dict:
        """Add labels in model-ready format."""
        tokens_batch = batch["tokens"]  # list of token lists
        labels_batch = batch["labels"]  # list of label lists

        # Tokenize all examples together
        tokenized = self.tokenizer(
            tokens_batch,
            truncation=True,
            is_split_into_words=True,
            padding=False,  # dynamic padding later by collator
        )

        all_label_ids = []

        # For each example in the batch
        for i, labels in enumerate(labels_batch):
            word_ids = tokenized.word_ids(batch_index=i)
            label_ids = []

            for word_idx in word_ids:
                # ✅ Guard against None (special tokens) and out-of-range indices
                if word_idx is None or word_idx >= len(labels):
                    label_ids.append(-100)
                else:
                    label = labels[word_idx]
                    label_ids.append(
                        self.label_to_id.get(label, self.label_to_id[self.NULL_LABEL])
                    )

            all_label_ids.append(label_ids)

        tokenized["labels"] = all_label_ids
        return tokenized

    def prepare_model_input_data(
        self, json_path: Path = None, use_gcs: bool = False
    ) -> Dataset:
        """
        Full preprocessing pipeline:
        1. Load and chunk long Label Studio JSONs (from GCS or local file)
        2. Tokenize and align BIO labels
        Returns a model-ready Hugging Face Dataset with input_ids, attention_mask, and labels.
        
        Args:
            json_path: Optional path to a local JSON file (used if use_gcs=False)
            use_gcs: If True, load data from GCS storage; if False, use json_path
        """
        print("🧩 Preparing model input data...")

        # Step 1. Load & preprocess (handles long or short docs automatically)
        if use_gcs:
            print("📦 Loading data from GCS...")
            dataset = self.import_gcs_annotation_data()
        else:
            if json_path is None:
                json_path = Path("tmp/sample-bpda-data.json")
            print(f"📂 Loading data from local file: {json_path}")
            dataset = self.import_label_studio_data_from_single_json(json_path)

        # Step 2. Tokenize and align labels
        tokenized_dataset = dataset.map(self.add_labels_in_model_format, batched=True)

        print(f"✅ Prepared {len(tokenized_dataset)} examples ready for training.")
        return tokenized_dataset

    def train(self, batch_size=8, epochs=3, learning_rate=2e-5, use_gcs=False, json_path=None, gradient_accumulation_steps=1):
        """
        Train the NER model with automatic Weights & Biases tracking.
        
        Args:
            batch_size: Training batch size per device
            epochs: Number of training epochs
            learning_rate: Learning rate for optimizer
            use_gcs: If True, load training data from GCS; if False, use local file
            json_path: Optional path to local JSON file (used if use_gcs=False)
            gradient_accumulation_steps: Number of steps to accumulate gradients before updating weights
                                        Effective batch size = batch_size * gradient_accumulation_steps
        """
        # Split the dataset into training and validation sets
        dataset = self.prepare_model_input_data(json_path=json_path, use_gcs=use_gcs)
        dataset = dataset.remove_columns(
            [
                col
                for col in dataset.column_names
                if col not in ["input_ids", "attention_mask", "labels"]
            ]
        )
        split = dataset.train_test_split(test_size=0.1)

        train_dataset = split["train"]
        val_dataset = split["test"]

        # ✅ Initialize wandb run with auto-generated name
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        model_short_name = self.model_name.split("/")[-1]  # e.g., "legal-bert-base-uncased"
        effective_batch_size = batch_size * gradient_accumulation_steps
        run_name = f"{model_short_name}-e{epochs}-bs{effective_batch_size}-{timestamp}"
        
        wandb.init(
            project="spatially-development-plans-ner",
            name=run_name,
            config={
                "model_name": self.model_name,
                "batch_size": batch_size,
                "gradient_accumulation_steps": gradient_accumulation_steps,
                "effective_batch_size": effective_batch_size,
                "epochs": epochs,
                "learning_rate": learning_rate,
                "train_size": len(train_dataset),
                "val_size": len(val_dataset),
                "num_labels": len(self.label_to_id),
                "labels": list(self.label_to_id.keys()),
                "device": str(self.device),
                "data_source": "gcs" if use_gcs else "local",
            },
            tags=["ner", "development-plans", "token-classification", "spatially"]
        )
        
        print(f"📊 Training configuration:")
        print(f"  - Batch size per step: {batch_size}")
        print(f"  - Gradient accumulation steps: {gradient_accumulation_steps}")
        print(f"  - Effective batch size: {effective_batch_size}")
        print(f"  - Device: {self.device}")
        if self.device != "gpu":
            print("⚠️ Warning: Using CPU for training. This may be slow.")
        
        # Log dataset info
        wandb.log({
            "dataset/total_examples": len(dataset),
            "dataset/train_examples": len(train_dataset),
            "dataset/val_examples": len(val_dataset),
        })

        # data loaders
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

        # ✅ Create a data collator for dynamic padding
        data_collator = DataCollatorForTokenClassification(tokenizer=self.tokenizer)

        # ✅ Use it in the DataLoader
        train_loader = DataLoader(
            train_dataset, batch_size=batch_size, shuffle=True, collate_fn=data_collator
        )
        val_loader = DataLoader(
            val_dataset, batch_size=batch_size, shuffle=False, collate_fn=data_collator
        )

        # optimizer
        optimizer = AdamW(self.model.parameters(), lr=learning_rate)

        device = self.device

        # Track global step for detailed logging
        global_step = 0

        # train the model
        for epoch in range(epochs):
            print(f"Epoch {epoch+1}/{epochs}")
            self.model.train()
            total_loss = 0
            epoch_steps = 0

            for batch_idx, batch in enumerate(tqdm(train_loader, desc="Training")):
                batch = {
                    k: v.to(device)
                    for k, v in batch.items()
                    if isinstance(v, torch.Tensor)
                }
                outputs = self.model(**batch)
                loss = outputs.loss
                
                # Normalize loss for gradient accumulation
                loss = loss / gradient_accumulation_steps
                total_loss += loss.item() * gradient_accumulation_steps
                
                loss.backward()
                
                # Only update weights every gradient_accumulation_steps
                if (batch_idx + 1) % gradient_accumulation_steps == 0 or (batch_idx + 1) == len(train_loader):
                    optimizer.step()
                    optimizer.zero_grad()
                    global_step += 1
                
                epoch_steps += 1
                
                # Log batch loss every 10 optimizer steps
                if global_step > 0 and global_step % 10 == 0:
                    wandb.log({
                        "train/batch_loss": loss.item() * gradient_accumulation_steps,
                        "train/global_step": global_step,
                    }, step=global_step)

            avg_train_loss = total_loss / len(train_loader)
            print(f"Average training loss: {avg_train_loss:.4f}")

            # evaluate the model
            avg_val_loss = self.evaluate(val_loader, device)
            print(f"Average validation loss: {avg_val_loss:.4f}")

            # Log epoch metrics
            wandb.log({
                "train/epoch_loss": avg_train_loss,
                "val/epoch_loss": avg_val_loss,
                "epoch": epoch + 1,
            }, step=global_step)

        # Save model
        model_path = "tmp/ner_model"
        tokenizer_path = "tmp/ner_tokenizer"
        self.model.save_pretrained(model_path)
        self.tokenizer.save_pretrained(tokenizer_path)
        
        # Log model as artifact (optional but recommended)
        model_artifact = wandb.Artifact(
            name="ner-model",
            type="model",
            description=f"NER model trained on {len(train_dataset)} examples"
        )
        model_artifact.add_dir(model_path)
        wandb.log_artifact(model_artifact)
        
        # Finish the wandb run
        wandb.finish()
        
        print("✅ Training completed and logged to Weights & Biases")

    def evaluate(self, loader: DataLoader, device: torch.device) -> float:
        # the eval() would set the model to evaluation mode, making it not trainable
        self.model.eval()
        total_loss = 0
        with torch.no_grad():
            for batch in tqdm(loader, desc="Evaluating"):
                batch = {
                    k: v.to(device)
                    for k, v in batch.items()
                    if isinstance(v, torch.Tensor)
                }
                outputs = self.model(**batch)
                loss = outputs.loss
                total_loss += loss.item()
        return total_loss / len(loader)
