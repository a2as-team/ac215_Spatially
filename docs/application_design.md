# Application Design Document

## Overview

Spatially is a spatially intelligent agent that leverages Large Language Models (LLMs) to help with real estate investment decisions. The system combines census data, zoning ordinances, zoning maps, and development plans to provide comprehensive spatial intelligence through natural language queries.

The application consists of:

- **Frontend**: Next.js web application with interactive maps and AI chat interface
- **Backend**: FastAPI REST API providing data access and LLM-powered query capabilities
- **Data Pipeline**: Collectors and processors for ingesting and processing spatial data
- **ML Pipeline**: Model training infrastructure for fine-tuning NER models on development plans

## Solution Architecture

### High-Level System Components

The Spatially system consists of the following major components:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ City Select  │  │  City Page   │  │  Chat UI     │          │
│  │   (Home)     │  │  (Map View)  │  │  (AI Chat)   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│         │                 │                 │                   │
│         └─────────────────┼─────────────────┘                   │
│                           │                                     │
│                    MapLibre GL (Interactive Maps)                │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ HTTP/REST API
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                    Backend API (FastAPI)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Cities API   │  │ Census API   │  │ Zoning API   │          │
│  │              │  │              │  │              │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│  ┌──────────────┐  ┌──────────────┐                            │
│  │ Chat API     │  │ Development  │                            │
│  │              │  │ Plans API    │                            │
│  └──────────────┘  └──────────────┘                            │
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

1. **User Query Flow (Frontend)**:

   - User selects a city from the home page
   - City page loads with interactive map (MapLibre GL) showing zoning districts
   - User can:
     - Click on map to get zoning information at specific location
     - Search zoning ordinances using natural language queries
     - Chat with AI assistant about zoning regulations
   - Frontend makes API calls to backend endpoints
   - Results are displayed on map and in chat interface

2. **User Query Flow (Backend)**:

   - User submits natural language query via API
   - Query is routed to appropriate handler:
     - **Census**: Text-to-SQL conversion using Together AI (Llama 3.3 70B)
     - **Zoning Ordinance**: Semantic search using vector embeddings (Vertex AI)
     - **Zoning Maps**: PostGIS spatial queries for location-based lookups
     - **Chat**: LLM-based conversational interface with zoning context
   - Results are returned with metadata and context

3. **Data Collection Flow**:

   - Collectors fetch data from various sources (Census API, municipal websites)
   - Raw data is stored in GCS with organized directory structures
   - Processors transform and enrich data (e.g., chunking, embedding)
   - Processed data is stored in PostgreSQL with PostGIS extensions

4. **Model Training Flow**:
   - Development plans are labeled in Label Studio
   - Annotations are exported to GCS
   - Training jobs run on Vertex AI
   - Fine-tuned models are stored in GCS and deployed to Label Studio backend

### API Endpoints

#### Cities API (`/api/v1/cities`)

- `GET /`: Get all available cities
  - Returns list of cities with zoning data available
- `GET /{city_name}`: Get information about a specific city
  - Returns city details (id, name, created_at)

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
- `GET /{city}`: Get all zoning data for a city
  - Returns all zoning districts with geometries for map display

#### Chat API (`/api/v1/chats`)

- `GET /`: Get all chats for a session
  - Returns recent chat history
- `GET /{chat_id}`: Get a specific chat by ID
- `POST /`: Start a new chat
  - Creates new chat session with AI assistant
  - Uses LLM for zoning-related conversations
- `POST /{chat_id}`: Continue an existing chat
  - Adds messages to existing chat thread

#### Development Plans API (`/api/v1/development_plans`)

- `GET /`: Placeholder endpoint (in development)

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
- **Vertex AI**: Text embeddings for semantic search and LLM chat
- **psycopg**: PostgreSQL database adapter
- **SQLModel**: SQL database ORM

#### Frontend

- **Next.js 16**: React framework with Pages Router
- **React 19**: UI library
- **TypeScript**: Type-safe JavaScript
- **Mantine UI**: Component library for UI elements
- **MapLibre GL**: Interactive map rendering (open-source alternative to Mapbox)
- **TanStack Query (React Query)**: Data fetching and state management
- **React Markdown**: Markdown rendering for chat messages
- **Axios**: HTTP client for API requests

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
│   │       │   ├── zoning_map.py
│   │       │   ├── cities.py
│   │       │   ├── chat.py
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
│       ├── spatial_query/   # PostGIS spatial queries
│       └── chat/            # Chat history and LLM client
│   └── main.py              # FastAPI application entry point

frontend/
├── pages/
│   ├── index.tsx            # Home page (city selection)
│   ├── city/
│   │   └── [id].tsx         # City page (map + chat)
│   ├── _app.tsx             # App wrapper with providers
│   └── _document.tsx        # HTML document structure
├── services/
│   ├── api.ts               # API client configuration
│   ├── citiesApi.ts         # Cities API client
│   ├── zoningApi.ts         # Zoning API client
│   └── chatApi.ts           # Chat API client
├── hooks/
│   ├── useChat.ts           # Chat hooks (React Query)
│   └── useZoningSearch.ts   # Zoning search hooks
└── styles/
    └── globals.css          # Global styles

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

3. **GCS for Data Storage**: Large datasets (census downloads, zoning documents) are stored in GCS with organized directory structures. Versioning is minimal (relies on GCS timestamps and Git commits).

4. **PostGIS for Spatial Queries**: Spatial operations (point-in-polygon, intersections) are handled by PostGIS, providing efficient spatial indexing and queries.

5. **MapLibre GL for Maps**: Open-source mapping library provides interactive map visualization with zoning district overlays, avoiding Mapbox licensing costs.

6. **Chat Interface with Context**: AI chat interface uses LLM (Vertex AI) with system instructions about zoning regulations, enabling conversational queries about zoning.

7. **Session-Based Chat History**: Chat history is managed per session (stored in memory/backend), allowing users to continue conversations across page loads.

8. **Modular Collector Architecture**: Each data source has its own collector class, making it easy to add new cities or data sources.

9. **API Versioning**: APIs are versioned (v1, v2) to support backward compatibility as the system evolves.

10. **React Query for State Management**: Frontend uses TanStack Query for efficient data fetching, caching, and state synchronization with backend APIs.

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

### User Interface

The frontend provides a modern, interactive interface for exploring zoning data:

1. **Home Page (`/`)**:

   - City selection interface
   - Displays all available cities with zoning data
   - Card-based layout with city information

2. **City Page (`/city/{cityName}`)**:

   - Interactive map (MapLibre GL) showing zoning districts
   - Click on map to get zoning information at specific coordinates
   - Sidebar with:
     - Chat interface for AI-powered zoning questions
     - Chat history sidebar
     - Zoning search results
   - Real-time zoning data overlay on map
   - Markdown rendering for chat responses

3. **Features**:
   - Responsive design with Mantine UI components
   - Dark mode support
   - Real-time map interactions
   - Chat with AI assistant about zoning regulations
   - Visual zoning district boundaries on map

### Deployment Strategy

- **Local Development**: Docker Compose for running all services locally
  - Backend: FastAPI on port 8000
  - Frontend: Next.js on port 3000
  - Database: PostgreSQL with PostGIS
- **Cloud Training**: Vertex AI for model training jobs
- **API Deployment**: FastAPI backend can be deployed to cloud runtimes (GCP Cloud Run, AWS ECS, etc.)
- **Frontend Deployment**: Next.js can be deployed to Vercel, Netlify, or containerized deployments
- **Database**: Managed PostgreSQL service (AWS RDS, GCP Cloud SQL) with PostGIS extension
