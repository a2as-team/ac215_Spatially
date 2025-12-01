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
        # Build consistent label mappings:
        # - BIO labels from config.NER_LABELS
        # - Add "O" (outside) label as the last class
        self.label_to_id = {v: i for i, v in enumerate(NER_LABELS)}
        # Add NULL / outside label
        self.label_to_id[self.NULL_LABEL] = len(self.label_to_id)
        # Mirror mapping for convenience (used in stratification, debugging, etc.)
        self.id_to_label = {i: v for v, i in self.label_to_id.items()}

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForTokenClassification.from_pretrained(
            self.model_name, 
            num_labels=len(self.label_to_id),
            id2label=self.id_to_label,
            label2id=self.label_to_id
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

    def prepare_model_input_data(self, json_path: Path = None, downsample_no_entities: float = 0.15) -> Dataset:
        """
        Full preprocessing pipeline:
        1. Load and chunk long Label Studio JSONs (from GCS or local file)
        2. Tokenize and align BIO labels
        3. Downsample chunks with no entities to reduce class imbalance
        Returns a model-ready Hugging Face Dataset with input_ids, attention_mask, and labels.

        Args:
            json_path: Optional path to a local JSON file. If None, loads from GCS storage.
            downsample_no_entities: Keep this fraction of NO_ENTITIES chunks (default 0.15 = 15%)
        """
        print("🧩 Preparing model input data...")

        # Step 1. Load & preprocess (handles long or short docs automatically)
        if json_path is None:
            print("📦 Loading data from GCS...")
            dataset = self.import_gcs_annotation_data()
        else:
            print(f"📂 Loading data from local file: {json_path}")
            dataset = self.import_label_studio_data_from_single_json(json_path)

        # Step 2. Downsample NO_ENTITIES chunks
        if downsample_no_entities < 1.0:
            print(f"🎲 Downsampling NO_ENTITIES chunks (keeping {downsample_no_entities*100:.0f}%)...")

            # Identify which examples have no entities
            has_entities = []
            for example in dataset:
                labels = example["labels"]
                # Check if any label is not "O"
                has_any_entity = any(label != self.NULL_LABEL for label in labels)
                has_entities.append(has_any_entity)

            # Count
            num_with_entities = sum(has_entities)
            num_without_entities = len(has_entities) - num_with_entities

            print(f"   Before: {len(dataset)} chunks ({num_with_entities} with entities, {num_without_entities} without)")

            # Keep all with entities, downsample those without
            import random
            random.seed(42)

            indices_to_keep = []
            for i, has_ent in enumerate(has_entities):
                if has_ent:
                    # Keep all chunks with entities
                    indices_to_keep.append(i)
                else:
                    # Randomly keep downsample_no_entities fraction of chunks without entities
                    if random.random() < downsample_no_entities:
                        indices_to_keep.append(i)

            dataset = dataset.select(indices_to_keep)

            num_kept_without = len(indices_to_keep) - num_with_entities
            print(f"   After:  {len(dataset)} chunks ({num_with_entities} with entities, {num_kept_without} without)")
            print(f"   Removed {num_without_entities - num_kept_without} NO_ENTITIES chunks")

        # Step 3. Tokenize and align labels
        tokenized_dataset = dataset.map(self.add_labels_in_model_format, batched=True)

        print(f"✅ Prepared {len(tokenized_dataset)} examples ready for training.")
        return tokenized_dataset

    def _create_stratification_labels(self, dataset: Dataset) -> list:
        """
        Stratify based on the rarest entity type present in each example.
        This ensures rare entities (like ZONING_RELIEF) are in both train/val sets.
        """
        from config.labels import BASE_ENTITY_TYPES

        # Priority order: rarest first (based on actual data distribution)
        entity_priority = {
            "ZONING_RELIEF": 0,        # Rarest (2.1%)
            "PROPERTY_USAGE": 1,       # (6.4%)
            "ZONING_DISTRICT": 2,      # (6.3%)
            "EXPECTED_IMPACT": 3,      # (10.7%)
            "LOCATION_CONTEXT": 4,     # (18.3%)
            "CONSTRUCTION_DETAILS": 5, # (25.3%)
            "ARTICLE_REFERENCE": 6,    # Most common (28.7%)
        }

        stratification_labels = []

        for example in dataset:
            labels = example["labels"]
            present_types = set()

            for label_id in labels:
                if label_id != -100:
                    label_name = self.id_to_label.get(label_id, "O")
                    if label_name != "O":
                        entity_type = label_name.split("-")[1] if "-" in label_name else label_name
                        present_types.add(entity_type)

            # Use the rarest entity type as the stratification label
            if present_types:
                rarest = min(present_types, key=lambda x: entity_priority.get(x, 999))
                strat_label = rarest
            else:
                strat_label = "NO_ENTITIES"

            stratification_labels.append(strat_label)

        return stratification_labels

    def train(self, batch_size=8, epochs=3, learning_rate=2e-5, json_path=None, downsample_no_entities=0.15):
        """
        Train the NER model with automatic Weights & Biases tracking.

        Args:
            batch_size: Training batch size per device
            epochs: Number of training epochs
            learning_rate: Learning rate for optimizer
            json_path: Optional path to local JSON file. If None, loads from GCS storage.
            downsample_no_entities: Fraction of NO_ENTITIES chunks to keep (0.15 = keep 15%, remove 85%)
        """
        # Split the dataset into training and validation sets
        dataset = self.prepare_model_input_data(json_path=json_path, downsample_no_entities=downsample_no_entities)

        # Create stratification labels (one label per entity type, prioritizing rare entities)
        print("🔀 Creating stratified split by rarest entity type...")
        stratification_labels = self._create_stratification_labels(dataset)

        from collections import Counter
        from datasets import ClassLabel

        strat_counts = Counter(stratification_labels)
        print(f"📊 Stratification by entity type:")
        for label, count in sorted(strat_counts.items(), key=lambda x: x[1]):
            print(f"   - {label}: {count} examples")

        # Convert to ClassLabel format (required by HuggingFace)
        unique_labels = sorted(set(stratification_labels))
        label_to_id = {label: i for i, label in enumerate(unique_labels)}
        stratification_ids = [label_to_id[label] for label in stratification_labels]

        dataset = dataset.add_column("_strat_label", stratification_ids)
        new_features = dataset.features.copy()
        new_features["_strat_label"] = ClassLabel(names=unique_labels)
        dataset = dataset.cast(new_features)

        # Perform stratified split (with fallback for edge cases)
        try:
            split = dataset.train_test_split(
                test_size=0.1,
                stratify_by_column="_strat_label"
            )
            print("✓ Stratified split complete")
        except ValueError as e:
            print(f"⚠️  Stratified split failed: {e}")
            print(f"   Falling back to random split (dataset too small for stratification)")
            dataset = dataset.remove_columns(["_strat_label"])
            split = dataset.train_test_split(test_size=0.1)
            print("✓ Random split complete")

        train_dataset = split["train"]
        val_dataset = split["test"]

        # Remove stratification column and keep only model inputs
        train_dataset = train_dataset.remove_columns(["_strat_label"])
        val_dataset = val_dataset.remove_columns(["_strat_label"])

        cols_to_remove = [
            col for col in train_dataset.column_names
            if col not in ["input_ids", "attention_mask", "labels"]
        ]
        if cols_to_remove:
            train_dataset = train_dataset.remove_columns(cols_to_remove)
            val_dataset = val_dataset.remove_columns(cols_to_remove)

        # ✅ Initialize wandb run with auto-generated name
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        model_short_name = self.model_name.split("/")[-1]  # e.g., "legal-bert-base-uncased"
        run_name = f"{model_short_name}-e{epochs}-bs{batch_size}-{timestamp}"

        wandb.init(
            project="spatially-development-plans-ner",
            name=run_name,
            config={
                "model_name": self.model_name,
                "batch_size": batch_size,
                "epochs": epochs,
                "learning_rate": learning_rate,
                "train_size": len(train_dataset),
                "val_size": len(val_dataset),
                "num_labels": len(self.label_to_id),
                "labels": list(self.label_to_id.keys()),
                "device": str(self.device),
                "data_source": "gcs" if json_path is None else "local",
                "downsample_no_entities": downsample_no_entities,
            },
            tags=["ner", "development-plans", "token-classification", "spatially"]
        )

        print(f"📊 B:")
        print(f"  - Batch size: {batch_size}")
        print(f"  - Device: {self.device}")
        if self.device.type != "cuda":
            print("⚠️ Warning: Using CPU for training. This may be slow.")
        
        # Log dataset info
        wandb.log({
            "dataset/total_examples": len(dataset),
            "dataset/train_examples": len(train_dataset),
            "dataset/val_examples": len(val_dataset),
        })

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

        # ============================
        # 🔧 Class-weighted loss
        # ============================
        #
        # Even after downsampling NO_ENTITIES chunks, most tokens are still "O".
        # This makes the model biased towards predicting "O" for everything.
        #
        # To counter this, we:
        # - Use a class-weighted CrossEntropyLoss
        # - Down-weight the "O" class so entity labels get higher gradient signal
        #
        # NOTE: We compute weights purely from label mappings here:
        #  - All entity labels = weight 1.0
        #  - "O" label         = weight 0.1 (configurable if needed)
        num_labels = len(self.label_to_id)
        class_weights = torch.ones(num_labels, device=device)
        null_label_id = self.label_to_id[self.NULL_LABEL]
        class_weights[null_label_id] = 0.1  # reduce impact of "O"

        loss_fn = torch.nn.CrossEntropyLoss(
            weight=class_weights,
            ignore_index=-100,  # ignore padded / special-token positions
        )

        # Track global step for detailed logging
        global_step = 0

        # train the model
        for epoch in range(epochs):
            print(f"Epoch {epoch+1}/{epochs}")
            self.model.train()
            total_loss = 0

            for batch in tqdm(train_loader, desc="Training"):
                batch = {
                    k: v.to(device)
                    for k, v in batch.items()
                    if isinstance(v, torch.Tensor)
                }

                # Forward pass (we'll compute loss manually with class weights)
                outputs = self.model(
                    input_ids=batch["input_ids"],
                    attention_mask=batch["attention_mask"],
                    labels=None,  # avoid built-in loss
                )

                logits = outputs.logits  # [batch, seq_len, num_labels]
                labels = batch["labels"]  # [batch, seq_len]

                # Flatten for CrossEntropyLoss: (N * T, C) vs (N * T)
                loss = loss_fn(
                    logits.view(-1, logits.size(-1)),
                    labels.view(-1),
                )

                total_loss += loss.item()

                loss.backward()
                optimizer.step()
                optimizer.zero_grad()
                global_step += 1

                # Log batch loss every 10 steps
                if global_step % 10 == 0:
                    wandb.log({
                        "train/batch_loss": loss.item(),
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

        # Save model locally, then upload to GCS if on Vertex AI
        aip_model_dir = os.environ.get("AIP_MODEL_DIR")

        # Always save to local tmp directory first
        local_model_dir = "tmp"
        model_path = f"{local_model_dir}/ner_model"
        tokenizer_path = f"{local_model_dir}/ner_tokenizer"

        print(f"\n💾 Saving model to local directory: {model_path}")
        
        # Set label mappings in model config before saving
        self.model.config.label2id = self.label_to_id
        self.model.config.id2label = self.id_to_label
        
        self.model.save_pretrained(model_path)
        self.tokenizer.save_pretrained(tokenizer_path)
        print(f"✅ Model saved locally")

        # Upload to GCS if running on Vertex AI
        if aip_model_dir:
            print(f"\n☁️  Uploading to GCS: {aip_model_dir}")

            # Extract bucket and path from gs:// URL
            gcs_path = aip_model_dir.replace("gs://", "")
            bucket_name = gcs_path.split("/")[0]
            gcs_prefix = "/".join(gcs_path.split("/")[1:])

            # Get GCP project from environment
            gcp_project = os.environ.get("GCP_PROJECT")

            # Initialize GCS client
            gcs_storage = GCPStorage(gcp_project=gcp_project, bucket_name=bucket_name)

            # Upload model files
            gcs_storage.upload_dir(
                source_path=model_path,
                destination_path=f"{gcs_prefix}ner_model"
            )

            # Upload tokenizer files
            gcs_storage.upload_dir(
                source_path=tokenizer_path,
                destination_path=f"{gcs_prefix}ner_tokenizer"
            )

            print(f"✅ Model uploaded to: {aip_model_dir}ner_model")
            print(f"✅ Tokenizer uploaded to: {aip_model_dir}ner_tokenizer")

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
        """
        Evaluation loop that mirrors the training loss:
        - Uses the same class-weighted CrossEntropyLoss
        - Ignores padded positions (-100)
        """
        self.model.eval()
        total_loss = 0

        # Recreate the same class-weighted criterion used in training
        num_labels = len(self.label_to_id)
        class_weights = torch.ones(num_labels, device=device)
        null_label_id = self.label_to_id[self.NULL_LABEL]
        class_weights[null_label_id] = 0.1

        loss_fn = torch.nn.CrossEntropyLoss(
            weight=class_weights,
            ignore_index=-100,
        )

        with torch.no_grad():
            for batch in tqdm(loader, desc="Evaluating"):
                batch = {
                    k: v.to(device)
                    for k, v in batch.items()
                    if isinstance(v, torch.Tensor)
                }

                outputs = self.model(
                    input_ids=batch["input_ids"],
                    attention_mask=batch["attention_mask"],
                    labels=None,
                )
                logits = outputs.logits
                labels = batch["labels"]

                loss = loss_fn(
                    logits.view(-1, logits.size(-1)),
                    labels.view(-1),
                )
                total_loss += loss.item()

        return total_loss / len(loader)
