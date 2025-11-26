# Backend API

FastAPI backend for the Spatially application, providing REST APIs for querying census data, zoning ordinances, and development plans.

## Overview

The backend provides three main API endpoints:

- **Census API**: Natural language queries about census data using text-to-SQL
- **Zoning Ordinance API**: Semantic search in zoning ordinance documents
- **Development Plans API**: (In development)

## Prerequisites

- Python 3.10 or higher
- PostgreSQL with PostGIS extension
- Google Cloud Platform account (for Vertex AI embeddings)
- Together AI API key (for text-to-SQL)
- UV package manager (recommended) or pip

## Environment Configuration

Create a `.env` file in the project root (one level above `backend/`) with the following variables:

```bash
# Database Configuration
POSTGRE_HOST=your-postgres-host
POSTGRE_PORT=5432
POSTGRE_USER=your-postgres-user
POSTGRE_PASSWORD=your-postgres-password
APP_DB_NAME=your-database-name

# GCP Configuration
GCP_PROJECT=your-gcp-project-id
GCP_REGION=us-central1

# API Keys
TOGETHER_API_KEY=your-together-ai-api-key

# CORS Configuration (optional)
BACKEND_CORS_ORIGINS=http://localhost:3000,http://localhost:5173
FRONTEND_HOST=http://localhost:5173

# Environment
ENVIRONMENT=local
```

Alternatively, you can use the secrets files in the `secrets/` directory:

- `ac215-spatially-project.env`
- `ac215-spatially-aws-postgres-db.env`

## Installation

### Using UV (Recommended)

```bash
# Install UV if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
cd backend
uv sync

# Activate virtual environment
source .venv/bin/activate  # On Unix/macOS
# or
.venv\Scripts\activate  # On Windows
```

### Using pip

```bash
cd backend
pip install -e .
```

## Running the Application

### Option 1: Docker (Recommended for Development)

From the project root:

```bash
docker compose up backend
```

The API will be available at `http://localhost:8000`

### Option 2: Docker Build and Run

```bash
cd backend
docker build -t spatially-api .
docker run --rm -p 8000:8000 \
  -e POSTGRE_HOST=your-host \
  -e POSTGRE_USER=your-user \
  -e POSTGRE_PASSWORD=your-password \
  -e APP_DB_NAME=your-db \
  -e GCP_PROJECT=your-project \
  -e GCP_REGION=us-central1 \
  -e TOGETHER_API_KEY=your-key \
  spatially-api
```

### Option 3: Uvicorn (Local Development)

```bash
cd backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or with activated virtual environment:

```bash
uvicorn app.main:app --reload
```

## API Documentation

Once the server is running, access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/api/v1/openapi.json

## API Endpoints

### Census API

**Search Census Data**

```
GET /api/v1/census/search?question={your_question}&city={city}&year={year}
```

Example:

```bash
curl "http://localhost:8000/api/v1/census/search?question=What%20is%20the%20median%20household%20income%20in%20Boston?&city=boston&year=2023"
```

### Zoning Ordinance API

**Search Zoning Ordinances**

```
GET /api/v1/zoning_ordinance/search?city={city}&question={your_question}&top_k={k}
```

Example:

```bash
curl "http://localhost:8000/api/v1/zoning_ordinance/search?city=boston&question=What%20are%20the%20height%20restrictions%20for%20residential%20zones?&top_k=5"
```

**Get Zoning at Location**

```
GET /api/v1/zoning_ordinance/zoning?city={city}&latitude={lat}&longitude={lon}
```

Example:

```bash
curl "http://localhost:8000/api/v1/zoning_ordinance/zoning?city=boston&latitude=42.3601&longitude=-71.0589"
```

## Testing

### Running the Backend for Testing

To test the backend API, start it using Docker Compose:

```bash
docker compose up backend
```

The API will be available at `http://localhost:8000` for testing. You can use the interactive API documentation at `http://localhost:8000/docs` to test endpoints.

### Unit Tests

Run tests with pytest:

```bash
cd backend
uv run pytest
```

Run with coverage:

```bash
uv run pytest --cov=app --cov-report=html
```

## Code Quality

### Linting

The project uses Ruff for linting:

```bash
uv run ruff check app/
```

### Type Checking

Type checking with mypy:

```bash
uv run mypy app/
```

### Formatting

Format code with Ruff:

```bash
uv run ruff format app/
```

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   └── routes/          # API route handlers
│   │       ├── v1/          # API version 1
│   │       └── base.py      # Health check endpoints
│   ├── core/
│   │   ├── config.py        # Settings and configuration
│   │   ├── db.py            # Database setup
│   │   └── security.py      # Authentication
│   ├── models/              # SQLModel data models
│   ├── utils/               # Utility modules
│   │   ├── db_accessor.py   # Database utilities
│   │   ├── embeddor/        # Embedding generation
│   │   ├── text2sql/        # Text-to-SQL conversion
│   │   ├── vector_query/    # Vector similarity search
│   │   └── spatial_query/   # PostGIS spatial queries
│   └── main.py              # FastAPI application
├── tests/                   # Test files
├── pyproject.toml           # Project dependencies
└── Dockerfile               # Docker configuration
```

## Development Guidelines

### Code Style

- Follow PEP 8 for Python code
- Use type hints for all function signatures
- Maximum line length: 100 characters (handled by Ruff)
- Use docstrings for all public functions and classes

### Adding New Endpoints

1. Create route handler in `app/api/routes/v1/`
2. Register router in `app/api/routes/v1/__init__.py`
3. Add tests in `tests/`
4. Update API documentation (docstrings are auto-generated)

### Database Migrations

Database schema changes should be managed through migrations. See the main project README for database schema details.

## Troubleshooting

### Database Connection Issues

- Verify PostgreSQL is running and accessible
- Check environment variables are set correctly
- Ensure PostGIS extension is installed: `CREATE EXTENSION postgis;`
- Verify pgvector extension is installed: `CREATE EXTENSION vector;`

### GCP Authentication Issues

- Ensure `GOOGLE_APPLICATION_CREDENTIALS` points to valid service account key
- Verify service account has necessary permissions (Vertex AI User)
- Check GCP project ID is correct

### API Key Issues

- Verify `TOGETHER_API_KEY` is set correctly
- Check API key is valid and has sufficient credits

## References

- FastAPI Documentation: https://fastapi.tiangolo.com/
- Full-Stack FastAPI Template: https://github.com/fastapi/full-stack-fastapi-template
- PostGIS Documentation: https://postgis.net/documentation/
- pgvector Documentation: https://github.com/pgvector/pgvector
