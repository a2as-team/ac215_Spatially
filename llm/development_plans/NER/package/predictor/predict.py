"""
NER Predictor for extracting entities from development plan documents.

This module loads a fine-tuned BERT model from GCS and provides entity extraction
functionality using BIO tagging scheme.
"""
import os
import torch
from pathlib import Path
from typing import Dict, List, Tuple
from transformers import AutoTokenizer, AutoModelForTokenClassification
from config.labels import NER_LABELS


class NERPredictor:
    """
    Named Entity Recognition predictor for development plans.

    Loads a fine-tuned BERT model from GCS and provides methods to extract
    entities from text using BIO (Begin-Inside-Outside) tagging scheme.
    """

    NULL_LABEL = "O"

    def __init__(
        self,
        gcp_storage,
        gcp_project: str,
        model_gcs_path: str = "ner_model_output/model/ner_model",
        tokenizer_gcs_path: str = "ner_model_output/model/ner_tokenizer",
        model_bucket: str = None,
        device: str = None,
    ):
        """
        Initialize NER predictor with model from GCS.

        Args:
            gcp_storage: GCPStorage instance for downloading model files
            gcp_project: GCP project ID
            model_gcs_path: GCS path to the model directory
            tokenizer_gcs_path: GCS path to the tokenizer directory
            model_bucket: GCS bucket name containing the model (if different from gcp_storage bucket)
            device: Device to run inference on ('cpu', 'cuda', 'mps', or None for auto)
        """
        self.gcp_storage = gcp_storage
        self.gcp_project = gcp_project
        self.model_gcs_path = model_gcs_path
        self.tokenizer_gcs_path = tokenizer_gcs_path
        self.model_bucket = model_bucket

        # Set up label mappings
        self.label_to_id = {v: i for i, v in enumerate(NER_LABELS)}
        self.label_to_id[self.NULL_LABEL] = len(self.label_to_id)
        self.id_to_label = {i: v for v, i in self.label_to_id.items()}

        # Determine device
        if device is not None:
            self.device = torch.device(device)
        elif torch.backends.mps.is_available():
            self.device = torch.device("mps")
        elif torch.cuda.is_available():
            self.device = torch.device("cuda")
        else:
            self.device = torch.device("cpu")

        print(f"NER Predictor using device: {self.device}")

        # Download and load model
        self._download_model_from_gcs()
        self._load_model()

    def _download_model_from_gcs(self):
        """Download model and tokenizer from GCS to local tmp directory."""
        # Create temporary directory for model files
        self.local_model_dir = Path("tmp/ner_model_inference")
        self.local_model_path = self.local_model_dir / "ner_model"
        self.local_tokenizer_path = self.local_model_dir / "ner_tokenizer"

        # Check if model already exists locally
        if self.local_model_path.exists() and self.local_tokenizer_path.exists():
            print(f"✓ Using cached model from {self.local_model_dir}")
            return

        print(f"📥 Downloading NER model from GCS...")
        self.local_model_dir.mkdir(parents=True, exist_ok=True)

        # Use different storage client if model is in different bucket
        storage = self.gcp_storage
        if self.model_bucket:
            from utils.gcp_storage import GCPStorage
            storage = GCPStorage(
                gcp_project=self.gcp_project,
                bucket_name=self.model_bucket
            )

        # Download model files
        self._download_directory_from_gcs(
            storage, self.model_gcs_path, self.local_model_path
        )

        # Download tokenizer files
        self._download_directory_from_gcs(
            storage, self.tokenizer_gcs_path, self.local_tokenizer_path
        )

        print(f"✓ Model downloaded to {self.local_model_dir}")

    def _download_directory_from_gcs(self, storage, gcs_prefix: str, local_path: Path):
        """Download all files from a GCS directory prefix to local path."""
        local_path.mkdir(parents=True, exist_ok=True)

        # List all files with the prefix
        blobs = storage.list_blobs(prefix=gcs_prefix)

        for blob in blobs:
            # Skip directories (blobs ending with /)
            if blob.name.endswith('/'):
                continue

            # Get relative path within the prefix
            relative_path = blob.name[len(gcs_prefix):].lstrip('/')
            if not relative_path:
                continue

            # Download to local path
            local_file = local_path / relative_path
            local_file.parent.mkdir(parents=True, exist_ok=True)

            print(f"  - Downloading {blob.name} -> {local_file}")
            storage.download_blob_to_file(blob.name, str(local_file))

    def _load_model(self):
        """Load the model and tokenizer from local directory."""
        print(f"🔧 Loading NER model and tokenizer...")

        self.tokenizer = AutoTokenizer.from_pretrained(str(self.local_tokenizer_path))
        self.model = AutoModelForTokenClassification.from_pretrained(
            str(self.local_model_path)
        )
        self.model.to(self.device)
        self.model.eval()  # Set to evaluation mode

        print(f"✓ Model loaded successfully ({len(self.label_to_id)} labels)")

    def predict_entities(self, text: str) -> List[Dict[str, any]]:
        """
        Extract named entities from text using the fine-tuned NER model.

        Args:
            text: Input text to extract entities from

        Returns:
            List of entity dictionaries with keys:
                - text: The entity text
                - label: Entity type (e.g., "ARTICLE_REFERENCE")
                - start: Character start position
                - end: Character end position
                - confidence: Model confidence score
        """
        if not text or not text.strip():
            return []

        # Tokenize with offsets to map back to original text
        encoding = self.tokenizer(
            text,
            return_offsets_mapping=True,
            return_tensors="pt",
            truncation=True,
            max_length=512,
        )

        # Move to device
        input_ids = encoding["input_ids"].to(self.device)
        attention_mask = encoding["attention_mask"].to(self.device)
        offsets = encoding["offset_mapping"][0].tolist()

        # Run inference
        with torch.no_grad():
            outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
            predictions = torch.argmax(outputs.logits, dim=-1)[0].tolist()
            probabilities = torch.softmax(outputs.logits, dim=-1)[0].tolist()

        # Decode BIO tags to entities
        entities = self._decode_bio_tags(
            text, predictions, probabilities, offsets
        )

        return entities

    def _decode_bio_tags(
        self,
        text: str,
        predictions: List[int],
        probabilities: List[List[float]],
        offsets: List[Tuple[int, int]]
    ) -> List[Dict[str, any]]:
        """
        Decode BIO tag predictions into entity spans.

        Merges consecutive B- and I- tags into single entities and maps
        character positions back to original text.

        Args:
            text: Original text
            predictions: List of predicted label IDs
            probabilities: List of probability distributions for each token
            offsets: List of (start, end) character offsets for each token

        Returns:
            List of entity dictionaries
        """
        entities = []
        current_entity = None

        for idx, (pred_id, probs, offset) in enumerate(zip(predictions, probabilities, offsets)):
            # Skip special tokens (offset is (0, 0))
            if offset[0] == 0 and offset[1] == 0:
                continue

            label = self.id_to_label.get(pred_id, self.NULL_LABEL)
            confidence = probs[pred_id]

            # Skip "O" (outside) tags
            if label == self.NULL_LABEL:
                if current_entity:
                    entities.append(current_entity)
                    current_entity = None
                continue

            # Parse BIO tag
            if label.startswith("B-"):
                # Save previous entity if exists
                if current_entity:
                    entities.append(current_entity)

                # Start new entity
                entity_type = label[2:]  # Remove "B-" prefix
                current_entity = {
                    "text": text[offset[0]:offset[1]],
                    "label": entity_type,
                    "start": offset[0],
                    "end": offset[1],
                    "confidence": confidence,
                }

            elif label.startswith("I-"):
                # Continue current entity
                entity_type = label[2:]  # Remove "I-" prefix

                if current_entity and current_entity["label"] == entity_type:
                    # Extend entity to include this token
                    current_entity["end"] = offset[1]
                    current_entity["text"] = text[current_entity["start"]:offset[1]]
                    # Average confidence scores
                    current_entity["confidence"] = (
                        current_entity["confidence"] + confidence
                    ) / 2
                else:
                    # I- tag without matching B- tag, treat as new entity
                    if current_entity:
                        entities.append(current_entity)

                    current_entity = {
                        "text": text[offset[0]:offset[1]],
                        "label": entity_type,
                        "start": offset[0],
                        "end": offset[1],
                        "confidence": confidence,
                    }

        # Add final entity if exists
        if current_entity:
            entities.append(current_entity)

        return entities

    def group_entities_by_type(self, entities: List[Dict[str, any]]) -> Dict[str, List[str]]:
        """
        Group entities by their type.

        Args:
            entities: List of entity dictionaries from predict_entities()

        Returns:
            Dictionary mapping entity types to lists of entity texts
            Example: {
                "ARTICLE_REFERENCE": ["Article 50", "Section 32"],
                "ZONING_DISTRICT": ["New Market Industrial Development Area"],
                ...
            }
        """
        grouped = {}
        for entity in entities:
            label = entity["label"]
            text = entity["text"]

            if label not in grouped:
                grouped[label] = []

            # Avoid duplicates
            if text not in grouped[label]:
                grouped[label].append(text)

        return grouped
