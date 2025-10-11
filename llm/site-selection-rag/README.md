# Site Selection RAG System

A Retrieval-Augmented Generation (RAG) system for real estate site selection, urban planning, and zoning analysis. This system processes academic research papers from the MDPI Land journal to provide insights for development projects.

## Overview

The system uses semantic chunking to split academic papers, generates embeddings with Vertex AI, stores them in ChromaDB, and provides intelligent question-answering through Google's Gemini LLM.

## Architecture

```
PDF Papers → Semantic Chunking → Embeddings (Vertex AI) → ChromaDB → Query Interface → Gemini LLM
```

## Prerequisites

- Docker and Docker Compose installed
- Google Cloud Project with Vertex AI API enabled
- GCP Service Account with appropriate permissions

## Setup

### 1. GCP Service Account Setup

1. Go to the [GCP Console](https://console.cloud.google.com/home/dashboard)
2. Navigate to "IAM & Admin" > "Service accounts"
3. Create a new service account named "llm-service-account"
4. Grant the following roles:
   - **Vertex AI User** (for embeddings and LLM)
   - **Storage Admin** (if using GCS for documents)
5. Create and download a JSON key
6. Place the JSON key in `../secrets/llm-service-account.json`

### 2. Project Structure

```
llm/
├── secrets/
│   └── llm-service-account.json
└── site-selection-rag/
    ├── cli.py                      # Main RAG pipeline
    ├── query.py                    # Interactive query interface
    ├── manage_chromadb.py          # Database management utility
    ├── agent_tools.py              # Agent function calling tools
    ├── semantic_splitter.py        # Semantic chunking implementation
    ├── Dockerfile                  # Container definition
    ├── docker-compose.yml          # Multi-container orchestration
    ├── docker-shell.sh             # Helper script to build and run
    ├── docker-entrypoint.sh        # Container startup script
    ├── pyproject.toml              # Python dependencies (uv)
    ├── uv.lock                     # Locked dependencies
    ├── README.md                   # This file
    ├── .venv/                      # Virtual environment (local dev)
    ├── outputs/                    # Generated chunks and embeddings
    │   ├── chunks-*.jsonl
    │   └── embeddings-*.jsonl
    └── docker-volumes/             # Persistent Docker storage
        └── chromadb/               # ChromaDB data persistence
```

### 3. Environment Configuration

The project expects:
- Academic papers in: `../../downloads/mdpi/land/`
- Service account key: `../secrets/llm-service-account.json`
- GCP Project ID configured in your environment or `cli.py`

## Running with Docker

### Start the Containers

```bash
cd llm/site-selection-rag
sh docker-shell.sh
```

Or manually:

```bash
# Start ChromaDB and CLI containers
docker-compose up -d

# Enter the CLI container
docker-compose run --rm site-selection-rag-cli
```

### Verify Containers

```bash
docker ps --filter "name=site-selection-rag"
```

You should see:
- `site-selection-rag-chromadb` (running on port 8000)
- `site-selection-rag-cli` (interactive shell)

## RAG Pipeline

### 1. Chunk PDF Documents

Process academic papers into semantic chunks:

```bash
python cli.py --chunk --chunk_type semantic-split
```

**Chunking methods available:**
- `char-split`: Character-based splitting (350 chars, 20 overlap)
- `recursive-split`: Recursive character splitting
- `semantic-split`: Semantic chunking (recommended)

Output: JSONL files in `outputs/chunks-{method}-{paper}.jsonl`

### 2. Generate Embeddings

Create embeddings using Vertex AI's `text-embedding-004` model:

```bash
python cli.py --embed --chunk_type semantic-split
```

- Batch size: 15 chunks (for semantic split) or 100 (for char/recursive)
- Embedding dimension: 256
- Automatic retry with exponential backoff

Output: JSONL files in `outputs/embeddings-{method}-{paper}.jsonl`

### 3. Load into Vector Database

Load embeddings into ChromaDB:

```bash
python cli.py --load --chunk_type semantic-split
```

- Creates collection: `mdpiland-semantic-split-collection`
- Stores metadata: paper name, category, category description
- Batch insertion: 500 items at a time

### 4. Combined Pipeline

Run all steps at once:

```bash
python cli.py --chunk --embed --load --chunk_type semantic-split
```

## Querying the System

### Interactive Query

Use the query script for custom questions:

```bash
python query.py "What factors influence land value in urban areas?"
```

**Query options:**

```bash
# With category filter
python query.py "How urban sprawl and land use change affect urban planning and spatial development?" --category "land use change and urbanization"

# Specify collection
python query.py "Find research focused on biodiversity conservation, protected areas, and land fragmentation." --collection mdpiland-semantic-split-collection

# Adjust number of results
python query.py "Find studies that analyze how climate change alters land cover, deforestation patterns, and ecosystem services." --n-results 20
```

### Available Categories

Each folder inside downloads/mdpi/land (data collected from paper collector) --> one category

## Database Management

### List Collections

```bash
python manage_chromadb.py --list
```

### Delete Collections

```bash
# Delete specific collection
python manage_chromadb.py --delete "mdpiland-semantic-split-collection"

# Delete all collections (with confirmation prompt)
python manage_chromadb.py --delete-all
```

## Configuration

### Key Settings (cli.py)

```python
GCP_PROJECT = os.environ["GCP_PROJECT"]
GCP_LOCATION = "us-central1"
EMBEDDING_MODEL = "text-embedding-004"
EMBEDDING_DIMENSION = 256
GENERATIVE_MODEL = "gemini-2.0-flash-001"
INPUT_FOLDER = "../../downloads/mdpi/land"
OUTPUT_FOLDER = "outputs"
CHROMADB_HOST = "site-selection-rag-chromadb"
CHROMADB_PORT = 8000
```

### Docker Configuration

The system uses two containers:
- **site-selection-rag-cli**: Python application with RAG pipeline
- **site-selection-rag-chromadb**: Vector database (persistent storage)

Network: `site-selection-rag-network`


## Development

### Running Without Docker

```bash
# Install dependencies with uv
uv sync

# Activate virtual environment
source .venv/bin/activate

# Set environment variables
export CHROMADB_HOST="localhost"
export CHROMADB_PORT="8000"
export GOOGLE_APPLICATION_CREDENTIALS="../secrets/llm-service-account.json"
export GCP_PROJECT="your-project-id"

# Run commands
python cli.py --chunk --chunk_type semantic-split
```

### Adding New Papers

1. Place PDF files in `../../downloads/mdpi/land/{category}/` (default download location of paper collector)
2. Run the pipeline: `python cli.py --chunk --embed --load --chunk_type semantic-split`
3. Query: `python query.py "your question" --category "{category}"`

## Future Improvements

### 1. Better PDF Parsers

The current system uses `pypdf` for PDF text extraction. Consider upgrading to more robust parsers:

- **[PyMuPDF](https://pypi.org/project/PyMuPDF/)**: Fast and accurate PDF parsing with better layout preservation
- **[pymupdf4llm](https://pypi.org/project/pymupdf4llm/)**: Optimized for LLM workflows with markdown output and semantic structure

**Benefits**: Improved text extraction quality, better handling of complex layouts, tables, and figures in academic papers.

### 2. Pre and Post Optimization

Implement query optimization and result enhancement:

- **Pre-optimization**: Query expansion, reformulation, or multi-query generation before retrieval
- **Post-optimization**: Result reranking, deduplication, or context filtering after retrieval

**Benefits**: Higher quality context for the LLM, more relevant answers, reduced hallucination.

### 3. Different Models for Embedding and Generation

Experiment with alternative models:

**Embedding Models:**
- `text-embedding-005` (newer Vertex AI model)
- `textembedding-gecko@003`
- OpenAI `text-embedding-3-large`

**Generative Models:**
- `gemini-1.5-pro` (more capable, higher cost)
- `gemini-2.0-flash-thinking-exp` (with reasoning)
- Claude via Vertex AI

**Benefits**: Performance benchmarking, cost optimization, task-specific model selection.

