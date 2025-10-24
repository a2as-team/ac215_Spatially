"""Base Label Studio service for NER annotation."""

import json
import os
import re
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional
import logging

import fitz  # pymupdf
import pandas as pd
from .base import BaseProceesor


class LabelStudioBaseProcessor(BaseProceesor, ABC):
    """
    Base service class for data processor.

    This service provides a framework for managing data processor across
    different dataset types (development_plans, zba, census, etc.).
    """

    def __init__(self):
        """Initialize data processor service."""
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        if not self.logger.hasHandlers():
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

        # Check if we should use GCS for storage
        self.use_gcs = os.getenv("USE_GCS_STORAGE", "false").lower() == "true"
        self.gcs_bucket = os.getenv("GCS_BUCKET_NAME", "")
        self.gcs_project = os.getenv("GCP_PROJECT_ID", "")
    
    
    def extract_text_from_pdf(self, pdf_path: Path) -> str:
        """
        Extract full text from PDF file using pymupdf.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Extracted text string
        """
        try:
            doc = fitz.open(pdf_path)

            text_parts = []
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_text = page.get_text()
                text_parts.append(page_text)

            doc.close()

            full_text = "\n\n".join(text_parts)

            # Clean up text - remove null bytes and control characters for PostgreSQL
            full_text = full_text.replace("\x00", "")  # Remove null bytes
            full_text = re.sub(
                r"[\x01-\x08\x0b-\x0c\x0e-\x1f\x7f]", "", full_text
            )  # Remove other control chars
            full_text = re.sub(r"\n{3,}", "\n\n", full_text)
            full_text = re.sub(r" {2,}", " ", full_text)

            return full_text.strip()

        except Exception as e:
            self.logger.error(f"Error extracting text from {pdf_path}: {e}")
            return ""
    
    @abstractmethod
    def load_metadata_from_csv(self):
        """Load metadata from CSV file."""
        pass
    
    @abstractmethod
    def process(self):
        pass