#!/usr/bin/env python3
"""Test BPDA Board document parser."""

import sys
import unittest
from pathlib import Path
import json

# Add parent directory to path to import parser modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from collector.development_plans.boston import BostonDevelopmentPlansCollector
from parser.development_plans.boston import BostonDevelopmentPlansParser


class TestBPDAParser(unittest.TestCase):
    """Test BPDA Board document parser."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        try:
            cls.parser = BostonDevelopmentPlansParser(
                model="llama3.2",
                resource_download_directory=f"{BostonDevelopmentPlansCollector.download_directory()}/pdfs"
            )

            # Find all BPDA Board PDFs
            pdf_dir = Path(BostonDevelopmentPlansCollector.download_directory()) / "pdfs"
            cls.bpda_pdfs = list(pdf_dir.rglob("BPDA_Board.pdf"))
            cls.ollama_available = True
        except Exception as e:
            if "ollama" in str(e).lower() or "could not connect" in str(e).lower():
                cls.ollama_available = False
                cls.bpda_pdfs = []
            else:
                raise

    def test_bpda_parser_exists(self):
        """Test that parse_bpda method exists."""
        if not self.ollama_available:
            self.skipTest("Ollama not available")

        self.assertTrue(hasattr(self.parser, "parse_bpda"))
        self.assertTrue(callable(self.parser.parse_bpda))

    def test_bpda_parsing_on_all_documents(self):
        """Test BPDA parsing on all BPDA_Board.pdf files."""
        if not self.ollama_available:
            self.skipTest("Ollama not available")

        if not self.bpda_pdfs:
            self.skipTest("No BPDA Board PDFs found")

        print(f"\n{'='*80}")
        print(f"Testing BPDA parser on {len(self.bpda_pdfs)} BPDA Board documents")
        print(f"{'='*80}\n")

        results = []
        errors = []

        for i, pdf_path in enumerate(self.bpda_pdfs, 1):
            project_name = pdf_path.parent.name
            print(f"\n[{i}/{len(self.bpda_pdfs)}] Processing: {project_name}")

            try:
                result = self.parser.parse_bpda(str(pdf_path))

                if "error" in result:
                    errors.append({
                        "project": project_name,
                        "error": result["error"]
                    })
                    print(f"❌ ERROR: {result['error']}")
                else:
                    num_sections = len(result.get("zoning_sections", []))
                    print(f"✅ Found {num_sections} ZONING section(s)")

                    # Print section headers
                    for section in result.get("zoning_sections", []):
                        header = section.get("header", "Unknown")
                        print(f"   📋 {header}")

                    results.append({
                        "project": project_name,
                        "num_sections": num_sections,
                        "headers": [s.get("header") for s in result.get("zoning_sections", [])],
                        "has_combined_text": bool(result.get("combined_zoning_text"))
                    })

            except Exception as e:
                errors.append({
                    "project": project_name,
                    "error": str(e)
                })
                print(f"❌ EXCEPTION: {e}")

        # Summary
        print(f"\n{'='*80}")
        print("BPDA PARSER SUMMARY")
        print(f"{'='*80}")
        print(f"✅ Successfully parsed: {len(results)}")
        print(f"❌ Errors: {len(errors)}")

        if results:
            success_rate = len(results) / len(self.bpda_pdfs) * 100
            print(f"📊 Success rate: {success_rate:.1f}%")

            section_counts = [r["num_sections"] for r in results]
            print(f"📊 Average sections per document: {sum(section_counts)/len(section_counts):.1f}")

            # Collect all unique headers
            all_headers = set()
            for r in results:
                all_headers.update(r["headers"])

            print(f"\n📝 Unique ZONING section headers found ({len(all_headers)}):")
            for header in sorted(all_headers):
                print(f"   • {header}")

        if errors:
            print(f"\n❌ Errors encountered:")
            for error in errors[:10]:  # Show first 10 errors
                print(f"   • {error['project']}: {error['error']}")
            if len(errors) > 10:
                print(f"   ... and {len(errors) - 10} more errors")

        # Save detailed results
        output_file = "bpda_parser_test_results.json"
        with open(output_file, "w") as f:
            json.dump({
                "successful": results,
                "errors": errors,
                "total_tested": len(self.bpda_pdfs),
                "success_rate": f"{len(results)/len(self.bpda_pdfs)*100:.1f}%" if self.bpda_pdfs else "0%"
            }, f, indent=2)

        print(f"\n💾 Detailed results saved to: {output_file}")

        # Assert at least 70% success rate
        if self.bpda_pdfs:
            success_rate = len(results) / len(self.bpda_pdfs) * 100
            self.assertGreaterEqual(success_rate, 70.0,
                f"BPDA parser success rate {success_rate:.1f}% is below 70%")


if __name__ == "__main__":
    unittest.main()
