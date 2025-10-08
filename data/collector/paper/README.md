# Paper Collector

This data collector is responsible for collecting academic journal articles related to urban planning and real estate. It uses Selenium to navigate journal pages, collect article links, and save PDF files either by search keyword or as a full journal dump.

## Resources

### 1. MDPI LAND

- URL: https://www.mdpi.com/search?q=&journal=land&sort=pubdate&page_count=50
  This is a public journal that publishes articles related to urban planning and real estate.

## File Structure

```
collector/
│
├── paper/
│   ├── __init__.py              # Facade class (PaperCollector) that dispatches to providers like MDPI
│   ├── base.py  # Abstract class implementing shared paper download logic
│   ├── mdpi.py                  # Concrete implementation for MDPI journals
│   └── run.py                   # CLI entry point
```

## Class Structure

`BasePaperCollector` (`base.py`)

- An abstract base class that defines shared functionality for all paper collectors.
- Handles:
  - Browser session setup (via Selenium)
  - Download management
  - Waiting for page loads and file downloads
- Provides a unified collect(query, max_pages) interface.
- Designed to be subclassed by specific collectors (e.g., MDPI, Elsevier) that implement how to:
  - Build search URLs
  - Find article links
  - Locate PDF download buttons

`MDPICollector` (`mdpi.py`)

- A concrete subclass of BasePaperCollector that implements logic specific to MDPI journals.
- Uses flexible CSS selectors to handle layout changes and supports both keyword-based and full-journal downloads.

`PaperCollector` (`init.py`)

- A facade (dispatcher) that provides a single interface for multiple paper sources.
- Currently supports MDPI but can be extended to other publishers.
- Internally maintains a registry of collector classes:

```
registry = {
    "mdpi": MDPICollector,
}
```

- Users call:

```
PaperCollector().collect(provider="mdpi", journal="land", query="crime", pages=3)
```

and the appropriate subclass (e.g. `MDPICollector`) handels the work.

## How to run

### 1. Using the CLI

Run the paper collector directly from the command line:

```
python data/collector/paper/run.py --query crime --pages 3 --journal land --provider mdpi
```

### 2. Interactive Mode

If you run without any arguments:

```
python data/collector/paper/run.py
```

You’ll be prompted for missing parameters (powered by `SmartArgParser`):

```
Search keyword (type 'none' for latest papers): crime
Number of pages to scrape: 3
MDPI journal slug (e.g., land, sensors, electronics): land
Paper provider (default: mdpi): mdpi
```

## Output

Downloaded PDFs are saved under:

```
downloads/<provider>/<journal>/<query>/
```

## Extending

To add another provider (e.g., Springer):

1. Create a subclass of `BasePaperCollector`.
2. Implement its `collect()` and scraping logic.
3. Register it in `collector/paper/__init__.py`:

```
self.registry["springer"] = SpringerCollector
```
