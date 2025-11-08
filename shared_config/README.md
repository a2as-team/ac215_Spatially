# Shared Configuration

This directory contains configuration shared across all services (collector, processor, workflow, etc.).

## Structure

```
shared_config/
├── __init__.py
├── cities.json      # City data (edit this to add new cities)
├── cities.py        # Python interface to city data
└── README.md        # This file
```

## Adding a New City

Simply edit `cities.json`:

```json
{
  "BOSTON": {
    "display_name": "Boston",
    "state": "MA"
  },
  "NEW_CITY": {
    "display_name": "New City Name",
    "state": "XX"
  }
}
```

**Note:** `state` field is optional for international cities.

## Usage in Code

From any service (collector, processor, workflow):

```python
from shared_config.cities import City

# Use constants (IDE autocomplete works!)
city = City.BOSTON  # "BOSTON"

# Get display name
display = City.get_display_name(City.BOSTON)  # "Boston"

# Get state (returns None if not available)
state = City.get_state(City.BOSTON)  # "MA"

# Validate city
if City.is_valid("BOSTON"):
    print("Valid city!")

# Get all cities
all_cities = City.get_all()  # ["BOSTON", "CHICAGO", ...]

# Get full metadata
metadata = City.get_metadata(City.BOSTON)
# {"display_name": "Boston", "state": "MA"}
```

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

## Available Cities

Current registered cities:
- BOSTON (Massachusetts)
- CHICAGO (Illinois)
- NEW_YORK (New York)
- LOS_ANGELES (California)
- SAN_FRANCISCO (California)
