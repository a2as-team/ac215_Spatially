"""
NER Service Wrapper for Development Plans

This module provides a singleton wrapper around the fine-tuned NER model
to extract ARTICLE_REFERENCE entities from development plan text.
"""
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional


class DevelopmentPlansNER:
    """
    Singleton wrapper for NER model to extract ARTICLE_REFERENCE entities.

    This wrapper implements lazy loading to defer expensive model initialization
    until the first prediction request. The model is cached in memory for
    subsequent requests.

    Usage:
        ner = DevelopmentPlansNER()
        article_refs = ner.extract_article_references(text)
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        """Implement singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the NER service (singleton, only runs once)."""
        if self._initialized:
            return

        self.logger = logging.getLogger(__name__)
        self.predictor = None
        self._initialized = True
        self.logger.info("DevelopmentPlansNER instance created (model not loaded yet)")

    def _ensure_predictor_loaded(self):
        """
        Load NER predictor on first use (lazy loading).

        This method downloads the model from GCS if needed and initializes
        the NER predictor. The model is cached locally for subsequent runs.

        Raises:
            RuntimeError: If model cannot be loaded or dependencies are missing
        """
        if self.predictor is not None:
            return

        try:
            self.logger.info("Loading NER model from GCS (first use)...")

            # Add llm package to Python path
            # In Docker: /llm/development_plans/NER/package
            # In local: ../../llm/development_plans/NER/package
            if Path("/llm/development_plans/NER/package").exists():
                llm_path = Path("/llm/development_plans/NER/package")
            else:
                llm_path = Path(__file__).parent.parent.parent.parent.parent / "llm" / "development_plans" / "NER" / "package"

            if str(llm_path) not in sys.path:
                sys.path.insert(0, str(llm_path))

            self.logger.info(f"Added NER package path to sys.path: {llm_path}")

            # Import NER dependencies
            from predictor.predict import NERPredictor
            from utils.gcp_storage import GCPStorage

            # Get GCP configuration from environment
            gcp_project = os.environ.get("GCP_PROJECT")
            gcp_region = os.environ.get("GCP_REGION")
            model_bucket = os.environ.get("FINETUNE_GCS_BUCKET", "spatially-us-central-1-model-training")

            if not gcp_project or not gcp_region:
                raise RuntimeError(
                    "GCP_PROJECT and GCP_REGION environment variables must be set"
                )

            # Initialize GCS client
            credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
            self.logger.info(f"Initializing GCS client with bucket: {model_bucket}")

            storage = GCPStorage(
                gcp_project=gcp_project,
                bucket_name=model_bucket,
                credentials_path=credentials_path,
            )

            # Initialize NER predictor (downloads model from GCS if needed)
            self.logger.info("Initializing NER predictor...")
            self.predictor = NERPredictor(
                gcp_storage=storage,
                gcp_project=gcp_project,
                model_gcs_path="ner_model_output/model/ner_model",
                tokenizer_gcs_path="ner_model_output/model/ner_tokenizer",
                model_bucket=model_bucket,
                device="cpu",  # Use CPU for backend inference
            )

            self.logger.info("✓ NER model loaded successfully")

        except ImportError as e:
            error_msg = (
                f"Failed to import NER dependencies: {e}. "
                "Ensure transformers and torch are installed."
            )
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)

        except Exception as e:
            error_msg = f"Failed to load NER model: {e}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)

    def extract_article_references(self, text: str) -> List[str]:
        """
        Extract ARTICLE_REFERENCE entities from text.

        This method uses the fine-tuned NER model to identify article references
        like "Article 50", "Section 32", etc. in development plan text.

        Args:
            text: Input text to extract article references from

        Returns:
            List of unique article reference strings found in the text
            Example: ["Article 50", "Section 32", "Article 10, Section 5"]

        Raises:
            RuntimeError: If NER model cannot be loaded
        """
        # Ensure model is loaded
        self._ensure_predictor_loaded()

        # Handle empty input
        if not text or not text.strip():
            return []

        try:
            # Use predictor to extract all entities
            entities = self.predictor.predict_entities(text)

            # Filter for ARTICLE_REFERENCE only
            article_refs = [
                entity["text"]
                for entity in entities
                if entity.get("label") == "ARTICLE_REFERENCE"
            ]

            # Remove duplicates while preserving order
            unique_refs = []
            seen = set()
            for ref in article_refs:
                if ref not in seen:
                    seen.add(ref)
                    unique_refs.append(ref)

            self.logger.debug(
                f"Extracted {len(unique_refs)} unique article references from text"
            )
            return unique_refs

        except Exception as e:
            error_msg = f"Error extracting article references: {e}"
            self.logger.error(error_msg)
            raise

    def extract_all_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extract all entity types from text (for future use).

        This method extracts all 7 entity types supported by the NER model:
        - ARTICLE_REFERENCE
        - CONSTRUCTION_DETAILS
        - PROPERTY_USAGE
        - ZONING_DISTRICT
        - ZONING_RELIEF
        - EXPECTED_IMPACT
        - LOCATION_CONTEXT

        Args:
            text: Input text to extract entities from

        Returns:
            Dictionary mapping entity type to list of extracted texts
            Example: {
                "ARTICLE_REFERENCE": ["Article 50", "Section 32"],
                "ZONING_DISTRICT": ["R1"],
                "CONSTRUCTION_DETAILS": ["5-story building"],
                ...
            }

        Raises:
            RuntimeError: If NER model cannot be loaded
        """
        # Ensure model is loaded
        self._ensure_predictor_loaded()

        # Handle empty input
        if not text or not text.strip():
            return {}

        try:
            # Extract all entities
            entities = self.predictor.predict_entities(text)

            # Group by type
            grouped = self.predictor.group_entities_by_type(entities)

            self.logger.debug(
                f"Extracted {len(entities)} entities across {len(grouped)} types"
            )
            return grouped

        except Exception as e:
            error_msg = f"Error extracting entities: {e}"
            self.logger.error(error_msg)
            raise
