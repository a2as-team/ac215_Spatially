# Reports Collector (Modular) — Lee & Associates

A small, extensible framework to collect report PDFs with consistent names.
This module includes a concrete collector for **Lee & Associates** reports.

## Install
    pip install requests beautifulsoup4

> Python 3.8+ supported. This module uses typing.List/Union for 3.8 compatibility.

## CLI (run from repo root)
The CLI mirrors the census SmartArg style. If utils.smart_arg_parser is missing, it falls back to argparse.

1) Discover options (report types / locations / years)
    python -m data.collector.reports.run --source lee_and_associates --action options --limit 20

2) List URLs (no download)
    python -m data.collector.reports.run --source lee_and_associates --action list --limit 20
    python -m data.collector.reports.run --source lee_and_associates --action list --report-type Industrial --location "United States/GA/Atlanta" --year 2024 --limit 50

3) Download a filtered subset
    python -m data.collector.reports.run --source lee_and_associates --action download --report-type Industrial --location "United States/GA/Atlanta" --year 2024 --limit 50
    # dry run first
    python -m data.collector.reports.run --source lee_and_associates --action download --dry-run --limit 10

## Output layout (per review)
Files are saved under the source-specific folder:
    data/collector/reports/lee_and_associates/downloads/<report_type>/<location>/<year>/<standardized-filename>.pdf

Add to .gitignore:
    data/collector/reports/lee_and_associates/downloads/

## Public API
- Base (BaseReportCollector)
  - get_downloadable_file_urls(limit=None) -> List[str]
  - download_urls(urls, dest_dir, filename_fn=None, dry_run=False)
  - get_select_options(limit=None)  (optional)
- Lee & Associates (LeeAndAssociatesCollector)
  - get_select_options(limit=None) -> dict
  - list_urls_for(report_type=None, location=None, year=None, limit=None) -> List[str]
  - download_for_options(report_type, location, year, dest_root, dry_run=False, limit=None) -> List[str]

## Dev workflow (short)
1. Create a feature branch (e.g., feat/lee-and-associates-collector)
2. Commit small changes; open a PR
3. Use Issues to track review items and TODOs
4. Keep downloads out of git (.gitignore above)

## Troubleshooting
- Slow/no output: add --limit 10/20 and try --dry-run
- Python 3.8 typing errors: ensure you’re on this module version
