import re
import sys
from .base import BaseDevelopmentPlansParser
from collector.development_plans.boston import BostonDevelopmentPlansCollector
import glob
import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Set, Optional
import pymupdf
import fitz
import ollama


# Set up logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class BostonDevelopmentPlansParser(BaseDevelopmentPlansParser):
    """
    Parser for Boston development plans documents using open source models.

    Extracts:
    1. Context - The background and details of the development project
    2. Purpose - The intended use and goals of the project
    3. Zoning Relief Types - Specific zoning variances or relief being requested

    This creates labeled training data for your zoning relief prediction model.

    Document types supported:
    1. Letter of Intent (LOI) - Short letter about the project
    2. Small Project Review Application (SPRA) - Detailed application for small projects
    3. Institutional Master Plan Notification Form (IMPNF) - Application for large projects
    4. Planned Development Area (PDA) Development Plan - Comprehensive plan
    5. PDA Development Plan Fact Sheet - Summary of PDA plan
    """

    @classmethod
    def city(cls) -> str:
        return BostonDevelopmentPlansCollector.city()

    def __init__(
        self,
        model: str = "llama3.2",
        resource_download_directory: str = None,
    ):
        """
        Initialize the parser with open source Ollama backend.

        Args:
            collector: BostonDevelopmentPlansCollector instance
            model: Ollama model to use (default: llama3.2)
        """

        super().__init__(resource_download_directory)
        self.logger = logger
        self.output_directory = (
            f"{BostonDevelopmentPlansCollector.download_directory()}/parsed"
        )
        self.zoning_relief_types_file = (
            f"{self.output_directory}/zoning_relief_types.json"
        )
        self.parsed_data_file = f"{self.output_directory}/parsed_data.json"

        self.model = model
        self.logger.info(f"Using Ollama with model: {self.model}")

        # Test Ollama connection
        try:
            print(ollama.list())
            self.logger.info("Ollama connection successful")
        except Exception as e:
            self.logger.error(f"Could not connect to Ollama: {e}")
            self.logger.error("Make sure Ollama is running: ollama serve")
            raise

        # Create output directory
        os.makedirs(self.output_directory, exist_ok=True)

    def read_pdf_directory(self) -> Dict[str, List[str]]:
        """
        Returns a dictionary mapping each top-level folder in the
        download directory to its list of PDF files (as strings).
        Ignores folders that have no PDF files.
        """
        pdf_dir = self.resource_download_directory
        print("This is the pdf_dir", pdf_dir)
        results = {}
        for root, dirs, files in os.walk(pdf_dir):
            pdf_files = [
                os.path.join(root, f) for f in files if f.lower().endswith(".pdf")
            ]
            if pdf_files:
                # The key is the folder name relative to the base directory
                key = os.path.relpath(root, pdf_dir)
                results[key] = pdf_files
        # Remove any empty key values (i.e., empty folders)
        results = {k: v for k, v in results.items() if v}
        self.logger.info(
            f"Found PDF files in {len(results)} folders; total {sum(len(v) for v in results.values())} PDFs."
        )
        return results

    def extract_pdf_content(self, pdf_path: str) -> Optional[str]:
        """
        Extract text content from PDF using pymupdf.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Extracted text or None if extraction fails
        """
        try:
            doc = pymupdf.open(pdf_path)
            text_parts = []

            for page in doc:
                text_parts.append(page.get_text())

            doc.close()

            full_text = "\n".join(text_parts)
            return full_text if full_text.strip() else None

        except Exception as e:
            self.logger.error(f"Error extracting PDF with pymupdf from {pdf_path}: {e}")
            return None

    def extract_zoning_reliefs_from_text(self, text: str, document_type: str) -> Dict:
        """
        Use Ollama (open source model) to extract zoning relief information.
        This creates labeled training data for your model.

        Args:
            text: The document text content
            document_type: Type of document (LOI, SPRA, IMPNF, PDA, etc.)

        Returns:
            Dictionary with context, purpose, and zoning relief types
        """
        try:
            prompt = f"""Analyze this Boston development plan document (type: {document_type}) and extract information for training data.

Extract these fields:
1. Context: Detailed description of the development project including location, property details, developer, and neighborhood
2. Purpose: Intended use and goals including proposed use, number of units, goals, and community benefits
3. Zoning Relief Types: ALL specific zoning variances or relief requested. Be thorough and list every type mentioned.

Common relief types include:
- Height relief / Height variance
- Setback reduction (front, side, rear)
- FAR (Floor Area Ratio) increase
- Lot coverage increase
- Parking reduction
- Use variance
- Density increase
- Open space reduction

Respond ONLY with valid JSON in this exact format:
{{
  "context": "detailed description here",
  "purpose": "purpose and goals here",
  "zoning_relief_types": ["specific relief 1", "specific relief 2", "..."]
}}

Document text (first 10000 characters):
{text[:10000]}"""

            response = ollama.generate(
                model=self.model,
                prompt=prompt,
                options={
                    "temperature": 0.1,  # Low temperature for consistent extraction
                    "num_predict": 1536,  # Allow longer responses
                },
            )

            response_text = response["response"]

            # Parse JSON from response
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            result = json.loads(response_text)
            return result

        except Exception as e:
            self.logger.error(f"Error extracting zoning reliefs: {e}")
            return {"error": str(e)}

    def discover_all_zoning_relief_types(self, parsed_results: List[Dict]) -> Set[str]:
        """
        Discover all unique zoning relief types across all documents.

        Args:
            parsed_results: List of parsed document results

        Returns:
            Set of unique zoning relief type strings
        """
        all_relief_types = set()

        for result in parsed_results:
            if "zoning_relief_types" in result and result["zoning_relief_types"]:
                for relief_type in result["zoning_relief_types"]:
                    # Normalize and add to set
                    normalized = relief_type.strip().lower()
                    all_relief_types.add(normalized)

        self.logger.info(
            f"Discovered {len(all_relief_types)} unique zoning relief types"
        )
        return all_relief_types

    def parse_letter_of_intent(self, pdf_path: str) -> Dict:
        """
        This is called for documents with Letter_of_Intent in the name.
        """
        pdf_text = self.extract_pdf_content(pdf_path)
        # This LOI document is small enough so we can safely
        pass

    def parse_spra(self, pdf_path: str) -> Dict:
        """
        Parse Small Project Review Application (SPRA) documents.

        SPRA documents typically have:
        - Variances section listing required relief
        - Zoning Analysis section
        - Project overview with zoning district

        Returns:
            Dict with context, purpose, and zoning relief types
        """
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text("text")

        # Extract project name from path
        path_parts = Path(pdf_path).parts
        project_name = path_parts[-2] if len(path_parts) >= 2 else "Unknown"

        # Look for "Variances:" section which lists required relief
        variances_match = re.search(
            r"Variances?:\s*([^\n]+(?:\n(?!\n)[^\n]+)*)", text, re.IGNORECASE
        )
        variances_text = variances_match.group(1) if variances_match else ""

        # Look for "Zoning Analysis" or "Zoning District" sections
        zoning_sections = []

        # Find Zoning District info
        zoning_district_match = re.search(
            r"Zoning District:\s*([^\n]+(?:\n(?!\n)[^\n]+)*)", text, re.IGNORECASE
        )
        if zoning_district_match:
            zoning_sections.append(
                {
                    "header": "Zoning District",
                    "content": zoning_district_match.group(1).strip(),
                }
            )

        # Find Zoning Analysis section (look for it as a section header)
        analysis_match = re.search(
            r"(Zoning Analysis[^\n]*)\n+(.*?)(?=\n[A-Z][a-z]+\s+[A-Z][a-z]+|\Z)",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if analysis_match:
            zoning_sections.append(
                {
                    "header": analysis_match.group(1).strip(),
                    "content": analysis_match.group(2).strip()[
                        :1000
                    ],  # Limit to first 1000 chars
                }
            )

        # Combine all zoning information
        combined_text = f"Variances: {variances_text}\n\n"
        for section in zoning_sections:
            combined_text += f"{section['header']}\n{section['content']}\n\n"

        self.logger.info(
            f"Found variances and {len(zoning_sections)} zoning section(s) in SPRA"
        )

        return {
            "project_name": project_name,
            "document_type": "SPRA",
            "variances": variances_text,
            "zoning_sections": zoning_sections,
            "combined_zoning_text": combined_text.strip(),
        }

    def parse_bpda(self, pdf_path: str) -> Dict:
        """
        Parse BPDA Board approval documents.

        Extracts all sections that start with "ZONING" (case-insensitive),
        ignoring document headers like BOARD APPROVED and DOCUMENT NO.

        Returns:
            Dict with context, purpose, and zoning relief types
        """
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text("text")

        # Headers to ignore (common document metadata)
        ignore_headers = ["BOARD APPROVED", "DOCUMENT NO", "MEMORANDUM"]

        # 1️⃣ Find ALL section headers (all-caps lines)
        pattern = r"\n([A-Z][A-Z\s&\-:]{5,})\n"  # all-caps lines (≥5 chars, allows spaces, &, -, :)
        all_headers = [
            (m.start(), m.group(1).strip()) for m in re.finditer(pattern, text)
        ]

        # Filter out ignore headers and find ZONING sections
        valid_headers = [
            (pos, header)
            for pos, header in all_headers
            if not any(ignore in header for ignore in ignore_headers)
        ]

        # 2️⃣ Extract all sections that contain "ZONING" in the header
        zoning_sections = []
        for i, (pos, header) in enumerate(valid_headers):
            if "ZONING" in header.upper():
                # Find where this section ends (start of next header or end of document)
                end_pos = (
                    valid_headers[i + 1][0] if i + 1 < len(valid_headers) else len(text)
                )
                section_text = text[pos:end_pos].strip()
                zoning_sections.append({"header": header, "content": section_text})

        if not zoning_sections:
            self.logger.warning(f"No ZONING sections found in {pdf_path}")
            return {"error": "No ZONING sections found"}

        # 3️⃣ Combine all zoning sections
        combined_zoning_text = "\n\n".join(
            [
                f"{section['header']}\n{section['content']}"
                for section in zoning_sections
            ]
        )

        self.logger.info(f"Found {len(zoning_sections)} ZONING section(s)")

        # Extract project name from path
        path_parts = Path(pdf_path).parts
        project_name = path_parts[-2] if len(path_parts) >= 2 else "Unknown"

        return {
            "project_name": project_name,
            "document_type": "BPDA_Board",
            "zoning_sections": zoning_sections,
            "combined_zoning_text": combined_zoning_text,
        }

    def parse(self) -> Dict:
        """
        Main parsing method that processes all PDFs and extracts information.

        Returns:
            Dictionary with parsed results and discovered zoning relief types
        """
        self.logger.info("Starting Boston development plans parsing")

        # This will return a dictionary mapping each top-level folder in the
        # download directory to its list of PDF files (as strings).
        pdf_files_by_folder = self.read_pdf_directory()

        if not pdf_files_by_folder:
            self.logger.warning("No PDF files found to parse")
            return {"error": "No PDF files found"}
        print(pdf_files_by_folder)
        for folder, pdf_list in pdf_files_by_folder.items():
            for pdf_path in pdf_list:
                if "BPDA_Board" in pdf_path:
                    self.parse_bpda(pdf_path)
                elif "Small_Project_Review" in pdf_path:
                    self.parse_spra(pdf_path)
                elif "Letter_of_Intent" in pdf_path:
                    self.parse_letter_of_intent(pdf_path)
                else:
                    continue
        return {"error": "Parsing process stopped early (sys.exit() was removed)."}
        # Flatten the dictionary to get all PDF paths
        all_pdf_paths = []
        for folder, pdf_list in pdf_files_by_folder.items():
            all_pdf_paths.extend(pdf_list)

        self.logger.info(f"Found {len(all_pdf_paths)} total PDF files to parse")

        # Parse each PDF
        parsed_results = []

        for idx, pdf_path in enumerate(all_pdf_paths, 1):
            self.logger.info(f"Processing {idx}/{len(all_pdf_paths)}: {pdf_path}")

            # Extract project name and document type from path
            # Path structure: .../pdfs/Project_Name/Document_Type.pdf
            path_parts = Path(pdf_path).parts
            project_name = path_parts[-2] if len(path_parts) >= 2 else "Unknown"
            document_type = Path(pdf_path).stem.replace("_", " ")

            # Extract PDF content
            pdf_text = self.extract_pdf_content(pdf_path)

            if not pdf_text:
                self.logger.warning(f"Failed to extract content from {pdf_path}")
                continue

            # Extract zoning relief information
            extraction_result = self.extract_zoning_reliefs_from_text(
                pdf_text, document_type
            )

            if "error" not in extraction_result:
                extraction_result["project_name"] = project_name
                extraction_result["document_type"] = document_type
                extraction_result["pdf_path"] = pdf_path
                parsed_results.append(extraction_result)
                self.logger.info(
                    f"Successfully parsed {project_name} - {document_type}"
                )
            else:
                self.logger.error(
                    f"Failed to parse {pdf_path}: {extraction_result['error']}"
                )

        # Discover all unique zoning relief types
        zoning_relief_types = self.discover_all_zoning_relief_types(parsed_results)

        # Save zoning relief types
        with open(self.zoning_relief_types_file, "w") as f:
            json.dump(
                {
                    "relief_types": sorted(list(zoning_relief_types)),
                    "count": len(zoning_relief_types),
                },
                f,
                indent=2,
            )

        self.logger.info(
            f"Saved zoning relief types to {self.zoning_relief_types_file}"
        )

        # Save parsed results
        with open(self.parsed_data_file, "w") as f:
            json.dump(
                {
                    "parsed_documents": parsed_results,
                    "total_documents": len(parsed_results),
                    "unique_relief_types": sorted(list(zoning_relief_types)),
                },
                f,
                indent=2,
            )

        self.logger.info(f"Saved parsed data to {self.parsed_data_file}")

        return {
            "parsed_documents": parsed_results,
            "total_documents": len(parsed_results),
            "unique_relief_types": sorted(list(zoning_relief_types)),
            "output_directory": self.output_directory,
        }
