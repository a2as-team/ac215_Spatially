# Reports Collector (Modular)

This module provides a small, extensible framework for collecting research report PDFs and storing them with consistent, human-readable names and folders. It includes a concrete integration for **Lee & Associates**.

## Quickstart

```bash
# Install minimal deps
pip install requests beautifulsoup4

# Preview only (no downloads)
python -m data.collector.reports.run --limit 20 --dry-run

# Download a small sample
python -m data.collector.reports.run --limit 40
```

Downloaded files are saved to:
```
data/collector/reports/downloads/<report_type>/<location>/<year>/<standardized-filename>.pdf
```

Example:
```
data/collector/reports/downloads/
  industrial/
    united-states/ga/atlanta/2024/2024-q4-united-states-ga-atlanta-industrial.pdf
  north-america-market-report/
    north-america/2024/2024-q2-north-america-north-america-market-report.pdf
```

> Tip: add `data/collector/reports/downloads/` to `.gitignore` to avoid committing large binaries.

## Architecture

- **`BaseReportCollector`** (`data/collector/reports/base.py`)
  - Unified `ReportItem` dataclass
  - `fetch_select_options()` — derive **Report Type / Location / Year** from discoverable PDFs
  - `iter_reports(limit=None)` — iterate normalized items
  - `download_all(dest_root, ...)` — store in a standard layout and filenames
- **`LeeAndAssociatesCollector`** (`data/collector/reports/lee_and_associates.py`)
  - Paginates `/research/`, discovers direct PDF links, parses year/quarter/type/location from filenames, with fallbacks
- **CLI** (`data/collector/reports/run.py`)
  - `--dry-run` to preview, `--limit` to keep runs small

