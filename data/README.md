# Data Collector/Parser

This directory contains the code for collecting and parsing data from various sources.

There are main two directories:

- `collector`: contains the code for collecting data from various sources.
- `parser`: contains the code for parsing data from various sources.

The `collector` directory contains the code for collecting data from various sources.
The `parser` directory contains the code for parsing data from various sources.

## Collector

We will collect data from various sources. Each source has its own collector. Currently, we have the following collectors:

- `census`: collects census data from the US Census Bureau.
- `development_plans`: collects development plans from various sources.
- `zba`: collects zoning board approval data from various sources.
- `image`: collects images from various sources. (TBD)
- `reports`: collects reports from various sources.
- `paper`: collects journal articles from various sources.

## Parser

Except for census data, all other data needs to be parsed as they are mostly pdfs or csvs.

Currently, we have the following parsers:

- `development_plans`: parses development plans from various sources.


## Tests

We have a test suite for the collector and parser. The test suite is located in the `tests` directory.
