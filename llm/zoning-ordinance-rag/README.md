# Zoning Ordinance RAG System

A Retrieval-Augmented Generation (RAG) system for zoning regulations and building codes. This system processes zoning ordinance documents from Boston (Excel files) and Chicago (PDF files) to provide expert guidance on compliance and development requirements.

## Overview

The system uses semantic chunking to split ordinance documents, generates embeddings with Vertex AI, stores them in ChromaDB, and provides intelligent question-answering through Google's Gemini LLM.

## Architecture

```
Excel/PDF Files → Text Extraction → Semantic Chunking → Embeddings (Vertex AI) → ChromaDB → Query Interface → Gemini LLM
```

## Data Sources

- **Boston**: Multiple Excel files containing zoning ordinance articles
  - Location: `../../data/collector/zoning_ordinance/collected_data/boston_collected_data/`
  - Format: `.xlsx` files with structured columns:
    - Row 1: Empty
    - Row 2: Headers (Url, NodeId, Title, Subtitle, Content)
    - Row 3+: Data rows with ordinance sections
  - Examples: ARTICLE_1_-_TITLE__PURPOSE_AND_SCOPE.xlsx, ARTICLE_2_-_DEFINITIONS.xlsx, etc.

- **Chicago**: PDF document containing comprehensive zoning ordinance
  - Location: `../../data/collector/zoning_ordinance/collected_data/chicago_collected_data/`
  - Format: Single PDF file (chicago-il-1.pdf)
  - Sections detected automatically using heading patterns

## Enhanced Metadata Structure

Each chunk in the vector database includes rich metadata for precise retrieval:

### Common Fields (Both Cities)
- **document**: Source document filename
- **city**: "boston" or "chicago"
- **district_code**: List of district codes found in the chunk
  - Matched from authoritative JSON files: B-1, R-2A, RS1, RM5, C2-1, etc.
- **district_category**: List of district categories for the matched codes
  - Examples: "Residential Districts", "Business and Commercial Districts", "Downtown Districts", etc.

### Boston-Specific Fields
- **article**: Article name from the Excel file (first row: Title + Subtitle)
  - Example: "ARTICLE 13 - DIMENSIONAL REQUIREMENTS"
  - All chunks from the same Excel file share the same article
- **section**: Individual section name from each row (Title + Subtitle)
  - Example: "Section 13-1. Dimensional Regulations."
  - Each chunk inherits the section from its source row
- **url**: Direct link to the ordinance section on municode.com

### Chicago-Specific Fields

Chicago uses **hierarchical metadata** to capture the document structure:

- **chapter**: CHAPTER heading (e.g., "CHAPTER 17-1 DEFINITIONS")
- **article**: ARTICLE heading (e.g., "ARTICLE 17-1-0400 USE REGULATIONS")
- **section**: SECTION heading (e.g., "SECTION 17-1-0403 PERMITTED USES")
- **heading**: The most specific heading for this chunk (duplicates one of the above)

**Hierarchical Structure:**
- The ordinance can have irregular nesting: `CHAPTER → ARTICLE → SECTION`
- Not all levels are always present (e.g., may skip from CHAPTER → SECTION)
- Each chunk inherits context from all parent levels currently active
- Sections marked "RESERVED" are automatically skipped

**Implementation:**
- Uses PyMuPDF for better text extraction from PDF
- Position-based regex detection with `re.finditer()` to find all headings
- Context tracking maintains current chapter/article/section as document is parsed
- When a higher-level heading is encountered, lower levels are reset

### Example Metadata

**Boston chunk:**
```json
{
  "document": "ARTICLE_13_-_DIMENSIONAL_REQUIREMENTS",
  "city": "boston",
  "article": "ARTICLE 13 - DIMENSIONAL REQUIREMENTS",
  "section": "Section 13-1. Dimensional Regulations.",
  "url": "https://library.municode.com/MA/Boston/codes/...",
  "district_code": ["B-1", "R-2"],
  "district_category": ["General Business Districts", "Residential Districts"]
}
```

**Chicago chunk (with full hierarchy):**
```json
{
  "document": "chicago-il-1",
  "city": "chicago",
  "chapter": "CHAPTER 17-1 DEFINITIONS",
  "article": "ARTICLE 17-1-0400 USE REGULATIONS",
  "section": "SECTION 17-1-0403 PERMITTED USES",
  "heading": "SECTION 17-1-0403 PERMITTED USES",
  "district_code": ["B2-1", "C1-1"],
  "district_category": ["Business and Commercial Districts"]
}
```

**Chicago chunk (irregular nesting - Chapter → Section):**
```json
{
  "document": "chicago-il-1",
  "city": "chicago",
  "chapter": "CHAPTER 13 PARKING",
  "section": "SECTION 13-1 PARKING REQUIREMENTS",
  "heading": "SECTION 13-1 PARKING REQUIREMENTS",
  "district_code": [],
  "district_category": []
}
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
└── zoning-ordinance-rag/
    ├── cli.py                      # Main RAG pipeline with Excel/PDF support
    ├── query.py                    # Interactive query interface
    ├── manage_chromadb.py          # Database management utility
    ├── agent_tools.py              # Agent function calling tools (placeholder)
    ├── semantic_splitter.py        # Semantic chunking implementation
    ├── Dockerfile                  # Container definition
    ├── docker-compose.yml          # Multi-container orchestration
    ├── docker-shell.sh             # Helper script to build and run
    ├── docker-entrypoint.sh        # Container startup script
    ├── pyproject.toml              # Python dependencies (uv)
    ├── uv.lock                     # Locked dependencies (generated)
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
- Zoning ordinance data in: `../../data/collector/zoning_ordinance/collected_data/`
- Service account key: `../secrets/llm-service-account.json`
- GCP Project ID configured in your environment or `docker-shell.sh`

## Running with Docker

### Start the Containers

```bash
cd llm/zoning-ordinance-rag
sh docker-shell.sh
```

Or manually:

```bash
# Start ChromaDB and CLI containers
docker-compose up -d

# Enter the CLI container
docker-compose run --rm zoning-ordinance-rag-cli
```

### Verify Containers

```bash
docker ps --filter "name=zoning-ordinance-rag"
```

You should see:
- `zoning-ordinance-rag-chromadb` (running on port 8001, mapped to internal 8000)
- `zoning-ordinance-rag-cli` (interactive shell)

## RAG Pipeline

### 1. Chunk Documents

Process Excel and PDF documents into semantic chunks:

```bash
python cli.py --chunk
```

**What happens:**

**Boston Excel Processing:**
1. Reads structured data from Excel (Url, Title, Subtitle, Content columns)
2. Extracts article name from first data row (row 4: Title + Subtitle)
   - Example: "ARTICLE 13 - DIMENSIONAL REQUIREMENTS"
   - This article name applies to ALL chunks from this Excel file
3. For each subsequent row with Content:
   - Concatenates Title + Subtitle as section name
   - Chunks the Content text using semantic chunking
   - Each chunk inherits: article, section, url, and extracted zoning codes
4. Preserves hierarchical metadata at the chunk level

**Chicago PDF Processing (Hierarchical Extraction):**
1. Extracts all text from PDF using PyMuPDF for better text quality
2. Detects hierarchical headings using regex patterns with `re.finditer()`:
   - CHAPTER headings (e.g., "CHAPTER 17-1 DEFINITIONS")
   - ARTICLE headings (e.g., "ARTICLE 17-1-0400 USE REGULATIONS")
   - SECTION headings (e.g., "SECTION 17-1-0403 PERMITTED USES")
   - APPENDIX headings
3. Sorts all detected headings by position in the document
4. Maintains hierarchical context as document is parsed:
   - Tracks current chapter, article, and section
   - When a higher-level heading is encountered, lower levels are reset
   - Handles irregular nesting (e.g., Chapter → Section, skipping Article)
5. For each section between headings:
   - Extracts content from current heading to next heading
   - Skips sections marked "RESERVED"
   - Chunks the section content using semantic chunking
   - Each chunk inherits full hierarchical context: chapter, article, section, heading
6. Result: Chunks with complete ordinance structure for precise retrieval

**Semantic Chunking:**
- Uses embeddings to identify natural semantic boundaries in text
- Creates chunks based on meaning rather than arbitrary character counts
- Preserves context and coherence within each chunk
- Optimal for legal/regulatory text like zoning ordinances

**District Code Extraction:**
- Matches district codes against authoritative JSON files:
  - **Source**: `../../data/collector/zoning_ordinance/collected_data/district_codes/`
    - `{city}_district_codes.json`: Maps codes to descriptions
    - `{city}_district_code_categories.json`: Maps categories to code lists
  - **Boston codes**: B-1, B-2, R-2A, M-1, etc. (68 total)
  - **Chicago codes**: RS1, RM5, B1-1, C2-1, DX-7, M1-1, etc. (105 total)
  - Uses word boundaries for exact matching (prevents "B-1" from matching "B-10")
  - Sorts codes by length (longest first) to avoid partial matches
  - Returns both matched codes and their categories

Output: JSONL files in `outputs/chunks-{city}-{document}.jsonl` with full metadata

### 2. Generate Embeddings

Create embeddings using Vertex AI's `text-embedding-004` model:

```bash
python cli.py --embed
```

- Batch size: 15 chunks (optimized for semantic chunking)
- Embedding dimension: 256
- Automatic retry with exponential backoff
- Model: `text-embedding-004` from Vertex AI

Output: JSONL files in `outputs/embeddings-{city}-{document}.jsonl`

### 3. Load into Vector Database

Load embeddings into ChromaDB:

```bash
python cli.py --load
```

- Creates collection: `zoning-ordinance-collection`
- Stores complete metadata per chunk: document, city, title, url (Boston), district_code, district_category
- Batch insertion: 500 items at a time
- Vector similarity: Cosine distance

### 4. Combined Pipeline

Run all steps at once:

```bash
python cli.py --chunk --embed --load
```

## Querying the System

### Interactive Query

Use the query script for questions about zoning ordinances:

```bash
python query.py "What are the height restrictions for residential buildings?"
```

**Query options:**

```bash
# Filter by city (Boston or Chicago)
python query.py "What are the parking requirements for commercial buildings?" --city boston

# Specify collection
python query.py "What are setback requirements?" --collection zoning-ordinance-collection

# Adjust number of results
python query.py "What are the definitions for mixed-use development?" --n-results 20

# Combined example
python query.py "What are the sign regulations?" --city chicago --n-results 10
```

### Query Parameters

- `query` (required): Your question about zoning ordinances
- `--collection`: Collection name (default: `zoning-ordinance-collection`)
- `--n-results`: Number of chunks to retrieve (default: 15)
- `--city`: Filter by city - `boston` or `chicago` (optional)

### Example Queries

```bash
# General zoning questions
python query.py "What is the definition of a dwelling unit?"

# Boston-specific
python query.py "What are the front yard requirements?" --city boston

# Chicago-specific
python query.py "What are the permitted uses in residential zones?" --city chicago

# Specific topics
python query.py "What are the parking space dimensions?"
python query.py "What are the requirements for outdoor lighting?"
python query.py "What is allowed in transition zoning?"
```

### Query Output Format

The query response includes:

1. **LLM Response**: AI-generated answer based on retrieved chunks
2. **Sources & Metadata**: Detailed information for each retrieved chunk

**Example output:**
```
==================================================
LLM RESPONSE:
==================================================
[AI-generated answer based on ordinance text]

==================================================
Sources & Metadata:
--------------------------------------------------

Chunk 1:
  City: BOSTON
  Document: ARTICLE_13_-_DIMENSIONAL_REQUIREMENTS
  Article: ARTICLE 13 - DIMENSIONAL REQUIREMENTS
  Section: Section 13-1. Dimensional Regulations.
  URL: https://library.municode.com/MA/Boston/codes/...
  District Codes: B-1, R-2
  District Categories: General Business Districts, Residential Districts

Chunk 2:
  City: CHICAGO
  Document: chicago-il-1
  Chapter: CHAPTER 17-1 DEFINITIONS
  Article: ARTICLE 17-1-0400 USE REGULATIONS
  Section: SECTION 17-1-0403 PERMITTED USES
  Heading: SECTION 17-1-0403 PERMITTED USES
  District Codes: B2-1, C1-1
  District Categories: Business and Commercial Districts
==================================================
```

This rich metadata helps you:
- Verify the source of information
- Access the full ordinance online (Boston URLs)
- Identify relevant district codes and categories for further research
- Understand which city's regulations apply
- Navigate the hierarchical structure of ordinances (Chapter → Article → Section)
- Filter and compare regulations across different district types

## Database Management

### List Collections

```bash
python manage_chromadb.py --list
```

### Delete Collections

```bash
# Delete specific collection
python manage_chromadb.py --delete "zoning-ordinance-collection"

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
INPUT_FOLDER = "../../data/collector/zoning_ordinance/collected_data"
OUTPUT_FOLDER = "outputs"
CHROMADB_HOST = "zoning-ordinance-rag-chromadb"
CHROMADB_PORT = 8000
```

### Docker Configuration

The system uses two containers:
- **zoning-ordinance-rag-cli**: Python application with RAG pipeline
- **zoning-ordinance-rag-chromadb**: Vector database (persistent storage on port 8001)

Network: `zoning-ordinance-rag-network`

**Note**: ChromaDB runs on port 8001 (host) to avoid conflicts with site-selection-rag which uses port 8000.

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
python cli.py --chunk
```

### Adding New Ordinance Documents

1. **Boston (Excel)**: Place `.xlsx` files in `../../data/collector/zoning_ordinance/collected_data/boston_collected_data/`
2. **Chicago (PDF)**: Place PDF files in `../../data/collector/zoning_ordinance/collected_data/chicago_collected_data/`
3. Run the pipeline: `python cli.py --chunk --embed --load`
4. Query: `python query.py "your question" --city {city}`

### Excel File Format

Boston Excel files should follow this structure:
- **Row 1**: Empty
- **Row 2**: Headers (Url, NodeId, Title, Subtitle, Content)
- **Row 3+**: Data rows

**Required columns:**
- **Url**: Link to the ordinance on municode.com
- **Title**: Section title (e.g., "Section 13-1.", "ARTICLE 13")
- **Subtitle**: Section subtitle (e.g., "Dimensional Regulations")
- **Content**: Full text of the ordinance section

The system processes each row independently, chunking the Content and preserving the row's metadata (Title+Subtitle, URL) across all chunks.

## Key Differences from site-selection-rag

1. **Multi-format Support**: Handles both Excel (.xlsx) and PDF files
2. **PyMuPDF for PDF Processing**: Uses PyMuPDF (fitz) instead of pypdf for better text extraction quality
3. **Hierarchical Metadata**: Chicago chunks include ordinance structure (chapter, article, section, heading)
4. **Rich Metadata**: Each chunk includes chapter/article, URL (Boston), section, district codes, and district categories
5. **Row-level Processing**: Boston Excel files processed row-by-row to preserve section metadata
6. **Context Tracking**: Maintains hierarchical context while parsing Chicago PDF (handles irregular nesting)
7. **District Code Extraction**: JSON-based matching against authoritative district code lists (not regex-based)
8. **Structured Excel Data**: Processes Excel columns (Url, Title, Subtitle, Content) individually
9. **Specialized Prompts**: Focused on zoning regulations rather than academic research
10. **Separate Network**: Uses different Docker network and ports to avoid conflicts

## Future Improvements

### 1. Better Excel Parsing
- Preserve table structures and relationships
- Handle merged cells and complex layouts
- Extract embedded images and charts

### 2. Structured Data Extraction
- Parse article numbers and section references
- Create hierarchical relationships between ordinance sections
- Enable navigation through document structure

### 3. Cross-Reference Resolution
- Identify references to other sections (e.g., "See Article 13")
- Create links between related ordinance sections
- Support multi-hop queries across documents

### 4. Comparison Features
- Direct comparison between Boston and Chicago ordinances
- Highlight differences in similar regulations
- Generate comparison reports

### 5. Enhanced PDF Parsing
Consider upgrading to:
- **[PyMuPDF](https://pypi.org/project/PyMuPDF/)**: Better layout preservation
- **[pymupdf4llm](https://pypi.org/project/pymupdf4llm/)**: Optimized for LLM workflows

### 6. Pre and Post Optimization
- Query expansion and reformulation
- Result reranking and filtering
- Context deduplication

## Troubleshooting

### Port Conflicts
If port 8001 is already in use, modify `docker-compose.yml`:
```yaml
ports:
    - 8002:8000  # Change host port to 8002 or any available port
```

### Excel Reading Errors
Ensure Excel files:
- Are valid .xlsx format (not .xls)
- Are not password-protected
- Have at least one sheet with data

### Memory Issues
For large ordinance documents:
- Reduce batch size in `cli.py`
- Process cities separately
- Use `char-split` instead of `semantic-split`

## License

See main project LICENSE file.
