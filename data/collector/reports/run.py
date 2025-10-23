from __future__ import annotations

import os
import sys
from typing import Optional
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Try to use SmartArg style like census; fallback to argparse if not available.
try:
    from utils.smart_arg_parser import SmartArgItem, SmartArgParser  # type: ignore

    _SMART = True
except Exception:
    import argparse

    _SMART = False

from reports import ReportsCollector

DEFAULT_DESTS = {
    "lee_and_associates": os.path.join(
        os.path.dirname(__file__), "lee_and_associates", "downloads"
    ),
}


def main_smart():
    schema = {
        "source": SmartArgItem(
            flags=["--source"], prompt="Report source id", arg_type=str, required=True
        ),
        "action": SmartArgItem(
            flags=["--action"],
            prompt="Action: options|list|download",
            arg_type=str,
            required=True,
        ),
        "report_type": SmartArgItem(
            flags=["--report-type"],
            prompt="Report type (optional)",
            arg_type=str,
            required=False,
        ),
        "location": SmartArgItem(
            flags=["--location"],
            prompt="Location (optional)",
            arg_type=str,
            required=False,
        ),
        "year": SmartArgItem(
            flags=["--year"], prompt="Year (optional)", arg_type=str, required=False
        ),
        "dest": SmartArgItem(
            flags=["--dest"],
            prompt="Destination root for downloads",
            arg_type=str,
            required=False,
        ),
        "limit": SmartArgItem(
            flags=["--limit"],
            prompt="Limit discovered items",
            arg_type=int,
            required=False,
        ),
        "dry_run": SmartArgItem(
            flags=["--dry-run"],
            prompt="Dry run (no downloads)",
            arg_type=bool,
            required=False,
        ),
    }
    parser = SmartArgParser(schema)
    args = parser.parse()
    return run(args)


def main_argparse():
    ap = argparse.ArgumentParser(description="Reports collector CLI")
    ap.add_argument(
        "--source", required=True, help="Report source id (e.g., lee_and_associates)"
    )
    ap.add_argument(
        "--action",
        required=True,
        choices=["options", "list", "download"],
        help="Action to run",
    )
    ap.add_argument("--report-type")
    ap.add_argument("--location")
    ap.add_argument("--year")
    ap.add_argument("--dest")
    ap.add_argument(
        "--limit", type=int, help="Limit discovered items (speeds up options/list)"
    )
    ap.add_argument("--dry-run", action="store_true")
    args = vars(ap.parse_args())
    return run(args)


def run(args):
    source = args["source"]
    action = args["action"].lower()
    report_type = args.get("report_type") or None
    location = args.get("location") or None
    year = args.get("year") or None
    if year and str(year).isdigit():
        year = int(year)
    dest = (
        args.get("dest")
        or DEFAULT_DESTS.get(source)
        or os.path.join(os.path.dirname(__file__), "downloads")
    )
    limit = args.get("limit")
    dry_run = bool(args.get("dry_run"))

    collector = ReportsCollector()
    if source not in collector.caller_map:
        raise ValueError(
            f"Invalid source: {source}. Available: {list(collector.caller_map.keys())}"
        )

    if action == "options":
        print(f"Discovering options (limit={limit or 'all'})...")
        opts = collector.options(source, limit=limit)
        print("Options:")
        for k, v in opts.items():
            print(f"  {k}: {len(v)} items")
            for s in v[:10]:
                print(f"    - {s}")
    elif action == "list":
        print(f"Listing URLs (limit={limit or 'all'})...")
        urls = collector.list_urls(
            source, report_type=report_type, location=location, year=year, limit=limit
        )
        print(f"Found {len(urls)} URLs:")
        for u in urls[:50]:
            print(" -", u)
        if len(urls) > 50:
            print(f"... (+{len(urls)-50} more)")
    elif action == "download":
        print("Downloading...")
        saved = collector.caller_map[source].download_for_options(
            report_type=report_type,
            location=location,
            year=year,
            dest_root=dest,
            dry_run=dry_run,
            limit=limit,
        )
        print(f"Saved {len(saved)} files under: {dest}")
    else:
        raise ValueError("action must be one of: options|list|download")


if __name__ == "__main__":
    if _SMART:
        main_smart()
    else:
        main_argparse()
