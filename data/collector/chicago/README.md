# Chicago Municipal Code Data Collector

This collector downloads the Municipal Code of Chicago from the amlegal.com code library.

## Source

**Website:** https://codelibrary.amlegal.com/codes/chicago/latest/overview

## What It Does

The collector:
1. Navigates to the Chicago code library overview page
2. Clicks the download button
3. Selects the "Municipal Code of Chicago" checkbox in the modal
4. Clicks the "Download" button to proceed
5. Selects "Save PDF" from the format selection modal
6. Waits for the server to prepare the file (5-10 minutes)
7. Clicks the "OPEN" button to download the prepared file
8. Downloads the complete municipal code PDF (~30MB)

## Usage

### Basic Usage

```bash
# Run from the data directory
uv run python -m collector.chicago.run
```

### Options

```bash
# Run with browser visible (non-headless)
uv run python -m collector.chicago.run --headless=false

# Specify custom download directory
uv run python -m collector.chicago.run --download-dir=/path/to/directory
```

## Output

Downloaded files are saved to `collector/chicago/collected_data_chicago/` by default.

## Technical Details

- **Framework:** Selenium WebDriver with Chrome
- **Download format:** PDF
- **File size:** ~30MB
- **Runtime:** ~7-10 minutes (includes server-side file preparation time)
- **Headless mode:** Fully supported
- **Reliability:** Multi-step workflow with modal interactions and file preparation wait

## Architecture

The collector extends `BaseCollector` and implements:
- Selenium-based web automation
- Modal interaction and checkbox selection
- Download completion detection
- File validation

## Files

- `base.py`: Core collector implementation
- `run.py`: CLI entry point
- `__init__.py`: Module exports
- `collected_data_chicago/`: Downloaded files directory
