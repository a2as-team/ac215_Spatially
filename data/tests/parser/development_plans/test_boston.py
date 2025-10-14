import sys
import unittest
from pathlib import Path
import os
import json

# Add parent directory to path to import parser modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from collector.development_plans.boston import BostonDevelopmentPlansCollector
from parser.development_plans.boston import BostonDevelopmentPlansParser


class TestBostonDevelopmentPlansParser(unittest.TestCase):
    """Minimal tests for BostonDevelopmentPlansParser."""

    def test_parser_initialization(self):
        """Test that parser initializes correctly."""
        try:
            parser = BostonDevelopmentPlansParser(
                model="llama3.2",
                resource_download_directory=f"{BostonDevelopmentPlansCollector.download_directory()}/pdfs"
            )
            self.assertIsNotNone(parser)
            self.assertEqual(parser.model, "llama3.2")
        except Exception as e:
            # If Ollama is not available, skip test
            if "ollama" in str(e).lower() or "could not connect" in str(e).lower():
                self.skipTest("Ollama not available")
            else:
                raise

    def test_pdf_extraction_method_exists(self):
        """Test that PDF extraction method exists."""
        try:
            parser = BostonDevelopmentPlansParser(
                model="llama3.2",
                resource_download_directory=f"{BostonDevelopmentPlansCollector.download_directory()}/pdfs"
            )
            self.assertTrue(hasattr(parser, "extract_pdf_content"))
            self.assertTrue(callable(parser.extract_pdf_content))
        except Exception as e:
            if "ollama" in str(e).lower() or "could not connect" in str(e).lower():
                self.skipTest("Ollama not available")
            else:
                raise

    def test_zoning_relief_extraction_method_exists(self):
        """Test that zoning relief extraction method exists."""
        try:
            parser = BostonDevelopmentPlansParser(
                model="llama3.2",
                resource_download_directory=f"{BostonDevelopmentPlansCollector.download_directory()}/pdfs"
            )
            self.assertTrue(hasattr(parser, "extract_zoning_reliefs_from_text"))
            self.assertTrue(callable(parser.extract_zoning_reliefs_from_text))
        except Exception as e:
            if "ollama" in str(e).lower() or "could not connect" in str(e).lower():
                self.skipTest("Ollama not available")
            else:
                raise

    def test_discover_zoning_relief_types(self):
        """Test that discover_all_zoning_relief_types works correctly."""
        try:
            parser = BostonDevelopmentPlansParser(
                model="llama3.2",
                resource_download_directory=f"{BostonDevelopmentPlansCollector.download_directory()}/pdfs"
            )

            # Mock parsed results
            mock_results = [
                {
                    "project_name": "Project A",
                    "context": "Test context",
                    "purpose": "Test purpose",
                    "zoning_relief_types": ["Height relief", "Parking reduction"]
                },
                {
                    "project_name": "Project B",
                    "context": "Test context 2",
                    "purpose": "Test purpose 2",
                    "zoning_relief_types": ["Height relief", "FAR increase"]
                }
            ]

            # Test discovery
            relief_types = parser.discover_all_zoning_relief_types(mock_results)

            self.assertEqual(len(relief_types), 3)
            self.assertIn("height relief", relief_types)
            self.assertIn("parking reduction", relief_types)
            self.assertIn("far increase", relief_types)

        except Exception as e:
            if "ollama" in str(e).lower() or "could not connect" in str(e).lower():
                self.skipTest("Ollama not available")
            else:
                raise

    def test_output_directory_creation(self):
        """Test that output directory is created."""
        try:
            parser = BostonDevelopmentPlansParser(
                model="llama3.2",
                resource_download_directory=f"{BostonDevelopmentPlansCollector.download_directory()}/pdfs"
            )

            # Check that output directory path is set
            self.assertIsNotNone(parser.output_directory)
            self.assertTrue(os.path.exists(parser.output_directory))

        except Exception as e:
            if "ollama" in str(e).lower() or "could not connect" in str(e).lower():
                self.skipTest("Ollama not available")
            else:
                raise

    def test_read_pdf_directory(self):
        """Test that read_pdf_directory method works."""
        try:
            parser = BostonDevelopmentPlansParser(
                model="llama3.2",
                resource_download_directory=f"{BostonDevelopmentPlansCollector.download_directory()}/pdfs"
            )
            pdf_files = parser.read_pdf_directory()

            # Should return a dict mapping folders to PDF lists
            self.assertIsInstance(pdf_files, dict)

        except Exception as e:
            if "ollama" in str(e).lower() or "could not connect" in str(e).lower():
                self.skipTest("Ollama not available")
            else:
                raise


if __name__ == "__main__":
    unittest.main()
