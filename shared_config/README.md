# Shared Configuration

This directory contains configuration shared across all services (collector, processor, workflow, etc.).

## Architecture

The **database `cities` table** is the single source of truth for city data. Cities are:
1. **Discovered dynamically** by collectors (e.g., `zoning_codes` collector scrapes cities from Zoneomics)
2. **Inserted into the database** as they are discovered
3. **Queried via `CityService`** by other services that need city data

This approach eliminates the need for manual city configuration and ensures all services have access to the same, up-to-date city data.

## Structure

```
shared_config/
├── __init__.py
├── city_service.py  # Database-backed city service
└── README.md        # This file
```

## Usage

Use `CityService` to query cities from the database:

```python
from shared_config.city_service import CityService

# Use as context manager (auto-closes connection)
with CityService() as service:
    # Get all cities
    cities = service.get_all_cities()
    # [{"id": 1, "name": "boston", "display_name": "Boston", "state": "MA"}, ...]

    # Get cities by state
    ma_cities = service.get_cities_by_state("Massachusetts")

    # Get a specific city by slug name
    city = service.get_city("boston")

    # Get a city by database ID
    city = service.get_city_by_id(123)

    # Check if city exists
    if service.city_exists("boston"):
        print("Boston exists!")

    # Search cities
    results = service.search_cities("new", limit=10)

    # Get all states
    states = service.get_states()  # ["Alabama", "Massachusetts", ...]

    # Get city count
    count = service.get_city_count()
```

## Database Schema

The `cities` table is created by `init_db.py`:

```sql
CREATE TABLE cities (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,     -- slug name (e.g., "boston")
    display_name VARCHAR(100) NOT NULL,    -- display name (e.g., "Boston")
    state VARCHAR(2),                      -- state abbreviation (e.g., "MA")
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Cities are populated by collectors that discover them from external data sources.

## Environment Variables

`CityService` requires the following environment variables:

| Variable | Description |
|----------|-------------|
| `APP_DB_NAME` | PostgreSQL database name |
| `POSTGRE_HOST` | PostgreSQL host |
| `POSTGRE_PORT` | PostgreSQL port (default: 5432) |
| `POSTGRE_USER` | PostgreSQL username |
| `POSTGRE_PASSWORD` | PostgreSQL password |

## Docker Configuration

The `shared_config/` directory is mounted as read-only in all service containers:

```yaml
volumes:
  - ./shared_config:/app/shared_config:ro
```

And PYTHONPATH is set to include the root:

```yaml
environment:
  PYTHONPATH: /app:/
```

This allows all services to import from `shared_config` without conflicts.

## Local Development

When running tests locally, add the project root to PYTHONPATH:

```bash
PYTHONPATH=/path/to/ac215_Spatially:/path/to/ac215_Spatially/data/collector \
uv run python -m unittest tests.test_module
```
