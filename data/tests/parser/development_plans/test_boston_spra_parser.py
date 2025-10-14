#!/usr/bin/env python3
"""Test Small Project Review Application parser."""

import sys
import unittest
from pathlib import Path
import json

# Add parent directory to path to import parser modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from collector.development_plans.boston import BostonDevelopmentPlansCollector
from parser.development_plans.boston import BostonDevelopmentPlansParser


class TestSPRAParser(unittest.TestCase):
    """Test Small Project Review Application parser."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        try:
            cls.parser = BostonDevelopmentPlansParser(
                model="llama3.2",
                resource_download_directory=f"{BostonDevelopmentPlansCollector.download_directory()}/pdfs"
            )

            # Find all SPRA PDFs
            pdf_dir = Path(BostonDevelopmentPlansCollector.download_directory()) / "pdfs"
            cls.spra_pdfs = list(pdf_dir.rglob("*Small_Project_Review*.pdf"))
            cls.ollama_available = True
        except Exception as e:
            if "ollama" in str(e).lower() or "could not connect" in str(e).lower():
                cls.ollama_available = False
                cls.spra_pdfs = []
            else:
                raise

    def test_spra_parser_exists(self):
        """Test that parse_spra method exists."""
        if not self.ollama_available:
            self.skipTest("Ollama not available")

        self.assertTrue(hasattr(self.parser, "parse_spra"))
        self.assertTrue(callable(self.parser.parse_spra))

    def test_spra_parsing_on_all_documents(self):
        """Test SPRA parsing on all Small_Project_Review*.pdf files."""
        if not self.ollama_available:
            self.skipTest("Ollama not available")

        if not self.spra_pdfs:
            self.skipTest("No SPRA PDFs found")

        print(f"\n{'='*80}")
        print(f"Testing SPRA parser on {len(self.spra_pdfs)} Small Project Review Application documents")
        print(f"{'='*80}\n")

        results = []
        errors = []

        for i, pdf_path in enumerate(self.spra_pdfs, 1):
            project_name = pdf_path.parent.name
            print(f"\n[{i}/{len(self.spra_pdfs)}] Processing: {project_name}")

            try:
                result = self.parser.parse_spra(str(pdf_path))

                if "error" in result:
                    errors.append({
                        "project": project_name,
                        "error": result["error"]
                    })
                    print(f"❌ ERROR: {result['error']}")
                else:
                    num_sections = len(result.get("zoning_sections", []))
                    has_variances = bool(result.get("variances", "").strip())

                    print(f"✅ Found {num_sections} section(s), Variances: {'Yes' if has_variances else 'No'}")

                    # Print section headers and variances preview
                    if has_variances:
                        variances_preview = result.get("variances", "")[:100].replace("\n", " ")
                        print(f"   📝 Variances: {variances_preview}{'...' if len(result.get('variances', '')) > 100 else ''}")

                    for section in result.get("zoning_sections", []):
                        header = section.get("header", "Unknown")
                        print(f"   📋 {header}")

                    results.append({
                        "project": project_name,
                        "num_sections": num_sections,
                        "has_variances": has_variances,
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
        print("SPRA PARSER SUMMARY")
        print(f"{'='*80}")
        print(f"✅ Successfully parsed: {len(results)}")
        print(f"❌ Errors: {len(errors)}")

        if results:
            success_rate = len(results) / len(self.spra_pdfs) * 100
            print(f"📊 Success rate: {success_rate:.1f}%")

            has_variances = sum(1 for r in results if r["has_variances"])
            print(f"📊 Documents with variances: {has_variances}/{len(results)} ({has_variances/len(results)*100:.1f}%)")

            section_counts = [r["num_sections"] for r in results]
            if section_counts:
                print(f"📊 Average sections per document: {sum(section_counts)/len(section_counts):.1f}")

            # Collect all unique headers
            all_headers = set()
            for r in results:
                all_headers.update(r["headers"])

            print(f"\n📝 Unique section headers found ({len(all_headers)}):")
            for header in sorted(all_headers):
                print(f"   • {header}")

        if errors:
            print(f"\n❌ Errors encountered:")
            for error in errors[:10]:  # Show first 10 errors
                print(f"   • {error['project']}: {error['error']}")
            if len(errors) > 10:
                print(f"   ... and {len(errors) - 10} more errors")

        # Save detailed results
        output_file = "spra_parser_test_results.json"
        with open(output_file, "w") as f:
            json.dump({
                "successful": results,
                "errors": errors,
                "total_tested": len(self.spra_pdfs),
                "success_rate": f"{len(results)/len(self.spra_pdfs)*100:.1f}%" if self.spra_pdfs else "0%"
            }, f, indent=2)

        print(f"\n💾 Detailed results saved to: {output_file}")

        # Assert at least 50% success rate for SPRA (may be lower due to variability)
        if self.spra_pdfs:
            success_rate = len(results) / len(self.spra_pdfs) * 100
            self.assertGreaterEqual(success_rate, 50.0,
                f"SPRA parser success rate {success_rate:.1f}% is below 50%")


if __name__ == "__main__":
    unittest.main()
