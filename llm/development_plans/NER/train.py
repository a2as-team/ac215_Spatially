from pathlib import Path
from typing import Dict
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

    def import_label_studio_data(
        self, json_path: Path = Path("tmp/sample-bpda-data.json")
    ) -> Dataset:
        """Load a Label Studio JSON file and convert it to a Hugging Face Dataset."""
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Step 1. Smart chunking (handles long or short texts)
        # this will handle long texts by smartly chunking them into smaller segments
        chunked_dataset = self.preprocess_label_studio_data_for_long_text(json_path)

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
        self, json_path: Path = Path("tmp/sample-bpda-data.json")
    ) -> Dataset:
        """
        Load a Label Studio JSON file and convert it to a Hugging Face Dataset.
        Handles long documents by smartly chunking them into multiple smaller segments
        that respect entity boundaries and token limits.
        """
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

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
        labels = ["O"] * len(tokens)

        # Assign BIO labels based on entity spans
        for ent in entities:
            ent_start, ent_end, ent_label = ent["start"], ent["end"], ent["label"]
            for i, (start, end) in enumerate(offsets):
                if start is None or end is None:
                    continue
                if start >= ent_start and end <= ent_end:
                    prefix = "B-" if start == ent_start else "I-"
                    label_tag = prefix + ent_label
                    labels[i] = label_tag if label_tag in self.label_to_id else "O"

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
                    label_ids.append(self.label_to_id.get(label, self.label_to_id["O"]))

            all_label_ids.append(label_ids)

        tokenized["labels"] = all_label_ids
        return tokenized

    def prepare_model_input_data(
        self, json_path: Path = Path("tmp/sample-bpda-data.json")
    ) -> Dataset:
        """
        Full preprocessing pipeline:
        1. Load and chunk long Label Studio JSONs (import_label_studio_data)
        2. Tokenize and align BIO labels (tokenize_and_align)
        Returns a model-ready Hugging Face Dataset with input_ids, attention_mask, and labels.
        """
        print("🧩 Preparing model input data...")

        # Step 1. Load & preprocess (handles long or short docs automatically)
        dataset = self.import_label_studio_data(json_path)

        # Step 2. Tokenize and align labels
        tokenized_dataset = dataset.map(self.add_labels_in_model_format, batched=True)

        print(f"✅ Prepared {len(tokenized_dataset)} examples ready for training.")
        return tokenized_dataset

    def train(self, batch_size=8, epochs=3, learning_rate=2e-5):
        # Split the dataset into training and validation sets
        dataset = self.prepare_model_input_data()
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
                outputs = self.model(**batch)
                loss = outputs.loss
                total_loss += loss.item()

                loss.backward()
                optimizer.step()
                optimizer.zero_grad()

            avg_loss = total_loss / len(train_loader)
            print(f"Average loss: {avg_loss:.4f}")

            # evaluate the model
            self.evaluate(val_loader, device)

        # self.model.save_pretrained("tmp/ner_model")
        # self.tokenizer.save_pretrained("tmp/ner_tokenizer")

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
