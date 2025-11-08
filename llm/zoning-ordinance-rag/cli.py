#############################################################################
#                               IMPORTS                                     #
#############################################################################

# Standard library imports
import os
import argparse
import json
import time
import glob
import hashlib
import re

# Third-party imports
import pandas as pd
from pymilvus import MilvusClient
import fitz  # PyMuPDF
import openpyxl
from dotenv import load_dotenv

# Google Vertex AI imports
from google import genai
from google.genai import types
from google.genai import errors

# Local imports
from semantic_splitter import SemanticChunker

# Load environment variables from .env file
load_dotenv()


#############################################################################
#                           CONFIGURATION                                   #
#############################################################################

# Setup
GCP_PROJECT = os.environ["GCP_PROJECT"]
GCP_LOCATION = "us-central1"
EMBEDDING_MODEL = "text-embedding-004"
EMBEDDING_DIMENSION = 256
GENERATIVE_MODEL = "gemini-2.0-flash-001"
INPUT_FOLDER = "../../data/downloads/zoning_ordinance"
OUTPUT_FOLDER = "outputs"
MILVUS_URI = os.environ.get("MILVUS_PUBLIC_ENDPOINT")
MILVUS_TOKEN = os.environ.get("MILVUS_API_KEY")

# District code JSON file paths
DISTRICT_CODES_FOLDER = "../../data/collector/zoning_ordinance/district_codes"

# Global caches for district codes (loaded lazily)
_district_codes_cache = {}
_district_categories_cache = {}
_code_to_category_cache = {}


#############################################################################
#                      DISTRICT CODE UTILITIES                              #
#############################################################################

def load_district_codes(city):
    """Load district codes from JSON file for a given city

    Args:
        city: "boston" or "chicago"

    Returns:
        dict: {code: description} mapping
    """
    if city in _district_codes_cache:
        return _district_codes_cache[city]

    file_path = os.path.join(DISTRICT_CODES_FOLDER, f"{city}_district_codes.json")
    try:
        with open(file_path, 'r') as f:
            codes = json.load(f)
        _district_codes_cache[city] = codes
        return codes
    except FileNotFoundError:
        print(f"Warning: District codes file not found: {file_path}")
        return {}
    except json.JSONDecodeError as e:
        print(f"Warning: Error parsing district codes JSON for {city}: {e}")
        return {}

def load_district_categories(city):
    """Load district categories from JSON file for a given city

    Args:
        city: "boston" or "chicago"

    Returns:
        dict: {category_name: [codes]} mapping
    """
    if city in _district_categories_cache:
        return _district_categories_cache[city]

    file_path = os.path.join(DISTRICT_CODES_FOLDER, f"{city}_district_code_categories.json")
    try:
        with open(file_path, 'r') as f:
            categories = json.load(f)
        _district_categories_cache[city] = categories
        return categories
    except FileNotFoundError:
        print(f"Warning: District categories file not found: {file_path}")
        return {}
    except json.JSONDecodeError as e:
        print(f"Warning: Error parsing district categories JSON for {city}: {e}")
        return {}

def get_code_to_category_mapping(city):
    """Create reverse mapping: district_code -> category_name

    Args:
        city: "boston" or "chicago"

    Returns:
        dict: {code: category_name} mapping
    """
    if city in _code_to_category_cache:
        return _code_to_category_cache[city]

    categories = load_district_categories(city)
    code_to_category = {}

    for category_name, code_list in categories.items():
        for code in code_list:
            code_to_category[code] = category_name

    _code_to_category_cache[city] = code_to_category
    return code_to_category

#############################################################################
#                      INITIALIZE LLM CLIENT                                #
#############################################################################

llm_client = genai.Client(
    vertexai=True, project=GCP_PROJECT, location=GCP_LOCATION)

# System instructions for the generative model
SYSTEM_INSTRUCTION = """
You are an AI assistant specialized in zoning regulations, building codes, and urban planning ordinances. Your responses are based solely on the information provided in the zoning ordinance documents from Boston and Chicago given to you. Do not use any external knowledge or make assumptions beyond what is explicitly stated in these documents.

When answering a query:
1. Carefully read all the text chunks provided from the zoning ordinance documents.
2. Identify the most relevant information from these chunks to address the user's question.
3. Formulate your response using only the information found in the given chunks.
4. If the provided chunks do not contain sufficient information to answer the query, state that you don't have enough information to provide a complete answer based on the available ordinances.
5. Always maintain a professional and knowledgeable tone, befitting a zoning and urban planning expert.
6. If there are contradictions between Boston and Chicago ordinances, clearly distinguish between them in your response.
7. When relevant, specify which city's ordinance the information comes from (Boston or Chicago).

Remember:
- You are an expert in zoning regulations and building codes, but your knowledge is limited to the information in the provided ordinance documents.
- Do not invent information or draw from knowledge outside of the given text chunks.
- If asked about topics unrelated to zoning or building codes, politely redirect the conversation back to these subjects.
- Be concise in your responses while ensuring you cover all relevant information from the chunks.
- Your insights should help users understand zoning requirements, building regulations, and compliance matters.

Your goal is to provide accurate, ordinance-backed information about zoning regulations and building codes based solely on the content of the text chunks from Boston and Chicago ordinances you receive with each query.
"""


#############################################################################
#                   DOCUMENT EXTRACTION UTILITIES                           #
#############################################################################

def extract_district_codes(text, city):
    """Extract district codes from text by matching against known codes for the city

    Args:
        text: Text to search for district codes
        city: "boston" or "chicago"

    Returns:
        tuple: (district_codes: list, district_categories: list)
            - district_codes: List of matched district codes
            - district_categories: List of unique categories for matched codes
    """
    if not text:
        return [], []

    # Load district codes and category mapping for this city
    district_codes_dict = load_district_codes(city)
    code_to_category = get_code_to_category_mapping(city)

    if not district_codes_dict:
        return [], []

    # Sort codes by length (longest first) to match "B-10" before "B-1"
    codes_sorted = sorted(district_codes_dict.keys(), key=len, reverse=True)

    matched_codes = set()
    for code in codes_sorted:
        # Escape special regex characters in the code
        escaped_code = re.escape(code)

        # Special handling for single-letter codes to avoid false matches
        # These should only match in zoning-specific contexts
        if len(code) == 1:
            # Negative lookbehind to exclude section numbers (e.g., "17-2-0401-D")
            # Ensures code is NOT preceded by digit-hyphen pattern
            neg_lookbehind = r'(?<!\d-)'

            # Only match if preceded by zoning-related keywords or specific patterns
            # Examples: "R district", "in M", "the D district", "zone R", etc.
            pattern = neg_lookbehind + r'(?:district|zone|zoning|districts|zones)\s+' + escaped_code + r'\b'
            pattern += r'|' + neg_lookbehind + r'\b' + escaped_code + r'\s+(?:district|zone|zoning|districts|zones)'
            # Also match in comma-separated lists like "R, RS1, RM5"
            pattern += r'|' + neg_lookbehind + r'(?:,\s*|;\s*)' + escaped_code + r'(?:\s*,|\s*;|\s+)'
        else:
            # For multi-character codes, use word boundaries
            pattern = r'\b' + escaped_code + r'\b'

        if re.search(pattern, text, re.IGNORECASE):
            matched_codes.add(code)

    # Get categories for matched codes
    matched_categories = set()
    for code in matched_codes:
        category = code_to_category.get(code)
        if category:
            matched_categories.add(category)

    # Return sorted lists for consistency
    return sorted(list(matched_codes)), sorted(list(matched_categories))


def extract_structured_data_from_excel(excel_file):
    """Extract structured data from Boston Excel files with metadata per row

    Boston zoning ordinance has 2-level hierarchy:
    - ARTICLE (heading_1): e.g., "ARTICLE 9 NONCONFORMING USES"
    - SECTION (heading_2): e.g., "Section 9-1. Extension of Nonconforming Uses..."

    Returns tuple: (article_name, list of dicts)
    article_name: str - Article name from first data row
    sections: list of [{url, heading_2, content}, ...]
    """
    try:
        workbook = openpyxl.load_workbook(excel_file, data_only=True)
        sheet = workbook.active  # Get first/active sheet

        # Row 1 is empty, Row 2 has headers, Row 3+ are data rows
        # Get article name from row 4 (one row after the header's first data row)
        article_title = sheet.cell(4, 3).value  # Column 3 = Title
        article_subtitle = sheet.cell(4, 4).value  # Column 4 = Subtitle

        # Concatenate to form article name (heading_1)
        article_name = ""
        if article_title and article_subtitle:
            article_name = f"{article_title} {article_subtitle}".strip()
        elif article_title:
            article_name = str(article_title).strip()
        elif article_subtitle:
            article_name = str(article_subtitle).strip()

        print(f"  Article: {article_name}")

        structured_data = []

        # Process all data rows starting from Row 3
        # Columns: 1=Url, 2=NodeId, 3=Title, 4=Subtitle, 5=Content
        for row_num in range(3, sheet.max_row + 1):
            url = sheet.cell(row_num, 1).value
            title = sheet.cell(row_num, 3).value
            subtitle = sheet.cell(row_num, 4).value
            content = sheet.cell(row_num, 5).value

            # Skip rows without content
            if not content or not str(content).strip():
                continue

            # Concatenate Title and Subtitle for section name (heading_2)
            section_name = ""
            if title and subtitle:
                section_name = f"{title} {subtitle}".strip()
            elif title:
                section_name = str(title).strip()
            elif subtitle:
                section_name = str(subtitle).strip()

            structured_data.append({
                "url": str(url) if url else "",
                "heading_2": section_name,  # Section (standardized field name)
                "content": str(content)
            })

        workbook.close()
        return article_name, structured_data

    except Exception as e:
        print(f"Error reading Excel file {excel_file}: {e}")
        return "", []


def extract_hierarchical_sections_from_pdf(pdf_file):
    """Extract text from Chicago PDF with Title and Chapter detection using PyMuPDF

    Chicago zoning ordinance has 2-level hierarchy:
    - TITLE (heading_1): e.g., "TITLE 17 CHICAGO ZONING ORDINANCE"
    - CHAPTER (heading_2): e.g., "CHAPTER 17-1 GENERAL PROVISIONS"

    Returns list of dicts: [{heading_1, heading_2, content}, ...]
    """
    try:
        # Extract full text using PyMuPDF
        doc = fitz.open(pdf_file)
        all_text = ""
        for page in doc:
            all_text += page.get_text() + "\n"
        doc.close()

        if not all_text.strip():
            return []

        # Define regex patterns for Title and Chapter headings only
        patterns = {
            'title': re.compile(r'^TITLE\s+\d+[-\w]*\s+.*$', re.IGNORECASE | re.MULTILINE),
            'chapter': re.compile(r'^CHAPTER\s+\d+[-\w]*\s+.*$', re.IGNORECASE | re.MULTILINE),
        }

        # Find all headings with their positions
        headings = []
        for heading_type, pattern in patterns.items():
            for match in pattern.finditer(all_text):
                headings.append({
                    'type': heading_type,
                    'text': match.group().strip(),
                    'start': match.start(),
                    'end': match.end()
                })

        # Sort headings by position in document
        headings.sort(key=lambda x: x['start'])

        if not headings:
            # No headings found, return entire text as one section
            return [{
                "heading_1": None,
                "heading_2": None,
                "content": all_text
            }]

        # Track current Title and Chapter context
        current_title = None
        current_chapter = None
        sections = []

        for i, heading in enumerate(headings):
            heading_text = heading['text']

            # Skip RESERVED sections
            if 'RESERVED' in heading_text.upper():
                continue

            # Update context based on heading type
            if heading['type'] == 'title':
                current_title = heading_text
                current_chapter = None  # Reset chapter when new title starts
            elif heading['type'] == 'chapter':
                current_chapter = heading_text

            # Extract content from this heading to the next
            content_start = heading['end']
            if i + 1 < len(headings):
                content_end = headings[i + 1]['start']
            else:
                content_end = len(all_text)

            content = all_text[content_start:content_end].strip()

            # Skip if no content
            if not content:
                continue

            # Store section with standardized metadata
            sections.append({
                "heading_1": current_title,      # Title
                "heading_2": current_chapter,    # Chapter
                "content": content
            })

        return sections

    except Exception as e:
        print(f"Error reading PDF file {pdf_file}: {e}")
        return []


#############################################################################
#                         EMBEDDING UTILITIES                               #
#############################################################################



def generate_query_embedding(query):
    kwargs = {
        "output_dimensionality": EMBEDDING_DIMENSION
    }
    response = llm_client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=query,
        config=types.EmbedContentConfig(**kwargs)
    )
    return response.embeddings[0].values


def generate_text_embeddings(chunks, dimensionality: int = 256, batch_size=250, max_retries=5, retry_delay=5):
    # Max batch size is 250 for Vertex AI
    all_embeddings = []

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]

        # Retry logic with exponential backoff
        retry_count = 0
        while retry_count <= max_retries:
            try:
                response = llm_client.models.embed_content(
                    model=EMBEDDING_MODEL,
                    contents=batch,
                    config=types.EmbedContentConfig(
                        output_dimensionality=dimensionality),
                )
                all_embeddings.extend(
                    [embedding.values for embedding in response.embeddings])
                break

            except errors.APIError as e:
                retry_count += 1
                if retry_count > max_retries:
                    print(
                        f"Failed to generate embeddings after {max_retries} attempts. Last error: {str(e)}")
                    raise

                # Calculate delay with exponential backoff
                wait_time = retry_delay * (2 ** (retry_count - 1))
                print(
                    f"API error (code: {e.code}): {e.message}. Retrying in {wait_time} seconds (attempt {retry_count}/{max_retries})...")
                time.sleep(wait_time)

    return all_embeddings


def load_text_embeddings(df, client, collection_name, batch_size=500):

    # Generate ids
    df["id"] = df.index.astype(str)
    hashed_docs = df["document"].apply(
        lambda x: hashlib.sha256(x.encode()).hexdigest()[:16])
    df["id"] = hashed_docs + "-" + df["id"]

    # Fill NaN values with empty strings to ensure no None values
    string_fields = ["heading_1", "heading_2", "url"]
    for field in string_fields:
        if field in df.columns:
            df[field] = df[field].fillna("")

    # Process data in batches
    total_inserted = 0
    for i in range(0, df.shape[0], batch_size):
        # Create a copy of the batch and reset the index
        batch = df.iloc[i:i+batch_size].copy().reset_index(drop=True)

        # Build data for Milvus insert with optimal schema
        insert_data = []
        for _, row in batch.iterrows():
            # Ensure arrays are proper lists (not empty strings or None)
            district_codes = row["district_code"] if isinstance(row["district_code"], list) else []
            district_categories = row["district_category"] if isinstance(row["district_category"], list) else []

            # Create data entry matching the schema (use .get() for optional fields)
            data_entry = {
                "id": row["id"],
                "text": row["chunk"],
                "vector": row["embedding"],
                "city": row["city"],
                "document": row["document"],
                "district_codes": district_codes,
                "district_categories": district_categories,
                "heading_1": row.get("heading_1", ""),  # Boston: Article, Chicago: Title
                "heading_2": row.get("heading_2", ""),  # Boston: Section, Chicago: Chapter
                "url": row.get("url", "")               # Boston-specific
            }
            insert_data.append(data_entry)

        # Insert batch into Milvus
        client.insert(collection_name=collection_name, data=insert_data)
        total_inserted += len(batch)
        print(f"Inserted {total_inserted} items...")

    print(
        f"Finished inserting {total_inserted} items into collection '{collection_name}'")


#############################################################################
#                      RAG PIPELINE FUNCTIONS                               #
#############################################################################

def chunk():
    print("chunk()")

    # Make dataset folders
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    # Get all Excel files from Boston and PDF from Chicago
    boston_files = glob.glob(os.path.join(INPUT_FOLDER, "boston", "*.xlsx"))
    chicago_files = glob.glob(os.path.join(INPUT_FOLDER, "chicago", "*.pdf"))

    all_files = [("boston", f, "excel") for f in boston_files] + [("chicago", f, "pdf") for f in chicago_files]

    print(f"Number of files to process: {len(all_files)} (Boston: {len(boston_files)}, Chicago: {len(chicago_files)})")

    # Initialize semantic text splitter
    text_splitter = SemanticChunker(embedding_function=generate_text_embeddings)

    # Process each file
    for city, file_path, file_type in all_files:
        print(f"\nProcessing {city} file: {file_path}")
        filename = os.path.basename(file_path)
        document_name = filename.rsplit(".", 1)[0]

        all_chunk_data = []

        try:
            if file_type == "excel":
                # Boston: Extract structured data with url, heading_2 (section), content per row
                article_name, structured_data = extract_structured_data_from_excel(file_path)
                print(f"Extracted {len(structured_data)} sections from Excel")

                # Process each section (each Excel row)
                for section_data in structured_data:
                    content = section_data["content"]
                    if not content.strip():
                        continue

                    # Chunk the content using semantic chunking
                    chunks = text_splitter.create_documents([content])
                    chunk_texts = [doc.page_content for doc in chunks]

                    # Each chunk inherits the article (heading_1) and section (heading_2) metadata
                    for chunk_text in chunk_texts:
                        # Extract district codes using regex
                        district_codes, district_categories = extract_district_codes(chunk_text, city)

                        all_chunk_data.append({
                            "chunk": chunk_text,
                            "document": document_name,
                            "city": city,
                            "heading_1": article_name,              # Article
                            "heading_2": section_data["heading_2"], # Section
                            "url": section_data["url"],             # Boston-specific
                            "district_code": district_codes,
                            "district_category": district_categories
                        })

            elif file_type == "pdf":
                # Chicago: Extract sections with Title (heading_1) and Chapter (heading_2) metadata
                sections = extract_hierarchical_sections_from_pdf(file_path)
                print(f"Extracted {len(sections)} sections from PDF")

                # Process each section
                for section in sections:
                    content = section["content"]
                    if not content.strip():
                        continue

                    # Chunk the content using semantic chunking
                    chunks = text_splitter.create_documents([content])
                    chunk_texts = [doc.page_content for doc in chunks]

                    # Each chunk inherits the hierarchical metadata
                    for chunk_text in chunk_texts:
                        # Extract district codes using regex
                        district_codes, district_categories = extract_district_codes(chunk_text, city)

                        chunk_metadata = {
                            "chunk": chunk_text,
                            "document": document_name,
                            "city": city,
                            "district_code": district_codes,
                            "district_category": district_categories
                        }

                        # Add hierarchical metadata (only if not None)
                        if section.get("heading_1"):
                            chunk_metadata["heading_1"] = section["heading_1"]  # Title
                        if section.get("heading_2"):
                            chunk_metadata["heading_2"] = section["heading_2"]  # Chapter

                        all_chunk_data.append(chunk_metadata)

        except Exception as e:
            print(f"Error processing {filename}: {e}")
            continue

        if all_chunk_data:
            # Save the chunks with metadata
            data_df = pd.DataFrame(all_chunk_data)
            print(f"Total chunks created: {len(data_df)}")
            print("Sample chunk data:")
            print(data_df.head(2))

            jsonl_filename = os.path.join(
                OUTPUT_FOLDER, f"chunks-{city}-{document_name}.jsonl")
            with open(jsonl_filename, "w") as json_file:
                json_file.write(data_df.to_json(orient='records', lines=True))
            print(f"Saved to: {jsonl_filename}")


def embed():
    print("embed()")

    # Get the list of chunk files
    jsonl_files = glob.glob(os.path.join(OUTPUT_FOLDER, "chunks-*.jsonl"))
    print("Number of files to process:", len(jsonl_files))

    # Process
    for jsonl_file in jsonl_files:
        print("Processing file:", jsonl_file)

        data_df = pd.read_json(jsonl_file, lines=True)
        print("Shape:", data_df.shape)
        print(data_df.head())

        chunks = data_df["chunk"].values
        chunks = chunks.tolist()

        # Generate embeddings with semantic-split batch size
        embeddings = generate_text_embeddings(
            chunks, EMBEDDING_DIMENSION, batch_size=15)
        data_df["embedding"] = embeddings

        time.sleep(5)

        # Save
        print("Shape:", data_df.shape)
        print(data_df.head())

        jsonl_filename = jsonl_file.replace("chunks-", "embeddings-")
        with open(jsonl_filename, "w") as json_file:
            json_file.write(data_df.to_json(orient='records', lines=True))


def load():
    print("load()")

    # Connect to Milvus
    if not MILVUS_URI or not MILVUS_TOKEN:
        raise ValueError("MILVUS_PUBLIC_ENDPOINT and MILVUS_API_KEY must be set in environment variables")

    print(f"Connecting to Milvus at {MILVUS_URI}")
    client = MilvusClient(uri=MILVUS_URI, token=MILVUS_TOKEN)

    # Get a collection object from an existing collection, by name. If it doesn't exist, create it.
    collection_name = "zoning_ordinance_collection"  # Milvus requires underscores, not hyphens
    print("Creating collection:", collection_name)

    # Check if collection exists and drop it
    if client.has_collection(collection_name):
        client.drop_collection(collection_name)
        print(f"Deleted existing collection '{collection_name}'")
    else:
        print(f"Collection '{collection_name}' did not exist. Creating new.")

    # Create collection with optimal schema for filtering
    from pymilvus import DataType

    schema = client.create_schema(
        auto_id=False,
        enable_dynamic_field=False  # Use defined fields only for better performance
    )

    # Primary key
    schema.add_field(field_name="id", datatype=DataType.VARCHAR, is_primary=True, max_length=100)

    # Document text
    schema.add_field(field_name="text", datatype=DataType.VARCHAR, max_length=65535)

    # Vector embedding
    schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIMENSION)

    # Filterable metadata fields
    schema.add_field(field_name="city", datatype=DataType.VARCHAR, max_length=50)
    schema.add_field(field_name="document", datatype=DataType.VARCHAR, max_length=500)

    # Array fields for multi-value filtering
    schema.add_field(
        field_name="district_codes",
        datatype=DataType.ARRAY,
        element_type=DataType.VARCHAR,
        max_capacity=100,  # Increased to handle documents with many district codes
        max_length=50
    )
    schema.add_field(
        field_name="district_categories",
        datatype=DataType.ARRAY,
        element_type=DataType.VARCHAR,
        max_capacity=10,
        max_length=100
    )

    # Standardized hierarchical metadata fields (used by both Boston and Chicago)
    # Boston: heading_1 = Article, heading_2 = Section
    # Chicago: heading_1 = Title, heading_2 = Chapter
    schema.add_field(field_name="heading_1", datatype=DataType.VARCHAR, max_length=500)
    schema.add_field(field_name="heading_2", datatype=DataType.VARCHAR, max_length=500)

    # Boston-specific field
    schema.add_field(field_name="url", datatype=DataType.VARCHAR, max_length=1000)

    # Create index for vector field
    index_params = client.prepare_index_params()
    index_params.add_index(
        field_name="vector",
        metric_type="COSINE",
        index_type="AUTOINDEX"
    )

    client.create_collection(
        collection_name=collection_name,
        schema=schema,
        index_params=index_params
    )
    print(f"Created new empty collection '{collection_name}'")

    # Get the list of embedding files
    jsonl_files = glob.glob(os.path.join(OUTPUT_FOLDER, "embeddings-*.jsonl"))
    print("Number of files to process:", len(jsonl_files))

    # Process
    for jsonl_file in jsonl_files:
        print("Processing file:", jsonl_file)

        data_df = pd.read_json(jsonl_file, lines=True)
        print("Shape:", data_df.shape)
        print(data_df.head())

        # Load data
        load_text_embeddings(data_df, client, collection_name)

    # Flush the collection to persist all data
    print(f"\nFlushing collection to persist data...")
    client.flush(collection_name)
    print(f"Data flushed successfully!")


#############################################################################
#                          MAIN ENTRY POINT                                 #
#############################################################################

def main(args=None):
    print("CLI Arguments:", args)

    if args.chunk:
        chunk()

    if args.embed:
        embed()

    if args.load:
        load()


if __name__ == "__main__":
    # Generate the inputs arguments parser
    # if you type into the terminal '--help', it will provide the description
    parser = argparse.ArgumentParser(description="CLI for Zoning Ordinance RAG Pipeline")

    parser.add_argument(
        "--chunk",
        action="store_true",
        help="Chunk text using semantic splitting",
    )
    parser.add_argument(
        "--embed",
        action="store_true",
        help="Generate embeddings",
    )
    parser.add_argument(
        "--load",
        action="store_true",
        help="Load embeddings to vector db",
    )

    args = parser.parse_args()

    main(args)
