# AC215 Spatially Project

This is a project that will leverage LLM to create a spatially intelligent agent that can help real estate decisions.

## Database Schema

```mermaid
erDiagram
    cities ||--o{ census_tracts : "has many"
    cities ||--o{ zoning_maps : "has many"
    census_tracts ||--|| census_data : "has one"

    cities {
        int id PK
        varchar name "Unique city identifier"
        varchar display_name "Human-readable name"
        varchar state "State code"
        timestamp created_at
        timestamp updated_at
    }

    census_tracts {
        int id PK
        int city_id FK "References cities(id)"
        varchar geoid "Geo identifier"
        geometry geom "PostGIS geometry"
        timestamp created_at
    }

    census_data {
        int id PK
        int census_tract_id FK "References census_tracts(id)"
        TBD TBD 
    }

    zoning_maps {
        int id PK
        int city_id FK "References cities(id)"
        varchar code "Zoning code (e.g. RS1)"
        timestamp created_at
    }
```

> **Note:** The `census_data` table schema is a placeholder. Please define the appropriate fields based on the census data requirements (e.g., demographics, housing statistics, economic indicators, etc.).

### Quick Start

```bash
docker compose -f docker-compose.yml up
```

If you only want to run the collector, you can run the following command
```bash
docker compose -f docker-compose.yml run --rm collector
```

If you only want to run the label studio, you can run the following command
```bash
docker compose -f docker-compose.yml run --rm label-studio
```

## References
1. NYC Zoning Webmap: https://zola.planning.nyc.gov/l/zoning-district/C5-P?search=false
2. ReZone (Keep in track of zoning changes): https://www.re-zone.ai/
3. TryMappr (Interactive zoning map): https://trymappr.com/

