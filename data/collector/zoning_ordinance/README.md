# Zoning Ordinance Data Collectors

This directory contains automated web scrapers for collecting zoning ordinance data from multiple cities.

## Available Cities

### Boston
- **Source:** https://library.municode.com/ma/boston/codes/redevelopment_authority
- **Format:** Excel (.xlsx) files for each zoning article
- **File Count:** ~140 articles
- **Runtime:** ~3-4 minutes
- **Collector:** `boston.py` → `BostonCollector`

### Chicago
- **Source:** https://codelibrary.amlegal.com/codes/chicago/latest/overview
- **Format:** Single PDF file (~30MB)
- **Runtime:** ~7-10 minutes (includes server file preparation)
- **Collector:** `chicago.py` → `ChicagoZoningCollector`

## Usage

### Basic Usage

From the `/data` directory:

```bash
# Collect Boston zoning data
python collector/zoning_ordinance/run.py --city boston --headless True

# Collect Chicago zoning data
python collector/zoning_ordinance/run.py --city chicago --headless True
```

### Options

- `--city`: Which city to collect data for (required: `boston` or `chicago`)
- `--headless`: Run browser in headless mode (default: `True`)
- `--download_dir`: Custom download directory (optional)

### Examples

```bash
# Run with visible browser window
python collector/zoning_ordinance/run.py --city boston --headless False

# Run with custom download directory
python collector/zoning_ordinance/run.py --city chicago --download_dir /path/to/output

# Interactive mode (will prompt for options)
python collector/zoning_ordinance/run.py
```

## Output

Downloaded files are saved to:
- Boston: `collector/zoning_ordinance/boston_collected_data/`
- Chicago: `collector/zoning_ordinance/chicago_collected_data/`

## Technical Details

Both collectors:
- Extend `BaseCollector` abstract class
- Use Selenium WebDriver with Chrome
- Support both headless and visible browser modes
- Include download completion detection
- Validate downloaded files

### Boston Collector

- Downloads individual Excel files for each zoning article
- Excludes certain sections (maps, comparative tables, etc.)
- Handles Angular-based dynamic content rendering
- Optimized for performance (O(n) complexity)

### Chicago Collector

- Multi-step modal interaction workflow
- Waits for server-side PDF generation
- Handles format selection (PDF/Word/etc.)
- Clicks "OPEN" button after file preparation

## Files

- `base.py`: Base class for zoning ordinance collectors (re-exports BaseCollector)
- `boston.py`: Boston zoning code collector implementation
- `chicago.py`: Chicago municipal code collector implementation
- `run.py`: CLI entry point for running either collector
- `__init__.py`: Module exports
- `README.md`: This file
- `boston_collected_data/`: Downloaded Boston files
- `chicago_collected_data/`: Downloaded Chicago files

## Requirements

- Python 3.9+
- Chrome/Chromium browser
- Selenium 4.6+
- See `/data/pyproject.toml` for full dependencies

## Troubleshooting

### ChromeDriver Issues

If you encounter ChromeDriver errors:
1. Ensure Chrome/Chromium browser is installed
2. Selenium 4.6+ includes automatic driver management

### Download Failures

If downloads fail:
1. Check internet connection
2. Verify source websites are accessible
3. Try running with `--headless False` to see what's happening
4. Check logs for specific error messages

### Boston-Specific Issues

- The website uses Angular for dynamic content
- Wait times are included for rendering
- If sections aren't detected, try increasing timeout values

### Chicago-Specific Issues

- Server file preparation can take 5-10 minutes
- The download involves multiple modals and steps
- If download hangs, check if the "OPEN" button appeared

## Adding New Cities

To add a new city collector:

1. Create `{city}.py` with a collector class extending `BaseCollector`
2. Implement `collect()` and `validate()` methods
3. Update `__init__.py` to export the new collector
4. Update `run.py` to handle the new city option
5. Update this README with the new city details
