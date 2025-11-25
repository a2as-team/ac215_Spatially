# AC215 Spatially Project

This is a project that will leverage LLM to create a spatially intelligent agent that can help real estate decisions.

## Database Schema

```mermaid
%% Enum: topic
%% Values:
%% - DEMOGRAPHICS
%% - HOUSEHOLD_COMPOSITION
%% - HOUSING_STOCK
%% - HOUSING_FINANCIALS
%% - HOUSING_TENURE_OCCUPANCY
%% - HOUSING_COST_BURDEN
%% - HOUSING_AGE_CONDITION
%% - VACANCY
%% - INCOME
%% - POVERTY
%% - EMPLOYMENT
%% - INDUSTRY
%% - TRANSPORTATION
%% - GEOGRAPHIC_MOBILITY
%% - EDUCATION

erDiagram
    cities ||--o{ zoning_maps : "has many"
    cities ||--o{ zoning_ordinance_embed : "has many"
    CENSUS_TRACT ||--o{ ACS_VALUE : "has measurements"
    ACS_TABLE ||--o{ ACS_VARIABLE : "defines variables"
    ACS_VARIABLE ||--o{ ACS_VALUE : "provides variable metadata"

    cities {
        int id PK
        varchar name "Unique city identifier"
        varchar display_name "Human-readable name"
        varchar state "State code"
        timestamp created_at
        timestamp updated_at
    }

    CENSUS_TRACT {
        varchar geoid PK "Geo identifier"
        geometry geom "PostGIS geometry"
        timestamp created_at
    }

    ACS_TABLE {
        string acs_table_id PK
        string title
        topic topic
        string description
    }

    ACS_VARIABLE {
        string variable_id PK
        string acs_table_id FK
        string name
        string concept
    }

    ACS_VALUE {
        int acs_value_id PK
        string geoid FK
        string variable_id FK
        int year
        float value
    }

    zoning_maps {
        int id PK
        int city_id FK "References cities(id)"
        varchar code "Zoning code (e.g. RS1)"
        varchar article "Zoning article"
        varchar usage "Zoning usage"
        geometry geom "PostGIS geometry"
        timestamp created_at
    }

    zoning_ordinance_embed {
        int id PK
        int city_id FK "References cities(id)"
        text chunk_hash "SHA256 hash for deduplication (unique)"
        text text_chunk "Zoning ordinance text chunk"
        varchar document_title "Title of the zoning ordinance"
        varchar document_subtitle "Subtitle of the zoning ordinance"
        text[] zoning_codes "Zoning codes mentioned in text"
        vector(768) embedding "Vector(768) for semantic search"
        jsonb metadata "Flexible metadata (source_url, tokens, etc.)"
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
