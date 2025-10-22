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


class BaseLabelStudioService(ABC):
    """
    Base service class for Label Studio NER annotation.

    This service provides a framework for managing Label Studio across
    different dataset types (development_plans, zba, census, etc.).

    Features:
    - Data preparation from PDFs
    - Metadata enrichment from collector CSVs
    - Label Studio lifecycle (start/stop/status)
    - Export management
    """

    def __init__(self):
        """Initialize Label Studio service."""
        self.base_dir = Path(__file__).parent.parent
        self.label_studio_dir = self.base_dir / "label_studio"
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

    @abstractmethod
    def pdf_directory(self) -> Path:
        """Return path to PDF directory."""
        pass

    @abstractmethod
    def csv_file(self) -> Path:
        """Return path to collector CSV file with metadata."""
        pass

    @abstractmethod
    def import_file(self) -> Path:
        """Return path to Label Studio import JSON file."""
        pass

    @abstractmethod
    def config_file(self) -> Path:
        """Return path to Label Studio config XML file."""
        pass

    @abstractmethod
    def export_directory(self) -> Path:
        """Return path to exports directory."""
        pass

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

    def load_metadata_from_csv(self) -> Dict:
        """
        Load project metadata from collector's CSV file.

        Returns:
            Dictionary mapping (project_name, document_type) to metadata
        """
        csv_path = self.csv_file()

        if not csv_path.exists():
            self.logger.warning(f"CSV file not found: {csv_path}")
            return {}

        try:
            df = pd.read_csv(csv_path)

            metadata = {}
            for _, row in df.iterrows():
                key = (row.get("project_name", ""), row.get("document_type", ""))
                metadata[key] = {
                    "neighborhood": row.get("neighborhood", ""),
                    "address": row.get("address", ""),
                    "project_status": row.get("project_status", ""),
                    "project_type": row.get("project_type", ""),
                    "gross_floor_area": row.get("gross_floor_area", ""),
                    "land_sq_feet": row.get("land_sq_feet", ""),
                    "project_description": row.get("project_description", ""),
                }

            self.logger.info(
                f"✓ Loaded metadata for {len(metadata)} project-document combinations"
            )
            return metadata

        except Exception as e:
            self.logger.error(f"Error loading CSV metadata: {e}")
            return {}

    @abstractmethod
    def get_document_types(self) -> dict:
        """
        Return document types mapping.

        Returns:
            Dictionary mapping document type keys to their display names
            Example: {"spra": "Small Project Review Application", "loi": "Letter of Intent"}
        """
        pass

    def infer_document_type(self, filename: str) -> str:
        """
        Infer document type key from filename.

        Uses get_document_types() and automatically derives patterns from names.

        Args:
            filename: Document filename

        Returns:
            Document type key (e.g., "spra", "loi", "imp")
        """
        filename_lower = filename.lower()
        doc_types = self.get_document_types()

        # Check each document type by matching the lowercased name in the filename
        for key, name in doc_types.items():
            if key == "all":
                continue
            if name.lower() in filename_lower:
                return key

        return "other"

    def prepare_annotation_data(
        self,
        doc_type_filter: Optional[str] = None,
    ) -> List[Dict]:
        """
        Prepare PDF data for Label Studio annotation.

        Args:
            doc_type_filter: Filter by document type (optional)

        Returns:
            List of Label Studio task dictionaries
        """
        doc_type_label = doc_type_filter if doc_type_filter else "all"
        pdf_dir = self.pdf_directory()

        if not pdf_dir.exists():
            self.logger.error(f"PDF directory not found: {pdf_dir}")
            self.logger.info("Please run the collector first to download PDFs")
            return []

        # Load metadata
        metadata_lookup = self.load_metadata_from_csv()

        # Find all PDFs
        pdf_files = sorted(pdf_dir.rglob("*.pdf"))  # full path objects

        if doc_type_filter and doc_type_filter != "all":
            doc_type_filter_name = self.get_document_types()[doc_type_filter]
            pdf_files = [
                f for f in pdf_files if doc_type_filter_name in f.name.replace("_", " ")
            ]

        self.logger.info(f"Document type filter: {doc_type_filter}")
        self.logger.info(f"Found {len(pdf_files)} PDF files")
        self.logger.info(f"Processing PDFs from {pdf_dir}")

        tasks = []
        for idx, pdf_path in enumerate(pdf_files, 1):
            self.logger.info(f"[{idx}/{len(pdf_files)}] Processing: {pdf_path.name}")

            # Extract full text
            text = self.extract_text_from_pdf(pdf_path)

            if not text:
                self.logger.warning(f"  ⚠️  Skipping (no text extracted)")
                continue

            # Get project name from directory structure
            project_name_raw = (
                pdf_path.parent.name if pdf_path.parent.name != "pdfs" else "Unknown"
            )
            project_name = project_name_raw.replace("_", " ")

            # Infer document type key (replace underscores with spaces for consistency)
            doc_type_key = self.infer_document_type(pdf_path.name.replace("_", " "))
            doc_type_name = self.get_document_types().get(doc_type_key, "Other")

            # Get metadata
            metadata_key = (project_name, doc_type_name)
            metadata = metadata_lookup.get(metadata_key, {})

            # Helper function to convert NaN to None for JSON serialization
            def clean_value(val):
                """Convert pandas NaN to None for valid JSON."""
                if pd.isna(val):
                    return None
                return val

            # Generate file URL/path based on storage mode
            if self.use_gcs and self.gcs_bucket:
                # For GCS: generate gs:// URL
                relative_path = pdf_path.relative_to(pdf_dir.parent.parent)
                file_url = f"gs://{self.gcs_bucket}/{relative_path}"
                source_path = str(relative_path)
            else:
                # For local: use relative file path
                file_url = str(pdf_path.relative_to(pdf_dir.parent.parent))
                source_path = file_url

            # Create Label Studio task
            task = {
                "data": {
                    "text": text,
                    "project_name": project_name,
                    "file_name": pdf_path.name,
                    "file_path": file_url,
                },
                "predictions": [
                    {
                        "model_version": "pre-annotation",
                        "result": [],
                    }
                ],
                "meta": {
                    "source": source_path,
                    "project": project_name,
                    "doc_type_hint": doc_type_name,
                    "char_count": len(text),
                    "storage_mode": "gcs" if self.use_gcs else "local",
                    "neighborhood": clean_value(metadata.get("neighborhood", "")),
                    "address": clean_value(metadata.get("address", "")),
                    "project_status": clean_value(metadata.get("project_status", "")),
                    "project_type": clean_value(metadata.get("project_type", "")),
                    "gross_floor_area": clean_value(
                        metadata.get("gross_floor_area", "")
                    ),
                    "land_sq_feet": clean_value(metadata.get("land_sq_feet", "")),
                },
            }

            tasks.append(task)
            enriched = "✓" if metadata else "○"
            self.logger.info(
                f"  {enriched} Added ({len(text)} chars, type: {doc_type_name})"
            )

        # Write output with doc type in filename
        output_file = self.import_file(doc_type=doc_type_label)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=2, ensure_ascii=False)

        self.logger.info(f"\n✨ Created {len(tasks)} tasks in {output_file}")

        return tasks

    def start_label_studio(self, detached: bool = True) -> bool:
        """
        Start Label Studio service using docker-compose.

        Args:
            detached: Run in background (default: True)

        Returns:
            True if successful, False otherwise
        """
        try:
            cmd = [
                "docker",
                "compose",
                "-f",
                str(self.base_dir / "docker-compose.dev.yml"),
                "up",
            ]

            if detached:
                cmd.append("-d")

            cmd.append("label-studio")

            self.logger.info("Starting Label Studio...")
            subprocess.run(
                cmd, cwd=self.base_dir, check=True, capture_output=True, text=True
            )

            if detached:
                self.logger.info("✓ Label Studio started successfully")
                self.logger.info("  URL: http://localhost:8080")
                self.logger.info(f"  Config: {self.config_file()}")
                self.logger.info(f"  Import: {self.import_file()}")

            return True

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to start Label Studio: {e}")
            if e.stderr:
                self.logger.error(e.stderr)
            return False

    def stop_label_studio(self) -> bool:
        """
        Stop Label Studio service.

        Returns:
            True if successful, False otherwise
        """
        try:
            cmd = [
                "docker",
                "compose",
                "-f",
                str(self.base_dir / "docker-compose.dev.yml"),
                "stop",
                "label-studio",
            ]

            self.logger.info("Stopping Label Studio...")
            subprocess.run(cmd, cwd=self.base_dir, check=True)

            self.logger.info("✓ Label Studio stopped successfully")
            return True

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to stop Label Studio: {e}")
            return False

    def restart_label_studio(self) -> bool:
        """
        Restart Label Studio service.

        Returns:
            True if successful, False otherwise
        """
        try:
            cmd = [
                "docker",
                "compose",
                "-f",
                str(self.base_dir / "docker-compose.dev.yml"),
                "restart",
                "label-studio",
            ]

            self.logger.info("Restarting Label Studio...")
            subprocess.run(cmd, cwd=self.base_dir, check=True)

            self.logger.info("✓ Label Studio restarted successfully")
            self.logger.info("  URL: http://localhost:8080")
            return True

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to restart Label Studio: {e}")
            return False

    def status(self) -> Dict:
        """
        Get Label Studio service status.

        Returns:
            Dictionary with status information
        """
        status_info = {
            "running": False,
            "url": "http://localhost:8080",
            "config_file": str(self.config_file()),
            "import_file": str(self.import_file()),
            "import_exists": self.import_file().exists(),
            "export_directory": str(self.export_directory()),
        }

        try:
            result = subprocess.run(
                [
                    "docker",
                    "ps",
                    "--filter",
                    "name=label_studio",
                    "--format",
                    "{{.Status}}",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            if result.stdout.strip():
                status_info["running"] = True
                status_info["status"] = result.stdout.strip()

        except subprocess.CalledProcessError:
            pass

        return status_info

    def show_logs(self, follow: bool = False, tail: int = 100) -> None:
        """
        Show Label Studio logs.

        Args:
            follow: Follow log output (default: False)
            tail: Number of lines to show (default: 100)
        """
        cmd = ["docker", "logs"]

        if follow:
            cmd.append("-f")
        else:
            cmd.extend(["--tail", str(tail)])

        cmd.append("label_studio")

        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to get logs: {e}")

    def setup_exports_directory(self) -> None:
        """Create exports directory if it doesn't exist."""
        export_dir = self.export_directory()
        export_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"✓ Exports directory ready: {export_dir}")

    def print_setup_instructions(self) -> None:
        """Print setup instructions for Label Studio."""
        status = self.status()

        print("\n" + "=" * 70)
        print(f"  Label Studio NER Annotation Service")
        print("=" * 70)
        print(f"\n📊 Status: {'🟢 Running' if status['running'] else '🔴 Stopped'}")
        print(f"🌐 URL: {status['url']}")
        print(f"📁 Config: {status['config_file']}")
        print(
            f"📥 Import: {status['import_file']} {'✓' if status['import_exists'] else '✗'}"
        )
        print(f"📤 Exports: {status['export_directory']}")

        print("\n" + "=" * 70)
        print("  Quick Setup Steps")
        print("=" * 70)
        print("\n1️⃣  Open Label Studio in your browser:")
        print(f"   → {status['url']}")

        print("\n2️⃣  Create an account (first time only)")

        print("\n3️⃣  Create a new project:")
        print("   • Name: 'Boston Development Plans NER'")
        print("   • Click 'Create'")

        print("\n4️⃣  Import labeling configuration:")
        print("   • Go to: Settings → Labeling Interface")
        print("   • Click 'Code' view")
        print(f"   • Copy contents from: {status['config_file']}")
        print("   • Paste and Save")

        print("\n5️⃣  Import annotation data:")
        print("   • Click 'Import' button")
        print(f"   • Upload file: {status['import_file']}")
        print("   • Click 'Import'")

        print("\n6️⃣  Start annotating!")
        print("   • Use hotkeys 0-9 for quick labeling")
        print("   • See config.xml for entity types")

        print("\n" + "=" * 70)
        print()
