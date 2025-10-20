# Zoning Ordinance RAG System

A Retrieval-Augmented Generation (RAG) system for zoning regulations and building codes. This system processes zoning ordinance documents from Boston and Chicago to provide expert guidance on compliance and development requirements.

## Overview

The system uses semantic chunking to split ordinance documents, generates embeddings with Vertex AI, stores them in ChromaDB, and provides intelligent question-answering through Google's Gemini LLM.

## Architecture

```
Excel/PDF Files → Text Extraction → Semantic Chunking → Embeddings → ChromaDB → Query Interface → LLM
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

## Metadata Structure

Each chunk in the vector database includes metadata for precise retrieval:

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

### Automatic Filter Extraction (Smart Querying)

The system uses **LLM-based automatic filter extraction** to intelligently analyze your query and apply relevant metadata filters. This improves retrieval precision by narrowing down results to the most relevant ordinance sections.

**How it works:**

1. **Detects City Context**: Recognizes when you mention "Boston" or "Chicago"
2. **Extracts District Codes**: Identifies explicit district codes (e.g., "RM5", "B-3-65")
3. **Understands Categories**: Maps general terms to district categories
   - "residential buildings" → "Residential Districts"
   - "commercial zones" → "Business and Commercial Districts"
4. **Conservative by Default**: Only applies filters that are clearly indicated in your query

**Examples of automatic filtering:**

```bash
# Automatically detects city=chicago
python query.py "what are the height limits in chicago?"

# Detects city=chicago + district_category="Residential Districts"
python query.py "residential buildings in chicago"

# Detects city=chicago + district_code="RM5" + district_category="Residential Districts"
python query.py "what are the height limits for chicago's residential buildings in RM5 zone?"

# Detects district_codes=["RS3", "RT4"] + district_category="Residential Districts"
python query.py "compare RS3 and RT4 districts"
```

The system will display which filters were automatically applied:

```
Filters Applied by LLM:
  City: chicago
  District Codes: RM5
  District Categories: Residential Districts
```

### Manual Filter Options

You can manually specify filters to override or supplement automatic detection:

```bash
# Filter by city
python query.py "What are the parking requirements?" --city boston

# Filter by specific district code(s) - can use multiple times
python query.py "What are the height limits?" --district-code RM5 --district-code RM6

# Filter by district category
python query.py "What uses are allowed?" --district-category "Residential Districts"

# Filter by article or section
python query.py "What are the definitions?" --article "ARTICLE 2"
python query.py "What are dimensional requirements?" --section "13-1"

# Disable automatic filter extraction (use only manual filters or no filters)
python query.py "What are height limits?" --no-auto-filter

# Adjust number of results
python query.py "What are setback requirements?" --n-results 20

# Combined example with manual filters
python query.py "What are the sign regulations?" --city chicago --district-code B1-1 --n-results 10
```

### Query Parameters

**Required:**
- `query`: Your question about zoning ordinances

**Optional Filters:**
- `--city`: Filter by city - `boston` or `chicago`
- `--district-code`: Filter by specific district code (e.g., `RM5`, `B-3-65`). Can be used multiple times for multiple codes.
- `--district-category`: Filter by district category (e.g., `"Residential Districts"`). Can be used multiple times.
- `--article`: Filter by article name/number
- `--section`: Filter by section name/number
- `--no-auto-filter`: Disable automatic LLM-based filter extraction (default: enabled)

**Other Options:**
- `--collection`: Collection name (default: `zoning-ordinance-collection`)
- `--n-results`: Number of chunks to retrieve (default: 15)

**Filter Behavior (Smart Hybrid Filtering):**
- **Type-specific override**: Manual filters override automatic detection ONLY for that specific filter type
  - Example: `--district-code RS5` overrides LLM's district code extraction, but LLM can still extract city and category
- **Best of both worlds**: LLM fills in filter types you didn't manually specify
  - Example: Query mentions "chicago" and "RM5", you provide `--district-code RS3` → Result: city=chicago (LLM), district_code=RS3 (manual), category="Residential Districts" (LLM)
- **Complete control**: Use `--no-auto-filter` to disable all automatic extraction
- **OR logic within filter type**: Multiple district codes or categories use OR (matches any)
- **AND logic between filter types**: Different filter types use AND (must match all)

### Example Queries

**Automatic Filter Extraction (No Manual Filters):**

```bash
# General question - no filters applied
python query.py "What is the definition of a dwelling unit?"

# City automatically detected
python query.py "What are the height restrictions in Boston?"
python query.py "Chicago parking requirements for commercial buildings"

# City + category automatically detected
python query.py "What uses are allowed in Chicago residential zones?"
python query.py "Boston commercial district regulations"

# City + specific district code + category detected
python query.py "What are the height limits for Chicago's RM5 zone?"
python query.py "What is allowed in Boston's B-3-65 district?"

# Multiple district codes detected
python query.py "Compare RS3 and RT4 districts in Chicago"
python query.py "Differences between H-1 and H-2 zones in Boston"
```

**Smart Hybrid Filtering (Manual + Automatic):**

```bash
# Manual city override, LLM detects category
python query.py "front yard setback requirements for residential zones" --city boston
# Result: city=boston (manual), category="Residential Districts" (LLM)

# Manual district code, LLM detects city and category
python query.py "height limits in chicago residential zones" --district-code RM5
# Result: city=chicago (LLM), district_code=RM5 (manual), category="Residential Districts" (LLM)

# Manual overrides specific code mentioned in query
python query.py "what are height limits in RS3 district?" --district-code RS5
# Result: district_code=RS5 (manual override, RS3 from query ignored)

# Multiple manual filters, LLM fills gaps
python query.py "height restrictions" --city chicago --district-code RM5 --district-code RM6
# Result: city=chicago (manual), district_codes=[RM5, RM6] (manual)

# Disable all automatic filtering
python query.py "What are parking requirements?" --no-auto-filter --city boston
# Result: city=boston (manual only), no LLM extraction
```

**Specific Topics:**

```bash
python query.py "What are the parking space dimensions?"
python query.py "What are the requirements for outdoor lighting?"
python query.py "What is allowed in transition zoning?"
python query.py "How are lot sizes calculated?"
```

### Query Output Format

The query response includes:

1. **User Question**: Your query
2. **Active Filters**: Which metadata filters are currently applied (combined manual + automatic)
3. **Search Results**: Number of relevant chunks found
4. **LLM Response**: AI-generated answer based on retrieved chunks
5. **Filter Sources**: Shows which filters were manual vs automatic
   - **Manual Filters**: Explicitly provided via CLI flags
   - **Automatic Filters**: Extracted by LLM from your query
6. **Sources & Metadata**: Detailed information for each retrieved chunk

**Example output with automatic filter extraction:**
```
==================================================
RAG (ZONING ORDINANCES)
==================================================
Connecting to ChromaDB at localhost:8000

User Question:
--------------------------------------------------
what are the height limits for chicago's residential buildings in RM5 zone?

Extracting relevant filters from query...

Searching zoning ordinance documents...

Active Filters:
  - City: chicago
  - District Code(s): RM5
  - District Category(ies): Residential Districts

Found 5 relevant chunks

Generating LLM response based on extracted information...

==================================================
LLM RESPONSE:
==================================================
[AI-generated answer about RM5 height limits in Chicago]

==================================================
Filter Sources:
--------------------------------------------------

  Automatic Filters (LLM-extracted):
    City: chicago
    District Codes: RM5
    District Categories: Residential Districts

==================================================
Sources & Metadata:
--------------------------------------------------

Chunk 1:
  City: CHICAGO
  Document: chicago_zoning_ordinance
  Chapter: CHAPTER 17-3 BULK REGULATIONS
  Section: SECTION 17-3-0401 BUILDING HEIGHT
  Heading: SECTION 17-3-0401 BUILDING HEIGHT
  District Codes: RM5
  District Categories: Residential Districts

Chunk 2:
  City: CHICAGO
  Document: chicago_zoning_ordinance
  Chapter: CHAPTER 17-2 USE REGULATIONS
  Article: ARTICLE 17-2-0200 RESIDENTIAL
  Section: SECTION 17-2-0207 MULTI-UNIT
  Heading: SECTION 17-2-0207 MULTI-UNIT
  District Codes: RM4.5, RM5, RM5.5
  District Categories: Residential Districts
==================================================
```

**Example output with Smart Hybrid Filtering (manual + automatic):**
```
==================================================
RAG (ZONING ORDINANCES)
==================================================

User Question:
--------------------------------------------------
What are the height restrictions for residential buildings in Chicago?

Active Filters:
  - City: chicago
  - District Code(s): RM5
  - District Category(ies): Residential Districts

Found 8 relevant chunks

==================================================
LLM RESPONSE:
==================================================
[AI-generated answer about Chicago RM5 height restrictions]

==================================================
Filter Sources:
--------------------------------------------------

  Manual Filters (user-specified):
    District Codes: RM5

  Automatic Filters (LLM-extracted):
    City: chicago
    District Categories: Residential Districts

==================================================
Sources & Metadata:
--------------------------------------------------

Chunk 1:
  City: CHICAGO
  Document: chicago_zoning_ordinance
  Chapter: CHAPTER 17-3 BULK REGULATIONS
  Section: SECTION 17-3-0401 BUILDING HEIGHT
  Heading: SECTION 17-3-0401 BUILDING HEIGHT
  District Codes: RM5
  District Categories: Residential Districts
==================================================
```

**Example output with manual-only filters (automatic disabled):**
```
==================================================
User Question:
--------------------------------------------------
What are the height restrictions?

Active Filters:
  - City: boston
  - District Code(s): B-3-65

==================================================
Filter Sources:
--------------------------------------------------

  Manual Filters (user-specified):
    City: boston
    District Codes: B-3-65

==================================================
```

### Benefits of Smart Hybrid Filtering

**Smart Hybrid Filtering provides:**

1. **Intelligent Automation**: LLM automatically detects context from your natural language query
2. **Selective Control**: Override specific filters when you need precision, keep automatic detection for others
3. **No Lost Context**: Manual filters don't wipe out all automatic detection - only their specific type
4. **Retrieval Precision**: Narrows down results to only relevant ordinance sections
5. **Response Quality**: LLM receives more focused context for better answers
6. **Performance**: Fewer chunks to process means faster responses
7. **Complete Transparency**: See exactly which filters came from where (manual vs automatic)

**Rich metadata helps you:**
- Verify the source of information
- Access the full ordinance online (Boston URLs)
- Identify relevant district codes and categories for further research
- Understand which city's regulations apply
- Navigate the hierarchical structure of ordinances (Chapter → Article → Section)
- Filter and compare regulations across different district types
- Trust the results by seeing exactly how the system filtered the data

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

## Differences from site-selection-rag

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

