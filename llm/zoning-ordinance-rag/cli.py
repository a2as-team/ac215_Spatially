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
import chromadb
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
CHROMADB_HOST = os.environ.get("CHROMADB_HOST", "localhost")
CHROMADB_PORT = int(os.environ.get("CHROMADB_PORT", "8001"))

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

    Returns tuple: (article_name, list of dicts)
    article_name: str - Article name from first data row
    sections: list of [{url, section, content}, ...]
    """
    try:
        workbook = openpyxl.load_workbook(excel_file, data_only=True)
        sheet = workbook.active  # Get first/active sheet

        # Row 1 is empty, Row 2 has headers, Row 3+ are data rows
        # Get article name from row 4 (one row after the header's first data row)
        article_title = sheet.cell(4, 3).value  # Column 3 = Title
        article_subtitle = sheet.cell(4, 4).value  # Column 4 = Subtitle

        # Concatenate to form article name
        article_name = ""
        if article_title and article_subtitle:
            article_name = f"{article_title} {article_subtitle}".strip()
        elif article_title:
            article_name = str(article_title).strip()
        elif article_subtitle:
            article_name = str(article_subtitle).strip()

        print(f"  Article: {article_name}")

        structured_data = []

        # Process all data rows starting from Row 3 (including the row before article)
        # Columns: 1=Url, 2=NodeId, 3=Title, 4=Subtitle, 5=Content
        for row_num in range(3, sheet.max_row + 1):
            url = sheet.cell(row_num, 1).value
            title = sheet.cell(row_num, 3).value
            subtitle = sheet.cell(row_num, 4).value
            content = sheet.cell(row_num, 5).value

            # Skip rows without content
            if not content or not str(content).strip():
                continue

            # Concatenate Title and Subtitle for section name
            section_name = ""
            if title and subtitle:
                section_name = f"{title} {subtitle}".strip()
            elif title:
                section_name = str(title).strip()
            elif subtitle:
                section_name = str(subtitle).strip()

            structured_data.append({
                "url": str(url) if url else "",
                "section": section_name,
                "content": str(content)
            })

        workbook.close()
        return article_name, structured_data

    except Exception as e:
        print(f"Error reading Excel file {excel_file}: {e}")
        return "", []


def extract_hierarchical_sections_from_pdf(pdf_file):
    """Extract text from PDF with hierarchical section detection using PyMuPDF

    Detects CHAPTER, ARTICLE, SECTION, and APPENDIX headings.
    Maintains hierarchical context (current chapter/article) for each section.

    Returns list of dicts: [{chapter, article, section, heading, content}, ...]
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

        # Define regex patterns for different heading types
        patterns = {
            'title': re.compile(r'^TITLE\s+\d+[-\w]*\s+.*$', re.IGNORECASE | re.MULTILINE),
            'chapter': re.compile(r'^CHAPTER\s+\d+[-\w]*\s+.*$', re.IGNORECASE | re.MULTILINE),
            'article': re.compile(r'^ARTICLE\s+\d+[A-Z\-]*\s+.*$', re.IGNORECASE | re.MULTILINE),
            'appendix': re.compile(r'^APPENDIX(?:\s+[A-Z0-9\-]+)?(?:\s+.*)?$', re.IGNORECASE | re.MULTILINE),
            'section': re.compile(r'^SECTION\s+\d+[-\d]*\s+.*$', re.IGNORECASE | re.MULTILINE),
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
                "title": None,
                "chapter": None,
                "article": None,
                "section": None,
                "heading": "Document",
                "content": all_text
            }]

        # Maintain current context
        current_context = {
            "title": None,
            "chapter": None,
            "article": None,
            "section": None
        }

        sections = []

        for i, heading in enumerate(headings):
            # Update context based on heading type
            heading_text = heading['text']

            # Skip RESERVED sections
            if 'RESERVED' in heading_text.upper():
                continue

            # Update context based on heading type
            if heading['type'] == 'title':
                current_context['title'] = heading_text
                current_context['chapter'] = None  # Reset lower levels
                current_context['article'] = None
                current_context['section'] = None
            elif heading['type'] == 'chapter':
                current_context['chapter'] = heading_text
                current_context['article'] = None  # Reset lower levels
                current_context['section'] = None
            elif heading['type'] == 'article':
                current_context['article'] = heading_text
                current_context['section'] = None  # Reset lower level
            elif heading['type'] == 'appendix':
                current_context['section'] = heading_text
            elif heading['type'] == 'section':
                current_context['section'] = heading_text

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

            # Store section with hierarchical metadata
            sections.append({
                "title": current_context['title'],
                "chapter": current_context['chapter'],
                "article": current_context['article'],
                "section": current_context['section'],
                "heading": heading_text,
                "content": content
            })

        return sections

    except Exception as e:
        print(f"Error reading PDF file {pdf_file}: {e}")
        return []


#############################################################################
#                         EMBEDDING UTILITIES                               #
#############################################################################

def normalize_district_code_to_field(code):
    """Convert district code to valid ChromaDB field name for filtering.

    Replaces special characters with underscores and adds 'district_' prefix.

    Examples:
        'RS3' -> 'district_RS3'
        'RT3.5' -> 'district_RT3_5'
        'H-1' -> 'district_H_1'
        'B-3-65' -> 'district_B_3_65'

    Args:
        code (str): District code from ordinance

    Returns:
        str: Normalized field name safe for ChromaDB metadata
    """
    normalized = code.replace('.', '_').replace('-', '_').replace(' ', '_')
    return f"district_{normalized}"


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


def load_text_embeddings(df, collection, batch_size=500):

    # Generate ids
    df["id"] = df.index.astype(str)
    hashed_docs = df["document"].apply(
        lambda x: hashlib.sha256(x.encode()).hexdigest()[:16])
    df["id"] = hashed_docs + "-" + df["id"]

    # Process data in batches
    total_inserted = 0
    for i in range(0, df.shape[0], batch_size):
        # Create a copy of the batch and reset the index
        batch = df.iloc[i:i+batch_size].copy().reset_index(drop=True)

        ids = batch["id"].tolist()
        documents = batch["chunk"].tolist()
        embeddings = batch["embedding"].tolist()

        # Build metadata for each row individually
        # Boston: article, section, url, district_code, district_category
        # Chicago: hierarchical metadata, district_code, district_category
        metadatas = []
        for _, row in batch.iterrows():
            metadata = {
                "document": row["document"],
                "city": row["city"],
                # Keep original JSON for display/backward compatibility
                "district_code": json.dumps(row["district_code"]) if isinstance(row["district_code"], list) else row["district_code"],
                "district_category": json.dumps(row["district_category"]) if isinstance(row["district_category"], list) else row["district_category"]
            }

            # Add flattened boolean fields for filtering district codes
            if isinstance(row["district_code"], list):
                for code in row["district_code"]:
                    if code:  # Skip empty strings
                        field_name = normalize_district_code_to_field(code)
                        metadata[field_name] = True

            # Add flattened boolean fields for filtering district categories
            if isinstance(row["district_category"], list):
                for category in row["district_category"]:
                    if category:  # Skip empty strings
                        # Normalize category name: replace spaces with underscores
                        cat_field = f"category_{category.replace(' ', '_')}"
                        metadata[cat_field] = True

            # Handle Boston (article + section) vs Chicago (hierarchical or old title)
            if "article" in row and row["article"]:  # Boston
                metadata["article"] = row["article"]
                metadata["section"] = row["section"]
                # Add URL for Boston only
                if "url" in row and row["url"]:
                    metadata["url"] = row["url"]
            elif "heading" in row:  # Chicago (hierarchical)
                if row.get("chapter"): metadata["chapter"] = row["chapter"]
                if row.get("article"): metadata["article"] = row["article"]
                if row.get("section"): metadata["section"] = row["section"]
                metadata["heading"] = row["heading"]

            metadatas.append(metadata)

        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings
        )
        total_inserted += len(batch)
        print(f"Inserted {total_inserted} items...")

    print(
        f"Finished inserting {total_inserted} items into collection '{collection.name}'")


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
                # Boston: Extract structured data with url, section, content per row
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

                    # Each chunk inherits the article and section metadata
                    for chunk_text in chunk_texts:
                        # Extract district codes using regex
                        district_codes, district_categories = extract_district_codes(chunk_text, city)

                        all_chunk_data.append({
                            "chunk": chunk_text,
                            "document": document_name,
                            "city": city,
                            "article": article_name,
                            "section": section_data["section"],
                            "url": section_data["url"],
                            "district_code": district_codes,
                            "district_category": district_categories
                        })

            elif file_type == "pdf":
                # Chicago: Extract sections with hierarchical metadata
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

                    # Each chunk inherits the section's hierarchical metadata
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
                        if section.get("title"):
                            chunk_metadata["title"] = section["title"]
                        if section.get("chapter"):
                            chunk_metadata["chapter"] = section["chapter"]
                        if section.get("article"):
                            chunk_metadata["article"] = section["article"]

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

    # Clear Cache
    chromadb.api.client.SharedSystemClient.clear_system_cache()

    # Connect to chroma DB
    print(f"Connecting to ChromaDB at {CHROMADB_HOST}:{CHROMADB_PORT}")
    client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)

    # Get a collection object from an existing collection, by name. If it doesn't exist, create it.
    collection_name = "zoning-ordinance-collection"
    print("Creating collection:", collection_name)

    try:
        # Clear out any existing items in the collection
        client.delete_collection(name=collection_name)
        print(f"Deleted existing collection '{collection_name}'")
    except Exception:
        print(f"Collection '{collection_name}' did not exist. Creating new.")

    collection = client.create_collection(
        name=collection_name, metadata={"hnsw:space": "cosine"})
    print(f"Created new empty collection '{collection_name}'")
    print("Collection:", collection)

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
        load_text_embeddings(data_df, collection)


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
