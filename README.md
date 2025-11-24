# AC215 Spatially Project

This is a project that will leverage LLM to create a spatially intelligent agent that can help real estate decisions.

## Database Schema

```mermaid
erDiagram
    cities ||--o{ zoning_maps : "has many"
    census_tracts ||--|| census_data : "has one"
    cities ||--o{ zoning_ordinance_embed : "has many"
    cities ||--o{ development_plans_embed : "has many"

    cities {
        int id PK
        varchar name "Unique city identifier"
        varchar display_name "Human-readable name"
        varchar state "State code"
        timestamp created_at
        timestamp updated_at
    }

    census_tracts {
        varchar geoid PK "Geo identifier"
        geometry geom "PostGIS geometry"
        timestamp created_at
    }

    census_data {
        varchar census_tract_id FK "References census_tracts(geoid)"
        TBD TBD 
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

    development_plans_embed {
        int id PK
        int city_id FK "References cities(id)"
        text chunk_hash "SHA256 hash for deduplication (unique)"
        text text_chunk "Development plans text chunk"
        varchar project_name "e.g. 100 Hood Park Drive"
        varchar file_name "e.g. Letter_of_Intent__LOI"
        text[] zoning_codes "Zoning codes mentioned in text (extracted by the NER model)"
        vector(768) embedding "Embedding vector for semantic search"
        text[] article_reference "Articles referenced by the text (extracted by the NER model)"
        text location_context "Contextual details about a site (extracted by the NER model)"
        jsonb metadata "Flexible metadata (source_url, land_area, etc.)"
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

