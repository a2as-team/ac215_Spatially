# Boston Zoning Code Data Collector

This data collector automates the download of Boston zoning code documents from the Municode Library using Selenium web automation.

## Overview

The collector downloads individual Excel (.xlsx) files for each zoning article from Boston's Redevelopment Authority code, excluding certain sections like maps and comparative tables.

## Requirements

- Python 3.13+
- Chrome/Chromium browser installed
- ChromeDriver (automatically managed by Selenium 4.6+)

## Installation

From the `/data` directory:

```bash
# Install dependencies
uv sync
# or
pip install -e .
```

## Usage

### Basic Usage

From the `/data` directory:

```bash
python collector/zoningcode/run.py --headless True
```

### Options

- `--headless`: Run browser in headless mode (default: True)
  - Set to `False` to see the browser window during execution
- `--download_dir`: Custom download directory (default: `collected_data/`)

### Examples

```bash
# Run with visible browser window
python collector/zoningcode/run.py --headless False

# Run with custom download directory
python collector/zoningcode/run.py --headless True --download_dir /path/to/output

# Interactive mode (will prompt for options)
python collector/zoningcode/run.py
```

## What Gets Downloaded

The collector downloads Excel files for all zoning articles **except**:

1. PROOF ONLY ZONING CODE CITY OF BOSTON, MASSACHUSETTS
2. SUPPLEMENT HISTORY TABLE
3. All Zoning Maps
4. CODE COMPARATIVE TABLE (both versions)

Each downloaded file is named according to its section (e.g., `ARTICLE_1_-_TITLE_PURPOSE_AND_SCOPE.xlsx`).

## Output

Downloaded files are saved to `collected_data/` directory by default. Each file contains the structured content of that zoning article in Excel format.

## Resources

- **Source URL**: https://library.municode.com/ma/boston/codes/redevelopment_authority
- **Publisher**: Municode Library
- **Content**: Boston Redevelopment Authority Zoning Code

## Troubleshooting

### ChromeDriver Issues

If you encounter ChromeDriver errors, ensure:
1. Chrome/Chromium browser is installed
2. Selenium version is 4.6+ (includes automatic driver management)

### Download Failures

If downloads fail:
1. Check internet connection
2. Verify the Municode website is accessible
3. Try running with `--headless False` to see what's happening
4. Check logs for specific error messages

### Angular Rendering Issues

The website uses Angular for dynamic content. If sections aren't being detected:
- The collector includes wait times for Angular to render
- Try increasing timeout values in `base.py` if needed
