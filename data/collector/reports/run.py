
import os
import argparse
from lee_and_associates import LeeAndAssociatesCollector

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lee & Associates report downloader")
    parser.add_argument("--dest", default=os.path.join(os.path.dirname(__file__), "downloads"), help="destination root folder")
    parser.add_argument("--limit", type=int, default=40, help="limit number of reports to scan (for quick tests)")
    parser.add_argument("--dry-run", action="store_true", help="don't download, just list what would be saved")
    args = parser.parse_args()

    collector = LeeAndAssociatesCollector()
    options = collector.fetch_select_options()
    print("Discovered options:")
    for k, v in options.items():
        print(f"  {k}: {len(v)} items")

    print("\nListing reports...")
    for i, item in enumerate(collector.iter_reports(limit=args.limit), start=1):
        print(f"{i:3d}. {item.year} {item.quarter or ''} | {item.location} | {item.report_type} | {item.url}")

    if not args.dry_run:
        os.makedirs(args.dest, exist_ok=True)
        saved = collector.download_all(args.dest, dry_run=False)
        print(f"\nSaved {len(saved)} files into {args.dest}")
    else:
        print("\nDry run complete.")
