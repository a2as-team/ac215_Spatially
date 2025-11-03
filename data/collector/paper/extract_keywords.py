#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Exact 'Keywords:' field extractor for batch PDFs.

What it does:
- Extract text from each PDF using one of: PyMuPDF (fitz) / pdfminer.six / (PyPDF2|pypdf)
- Find the literal 'Keywords:' (case-insensitive) and capture the subsequent list
  until the first boundary marker (blank line or common headers such as Citation/Received/etc.)
- Normalize separators and whitespace
- Write a 2-column CSV: file, keywords
"""

import re
import csv
from pathlib import Path
from typing import Optional

# -------- Settings --------
PDF_DIR = Path(".")                  # Change to your PDF directory if needed
OUT_CSV = "pdf_keywords.csv"         # Output file name
MAX_CAPTURE_CHARS = 500              # Safety cap for over-greedy captures

# -------- PDF text extraction backends --------
def extract_text_pymupdf(path: Path) -> Optional[str]:
    """Try PyMuPDF (fitz)."""
    try:
        import fitz  # PyMuPDF
    except Exception:
        return None
    try:
        parts = []
        with fitz.open(path) as doc:
            for page in doc:
                parts.append(page.get_text("text"))
        return "\n".join(parts)
    except Exception:
        return None

def extract_text_pdfminer(path: Path) -> Optional[str]:
    """Try pdfminer.six."""
    try:
        from pdfminer.high_level import extract_text
    except Exception:
        return None
    try:
        return extract_text(str(path)) or ""
    except Exception:
        return None

def extract_text_pypdf(path: Path) -> Optional[str]:
    """Try PyPDF2 or pypdf."""
    try:
        import PyPDF2
    except Exception:
        try:
            import pypdf as PyPDF2  # newer package name
        except Exception:
            return None
    try:
        chunks = []
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                try:
                    chunks.append(page.extract_text() or "")
                except Exception:
                    chunks.append("")
        return "\n".join(chunks)
    except Exception:
        return None

def extract_text(path: Path) -> str:
    """Try multiple backends and return the first successful text string."""
    for fn in (extract_text_pymupdf, extract_text_pdfminer, extract_text_pypdf):
        txt = fn(path)
        if txt:
            return txt
    return ""

# -------- Keywords field parser --------
# Common boundary markers that usually appear right after the keywords line
STOP_MARKERS = [
    r"\n\s*\n",                # blank line
    r"\n?Citation:",
    r"\n?Received",
    r"\n?Abstract",
    r"\n?1\.\s*Introduction",
    r"\n?Academic Editor",
    r"\n?Editor",
    r"\n?Publisher",
    r"\n?Copyright",
    r"\n?Funding",
    r"\n?Conflicts of Interest",
    r"\n?Data Availability",
]
STOP_RE = re.compile("|".join(STOP_MARKERS), re.IGNORECASE | re.DOTALL)

def extract_keywords_field(text: str) -> str:
    """
    Find 'Keywords:' and capture the list until a boundary marker or EOF.
    Returns an empty string if not found.
    """
    # Locate the 'Keywords:' anchor (allow flexible spaces)
    m = re.search(r"(?i)\bkeywords?\s*:\s*", text)
    if not m:
        return ""

    start = m.end()
    tail = text[start:]

    # Cut at the first stop marker
    stop = STOP_RE.search(tail)
    if stop:
        tail = tail[:stop.start()]

    # Safety cap to avoid runaway captures
    tail = tail[:MAX_CAPTURE_CHARS]

    # Normalize whitespace and separators
    tail = re.sub(r"[ \t]+", " ", tail)
    tail = tail.strip(" \n-—–:;,.")
    tail = re.sub(r"\s*;\s*", "; ", tail)
    tail = re.sub(r"\s*,\s*", ", ", tail)

    # Drop a trailing period
    tail = tail.rstrip(".")
    return tail.strip()

# -------- Main --------
def main(pdf_dir: Path = PDF_DIR, out_csv: str = OUT_CSV) -> None:
    pdfs = sorted([p for p in Path(pdf_dir).iterdir() if p.suffix.lower() == ".pdf"])
    rows = []
    for pdf in pdfs:
        txt = extract_text(pdf)
        keywords = extract_keywords_field(txt)
        rows.append([pdf.name, keywords])

    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["file", "keywords"])
        w.writerows(rows)

    print(f"Saved: {out_csv} (files: {len(pdfs)})")

if __name__ == "__main__":
    main()
