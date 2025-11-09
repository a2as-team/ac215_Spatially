# City Registry

This directory contains the centralized city registry for all collectors.

## Adding a New City

To add a new city, simply edit `cities.json`:

```json
{
  "BOSTON": {
    "display_name": "Boston",
    "state": "MA"
  },
  "NEW_YORK": {
    "display_name": "New York",
    "state": "NY"
  },
  "LONDON": {
    "display_name": "London"
  }
}
```

**Note:** Not all fields are required. Cities outside the US may not have a `state` field.

## Usage in Code

```python
from config.cities import City

# Use the generated constants
city_key = City.BOSTON  # "BOSTON"

# Get display name
display = City.get_display_name(City.BOSTON)  # "Boston"

# Get state (returns None if not available)
state = City.get_state(City.BOSTON)  # "MA"

# Validate city
if City.is_valid("BOSTON"):
    print("Valid city!")

# Get all cities
all_cities = City.get_all()  # ["BOSTON", "CHICAGO"]

# Get full metadata
metadata = City.get_metadata(City.BOSTON)
# {"display_name": "Boston", "state": "MA"}
```

## Available Fields

Current supported fields in `cities.json`:

- `display_name` (required): Human-readable name for the city
- `state` (optional): State/province code (mainly for US cities)

## Adding More Metadata

You can add any additional fields to the city objects in `cities.json`:

```json
{
  "BOSTON": {
    "display_name": "Boston",
    "state": "MA",
    "country": "USA",
    "timezone": "America/New_York"
  }
}
```

Access via `City.get_metadata("BOSTON")` or add specific helper methods like `City.get_state()`.
