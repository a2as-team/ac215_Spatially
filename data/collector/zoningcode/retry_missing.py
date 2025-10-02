import os
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from collector.zoningcode import ZoningCodeCollector

# Missing sections based on verification
MISSING_SECTIONS = [
    "ARTICLE 9 - NONCONFORMING USES",
    "ARTICLE 23 - OFF-STREET PARKING",
    "ARTICLE 25A - COASTAL FLOOD RESILIENCE OVERLAY DISTRICT",
    "ARTICLE 32 - GROUNDWATER CONSERVATION OVERLAY DISTRICT",
    "ARTICLE 39 - NORTH STATION ECONOMIC DEVELOPMENT AREA",
    "ARTICLE 40 - SOUTH STATION ECONOMIC DEVELOPMENT AREA",
    "ARTICLE 41 - HUNTINGTON AVENUE/PRUDENTIAL CENTER DISTRICT",
    "ARTICLE 42B - HARBORPARK DISTRICT - CHARLESTOWN WATERFRONT",
    "ARTICLE 42E - HARBORPARK DISTRICT - FORT POINT WATERFRONT",
    "ARTICLE 42F - HARBORPARK DISTRICT - CHARLESTOWN NAVY YARD",
    "ARTICLE 51 - ALLSTON-BRIGHTON NEIGHBORHOOD DISTRICT",
    "ARTICLE 60. - GREATER MATTAPAN NEIGHBORHOOD DISTRICT",
    "ARTICLE 70 - BETH ISRAEL DEACONESS MEDICAL CENTER INSTITUTIONAL DISTRICT EAST",
    "ARTICLE 71 - MASSACHUSETTS COLLEGE OF PHARMACY INSTITUTIONAL DISTRICT",
    "ARTICLE 72 - NEW ENGLAND DEACONESS HOSPITAL INSTITUTIONAL DISTRICT",
    "ARTICLE 73 - DANA-FARBER CANCER INSTITUTE INSTITUTIONAL DISTRICT",
]

if __name__ == "__main__":
    download_dir = os.path.join(os.path.dirname(__file__), "collected_data")

    collector = ZoningCodeCollector(headless=False, download_dir=download_dir)

    print("\n" + "=" * 80)
    print("Retrying Missing Sections")
    print("=" * 80)
    print(f"Sections to retry: {len(MISSING_SECTIONS)}")
    print("=" * 80 + "\n")

    # Run the full collection - it will process all but retry logic will help
    results = collector.collect()

    print("\n" + "=" * 80)
    print("Retry Results")
    print("=" * 80)
    print(f"Downloaded: {results['downloaded']}")
    print(f"Failed: {results['failed']}")
    if results['failed_sections']:
        print("\nStill missing:")
        for section in results['failed_sections']:
            if section in MISSING_SECTIONS:
                print(f"  - {section}")
    print("=" * 80 + "\n")
