import os
import sys
from pathlib import Path
from mdpi_land import MDPICollector

if __name__ == "__main__":
    # Example CLI-ish usage:
    #   python run.py           -> dump latest from page 1
    #   python run.py crime 3   -> search 'crime' across 3 pages
    query = None
    pages = 1
    if len(sys.argv) >= 2:
        query = sys.argv[1] if sys.argv[1].lower() != "none" else None
    if len(sys.argv) >= 3:
        pages = int(sys.argv[2])

    collector = MDPICollector(
        journal="land",
        out_dir="downloads/mdpi",
        headless=False,            # try non-headless first if you’ve seen 403s
        per_page_timeout_s=25,
        polite_sleep_s=1.2,
        download_wait_s=90,
    )

    if query:
        files = collector.download_by_keyword(query=query, max_pages=pages)
    else:
        files = collector.download_all_dump(max_pages=pages)

    print(f"Downloaded {len(files)} files:")
    for f in files:
        print(" -", f)
