# Database Setup

Initializes the database and populates the `cities` table by scraping city data from [Zoneomics](https://www.zoneomics.com).

## What It Does

1. Creates the database if it doesn't exist
2. Enables PostGIS extension
3. Creates the `cities` table
4. Scrapes cities from Zoneomics (all 50 US states) and populates the table

## Usage

### Docker Compose (Selenium)

```bash
# Create tables only (default)
docker compose run --rm collector -c "source .venv/bin/activate && python setup/run.py"

# Populate cities from Zoneomics (all 50 states)
docker compose run --rm collector -c "source .venv/bin/activate && python setup/run.py --populate"

# Test mode - populate only Alabama
docker compose run --rm collector -c "source .venv/bin/activate && python setup/run.py --populate --test-mode"
```

### Docker Compose (Playwright)

If Selenium fails due to bot detection, use the Playwright image:

```bash
docker compose run --rm collector-playwright -c "source /home/pwuser/.venv/bin/activate && python setup/run.py --populate --test-mode"
```

## Command Line Arguments

| Argument | Description |
|----------|-------------|
| `--populate` | Scrape cities from Zoneomics and populate the table |
| `--test-mode` | Only process the first state (Alabama) for testing |

## Database Schema

### cities table

```sql
CREATE TABLE cities (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,     -- unique slug (e.g., "boston", "springfield-ma")
    display_name VARCHAR(100) NOT NULL,    -- display name (e.g., "Boston", "Springfield")
    state VARCHAR(100),                    -- state/region name (e.g., "Massachusetts", "Illinois")
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**City naming strategy:**
- By default, cities use simple slugs: `"boston"`, `"cambridge"`, `"new-york"`
- When there's a name conflict (same city name in different states), a state suffix is added:
  - First `Springfield` (e.g., Illinois) → `"springfield"`
  - Second `Springfield` (e.g., Massachusetts) → `"springfield-ma"`

## Browser Fallback

The setup tries browsers in this order:
1. **Selenium** (default, available in the base collector image)
2. **Playwright** (fallback, available in the playwright image)

If neither is available, setup will complete but cities won't be populated.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `APP_DB_NAME` | PostgreSQL database name |
| `POSTGRE_HOST` | PostgreSQL host |
| `POSTGRE_PORT` | PostgreSQL port (default: 5432) |
| `POSTGRE_USER` | PostgreSQL username |
| `POSTGRE_PASSWORD` | PostgreSQL password |

## Notes

- Cities are inserted with `ON CONFLICT DO NOTHING`, so existing cities are preserved
- The scraper is polite to Zoneomics (1 second delay between states)
- Full collection of all 50 states takes approximately 5-10 minutes
