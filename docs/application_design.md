# Application Design Document

## Overview

Spatially is a spatially intelligent agent that leverages Large Language Models (LLMs) to help with real estate investment decisions. The system combines census data, zoning ordinances, zoning maps, and development plans to provide comprehensive spatial intelligence through natural language queries.

## Solution Architecture

### High-Level System Components

The Spatially system consists of the following major components:

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend                                │
│                    (Currently in development)                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ HTTP/REST API
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                    Backend API (FastAPI)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Census API   │  │ Zoning API   │  │ Development  │          │
│  │              │  │              │  │ Plans API    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└────────────────────────────┬────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Text2SQL   │    │   Vector     │    │   Spatial    │
│   (Census)   │    │   Search     │    │   Queries    │
│              │    │   (Zoning)   │    │   (Maps)     │
└──────────────┘    └──────────────┘    └──────────────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  PostgreSQL DB  │
                    │  (PostGIS)      │
                    └─────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   GCS        │    │   Vertex AI  │    │   Together   │
│   Storage    │    │   Embeddings │    │   AI (LLM)   │
└──────────────┘    └──────────────┘    └──────────────┘
```

### Data Flow

1. **User Query Flow**:

   - User submits natural language query via API
   - Query is routed to appropriate handler (census, zoning, or development plans)
   - For census: Text-to-SQL conversion using Together AI (Llama 3.3 70B)
   - For zoning: Semantic search using vector embeddings (Vertex AI)
   - Results are returned with metadata and context

2. **Data Collection Flow**:

   - Collectors fetch data from various sources (Census API, municipal websites)
   - Raw data is stored in GCS with versioned paths
   - Processors transform and enrich data (e.g., chunking, embedding)
   - Processed data is stored in PostgreSQL with PostGIS extensions

3. **Model Training Flow**:
   - Development plans are labeled in Label Studio
   - Annotations are exported to GCS
   - Training jobs run on Vertex AI
   - Fine-tuned models are stored in GCS and deployed to Label Studio backend

### API Endpoints

#### Census API (`/api/v1/census`)

- `GET /search`: Natural language query about census data
  - Converts query to SQL using text-to-SQL model
  - Supports city, location, and year filters
  - Returns structured census data

#### Zoning Ordinance API (`/api/v1/zoning_ordinance`)

- `GET /search`: Semantic search in zoning ordinance documents

  - Uses vector similarity search with pgvector
  - Supports location-based filtering (auto-detects zoning codes)
  - Returns relevant text chunks with similarity scores

- `GET /zoning`: Get zoning information at specific location
  - Uses PostGIS spatial queries
  - Returns zoning codes, articles, and usage information

#### Development Plans API (`/api/v1/development_plans`)

- Currently in development

### Database Schema

The system uses PostgreSQL with PostGIS for spatial data:

- **census_tract**: Geographic boundaries of census tracts
- **acs_table**: Metadata about ACS (American Community Survey) tables
- **acs_variable**: Variable definitions for census data
- **acs_value**: Actual census values by tract, year, and variable
- **zoning_maps**: Zoning district geometries with codes and usage
- **zoning_ordinance_embed**: Chunked zoning ordinance text with vector embeddings
- **cities**: City metadata and configuration

See the main README.md for the complete database schema diagram.

## Technical Architecture

### Technologies and Frameworks

#### Backend

- **FastAPI**: Modern Python web framework for building APIs
- **PostgreSQL + PostGIS**: Relational database with spatial extensions
- **pgvector**: Vector similarity search extension for PostgreSQL
- **LangChain**: Framework for LLM integration
- **Together AI**: Text-to-SQL generation (Llama 3.3 70B Instruct Turbo)
- **Vertex AI**: Text embeddings for semantic search
- **psycopg**: PostgreSQL database adapter
- **SQLModel**: SQL database ORM

#### Data Processing

- **Python 3.10+**: Core programming language
- **Selenium**: Web scraping for zoning ordinance collection
- **GeoPandas**: Geospatial data manipulation
- **Pandas**: Data processing and analysis
- **Google Cloud Storage (GCS)**: Object storage for versioned data

#### Model Training

- **HuggingFace Transformers**: Model training framework
- **PyTorch**: Deep learning framework
- **Weights & Biases (W&B)**: Experiment tracking
- **Vertex AI**: Cloud training infrastructure
- **Label Studio**: Data annotation platform

#### Infrastructure

- **Docker**: Containerization
- **Docker Compose**: Multi-container orchestration
- **Google Cloud Platform**: Cloud infrastructure
- **Git**: Version control

### Design Patterns

1. **Repository Pattern**: Database access is abstracted through `DBConnector` and `DBAccessor` classes
2. **Strategy Pattern**: Different collectors (census, zoning, development plans) implement a common interface
3. **Factory Pattern**: Collectors are auto-discovered and registered dynamically
4. **Adapter Pattern**: LLM clients (Together AI, Vertex AI) are wrapped in adapter classes
5. **Template Method Pattern**: Base collectors define the workflow, subclasses implement specific steps

### Code Organization

```
backend/
├── app/
│   ├── api/
│   │   └── routes/
│   │       ├── v1/          # API v1 endpoints
│   │       │   ├── census.py
│   │       │   ├── zoning_ordinance.py
│   │       │   └── development_plans.py
│   │       └── base.py      # Health check endpoints
│   ├── core/
│   │   ├── config.py        # Settings and configuration
│   │   ├── db.py            # Database connection setup
│   │   └── security.py      # Authentication/authorization
│   ├── models/              # SQLModel data models
│   └── utils/
│       ├── db_accessor.py   # Database query utilities
│       ├── embeddor/        # Embedding generation
│       ├── text2sql/        # Text-to-SQL conversion
│       ├── vector_query/    # Vector similarity search
│       └── spatial_query/   # PostGIS spatial queries
│   └── main.py              # FastAPI application entry point

data/
├── collector/               # Data collection modules
│   ├── census/             # Census data collection
│   ├── zoning_ordinance/   # Zoning ordinance scraping
│   ├── zoning_maps/        # Zoning map collection
│   └── development_plans/  # Development plan collection
└── processor/              # Data processing modules
    └── zoning_ordinance/   # Chunking and embedding

workflow/
├── jobs/                   # Vertex AI job definitions
│   └── finetune/          # Model training jobs
├── pipelines/              # Data pipeline definitions
└── packages/               # Python package publishing

llm/
└── development_plans/
    └── NER/               # NER model training code
```

### Key Design Decisions

1. **Vector Search for Zoning**: Zoning ordinances are chunked and embedded using Vertex AI embeddings, enabling semantic search without keyword matching.

2. **Text-to-SQL for Census**: Census queries use text-to-SQL conversion to leverage the structured nature of census data while maintaining natural language interface.

3. **GCS for Data Versioning**: Large datasets (census downloads, zoning documents) are stored in GCS with organized directory structures, enabling versioning and reproducibility.

4. **PostGIS for Spatial Queries**: Spatial operations (point-in-polygon, intersections) are handled by PostGIS, providing efficient spatial indexing and queries.

5. **Modular Collector Architecture**: Each data source has its own collector class, making it easy to add new cities or data sources.

6. **API Versioning**: APIs are versioned (v1, v2) to support backward compatibility as the system evolves.

### Security Considerations

- Environment variables for sensitive credentials (API keys, database passwords)
- Service account keys stored securely in `secrets/` directory
- CORS configuration for frontend access
- Database connection pooling and proper connection management

### Scalability Considerations

- Vector search uses pgvector with efficient indexing
- Spatial queries use PostGIS spatial indexes (GIST)
- LLM calls are rate-limited and include retry logic
- Database connections are pooled and properly closed
- GCS provides scalable object storage

### Deployment Strategy

- **Local Development**: Docker Compose for running all services locally
- **Cloud Training**: Vertex AI for model training jobs
- **API Deployment**: FastAPI backend can be deployed to cloud runtimes (GCP Cloud Run, AWS ECS, etc.)
- **Database**: Managed PostgreSQL service (AWS RDS, GCP Cloud SQL) with PostGIS extension
