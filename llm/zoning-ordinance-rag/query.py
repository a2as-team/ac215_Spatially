import os
import chromadb
import argparse

# Set default environment variables if not already set
if "GCP_PROJECT" not in os.environ:
    os.environ["GCP_PROJECT"] = "our-dominion-471022-n9"
if "CHROMADB_HOST" not in os.environ:
    os.environ["CHROMADB_HOST"] = "localhost"
if "CHROMADB_PORT" not in os.environ:
    os.environ["CHROMADB_PORT"] = "8000"
if "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "../secrets/llm-service-account.json"

import cli
import json


# Available filter vocabulary for LLM-based filter extraction
AVAILABLE_FILTERS = {
    "cities": ["boston", "chicago"],
    "boston_categories": [
        "Residential Districts",
        "Mixed Use Districts",
        "Local Business Districts",
        "General Business Districts",
        "Industrial / Manufacturing Districts",
        "Open Space Districts"
    ],
    "chicago_categories": [
        "Residential Districts",
        "Business and Commercial Districts",
        "Downtown Districts",
        "Manufacturing Districts",
        "Special Purpose Districts"
    ]
}


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


def extract_filters_from_query(query: str) -> dict:
    """Use LLM to analyze query and extract relevant metadata filters.

    The LLM is instructed to be conservative and only extract filters
    that are clearly indicated in the user's query. It prefers broader
    district categories over specific codes.

    Args:
        query (str): User's question about zoning ordinances

    Returns:
        dict: Extracted filters with keys:
            - city (str|None): 'boston' or 'chicago'
            - district_categories (list): Category names if applicable
            - district_codes (list): Specific district codes if applicable
            - article (str|None): Article filter if mentioned
            - section (str|None): Section filter if mentioned
    """
    filter_extraction_prompt = f"""You are a filter extraction assistant for a zoning ordinance database.

Analyze the following user query and extract ONLY the filters that are CLEARLY indicated in the query.
Be VERY conservative - if a filter is not explicitly mentioned or strongly implied, DO NOT extract it.

User Query: "{query}"

Available Filters:
- Cities: {', '.join(AVAILABLE_FILTERS['cities'])}
- Boston District Categories: {', '.join(AVAILABLE_FILTERS['boston_categories'])}
- Chicago District Categories: {', '.join(AVAILABLE_FILTERS['chicago_categories'])}

Common District Codes (examples):
- Chicago: RS1, RS2, RS3, RT3.5, RT4, RM4.5, RM5, RM5.5, RM6, RM6.5, B1-1, B2-1, B3-1, C1-1, C2-1, C3-1, M1-1, M2-1, M3-1, DC-12, DX-5, DR-3, DS-3, PMD, POS
- Boston: R-.8, H-1, H-2, H-3, H-4, H-5, L-1, L-2, B-1, B-2, B-3-65, B-4, M-1, M-2, M-4, OS, S0, S1, S2, S3

Guidelines:
1. Only extract city if explicitly mentioned (e.g., "in Boston", "Chicago zoning")

2. **IMPORTANT - District Codes vs Categories:**
   - If the query explicitly mentions a SPECIFIC district code (e.g., "RM5", "RS3", "H-1", "B-3-65"), extract that code in district_codes
   - If the query only mentions general terms (e.g., "residential", "commercial"), use broader categories instead
   - When specific codes are mentioned, you can ALSO include the category if it helps

3. Category keyword mapping:
   - "residential" → "Residential Districts"
   - "commercial", "business" → "Business and Commercial Districts" (Chicago) or "General Business Districts" (Boston)
   - "industrial", "manufacturing" → "Manufacturing Districts" or "Industrial / Manufacturing Districts"
   - "downtown" → "Downtown Districts" (Chicago only)
   - "mixed use" → "Mixed Use Districts" (Boston only)

4. If the query is vague or general, return empty filters

Examples:
- "what are height limits in chicago?" → city: chicago, no other filters
- "residential buildings in chicago" → city: chicago, district_categories: ["Residential Districts"]
- "RM5 zone in chicago" → city: chicago, district_codes: ["RM5"], district_categories: ["Residential Districts"]
- "RS3 and RT4 districts" → district_codes: ["RS3", "RT4"], district_categories: ["Residential Districts"]

Return your response as a JSON object with this exact structure:
{{
    "city": null or "boston" or "chicago",
    "district_categories": [],
    "district_codes": [],
    "article": null,
    "section": null
}}

Return ONLY the JSON object, nothing else."""

    try:
        # Call LLM to extract filters
        response = cli.llm_client.models.generate_content(
            model=cli.GENERATIVE_MODEL,
            contents=filter_extraction_prompt,
            config=cli.types.GenerateContentConfig(
                temperature=0.1,  # Low temperature for consistent extraction
                response_mime_type="application/json"
            )
        )

        # Parse JSON response
        extracted_filters = json.loads(response.text)

        # Validate and clean the response
        return {
            "city": extracted_filters.get("city"),
            "district_categories": extracted_filters.get("district_categories", []),
            "district_codes": extracted_filters.get("district_codes", []),
            "article": extracted_filters.get("article"),
            "section": extracted_filters.get("section")
        }
    except Exception as e:
        print(f"Warning: Failed to extract filters with LLM: {e}")
        # Return empty filters on error
        return {
            "city": None,
            "district_categories": [],
            "district_codes": [],
            "article": None,
            "section": None
        }


def main(args=None):
    """Main function to query the RAG system"""
    print("=" * 50)
    print("RAG (ZONING ORDINANCES)")
    print("=" * 50)

    # Connect to chroma DB - use environment variables for flexibility
    chromadb_host = os.environ.get("CHROMADB_HOST", "localhost")
    chromadb_port = int(os.environ.get("CHROMADB_PORT", "8000"))

    print(f"Connecting to ChromaDB at {chromadb_host}:{chromadb_port}")
    client = chromadb.HttpClient(host=chromadb_host, port=chromadb_port)
    collection = client.get_collection(name=args.collection)

    query = args.query

    print(f"\nUser Question:")
    print("-" * 50)
    print(query)

    # LLM-based automatic filter extraction
    # Check if user provided any manual filters
    has_manual_filters = any([
        args.city,
        args.district_codes,
        args.district_categories,
        args.article,
        args.section
    ])

    # Track which filters were auto-applied
    llm_applied_filters = {}

    # Only use LLM extraction if no manual filters and not disabled
    if not has_manual_filters and not args.no_auto_filter:
        print("\nExtracting relevant filters from query...")
        extracted_filters = extract_filters_from_query(query)

        # Apply extracted filters to args if they were detected
        if extracted_filters["city"]:
            args.city = extracted_filters["city"]
            llm_applied_filters["city"] = extracted_filters["city"]

        if extracted_filters["district_categories"]:
            args.district_categories = extracted_filters["district_categories"]
            llm_applied_filters["district_categories"] = extracted_filters["district_categories"]

        if extracted_filters["district_codes"]:
            args.district_codes = extracted_filters["district_codes"]
            llm_applied_filters["district_codes"] = extracted_filters["district_codes"]

        if extracted_filters["article"]:
            args.article = extracted_filters["article"]
            llm_applied_filters["article"] = extracted_filters["article"]

        if extracted_filters["section"]:
            args.section = extracted_filters["section"]
            llm_applied_filters["section"] = extracted_filters["section"]

    print("\nSearching zoning ordinance documents...")
    query_embedding = cli.generate_query_embedding(query)

    # Build query parameters
    query_params = {
        "query_embeddings": [query_embedding],
        "n_results": args.n_results
    }

    # Build where clause with filters
    where_conditions = []
    active_filters = []

    # Add city filter if specified
    if args.city:
        where_conditions.append({"city": args.city})
        active_filters.append(f"City: {args.city}")

    # Add district code filters using flattened boolean fields (pre-retrieval filtering)
    if args.district_codes:
        # Build OR conditions for multiple district codes
        district_conditions = []
        for code in args.district_codes:
            field_name = normalize_district_code_to_field(code)
            district_conditions.append({field_name: True})

        if len(district_conditions) == 1:
            where_conditions.append(district_conditions[0])
        else:
            where_conditions.append({"$or": district_conditions})

        active_filters.append(f"District Code(s): {', '.join(args.district_codes)}")

    # Add district category filters using flattened boolean fields
    if args.district_categories:
        # Build OR conditions for multiple district categories
        category_conditions = []
        for category in args.district_categories:
            cat_field = f"category_{category.replace(' ', '_')}"
            category_conditions.append({cat_field: True})

        if len(category_conditions) == 1:
            where_conditions.append(category_conditions[0])
        else:
            where_conditions.append({"$or": category_conditions})

        active_filters.append(f"District Category(ies): {', '.join(args.district_categories)}")

    # Add article filter (exact match or substring)
    if args.article:
        where_conditions.append({"article": args.article})
        active_filters.append(f"Article: {args.article}")

    # Add section filter (exact match or substring)
    if args.section:
        where_conditions.append({"section": args.section})
        active_filters.append(f"Section: {args.section}")

    # Combine all where conditions with AND logic
    if len(where_conditions) == 1:
        query_params["where"] = where_conditions[0]
    elif len(where_conditions) > 1:
        query_params["where"] = {"$and": where_conditions}

    # Display active filters
    if active_filters:
        print("\nActive Filters:")
        for filter_desc in active_filters:
            print(f"  - {filter_desc}")

    # Search
    results = collection.query(**query_params)

    print(f"Found {len(results['documents'][0])} relevant chunks")

    # Create RAG prompt
    INPUT_PROMPT = f"""
You are an AI assistant specialized in zoning regulations and building codes, providing expert guidance on compliance and development requirements.

Based on the following excerpts from zoning ordinance documents, please answer this question:
{query}

Provide specific, actionable information based on the ordinance text.

Ordinance excerpts:
{chr(10).join(results["documents"][0])}
"""

    print("\nGenerating LLM response based on extracted information...")
    response = cli.llm_client.models.generate_content(
        model=cli.GENERATIVE_MODEL,
        contents=INPUT_PROMPT,
        config=cli.types.GenerateContentConfig(
            system_instruction=cli.SYSTEM_INSTRUCTION
        )
    )

    print("\n" + "=" * 50)
    print("LLM RESPONSE:")
    print("=" * 50)
    print(response.text)

    # Display LLM-applied filters if any
    if llm_applied_filters:
        print("\n" + "=" * 50)
        print("Filters Applied by LLM:")
        print("-" * 50)
        if "city" in llm_applied_filters:
            print(f"  City: {llm_applied_filters['city']}")
        if "district_categories" in llm_applied_filters:
            print(f"  District Categories: {', '.join(llm_applied_filters['district_categories'])}")
        if "district_codes" in llm_applied_filters:
            print(f"  District Codes: {', '.join(llm_applied_filters['district_codes'])}")
        if "article" in llm_applied_filters:
            print(f"  Article: {llm_applied_filters['article']}")
        if "section" in llm_applied_filters:
            print(f"  Section: {llm_applied_filters['section']}")

    print("\n" + "=" * 50)
    print("Sources & Metadata:")
    print("-" * 50)
    if results['metadatas'] and results['metadatas'][0]:
        import json as json_lib

        # Display detailed metadata for each chunk
        for i, meta in enumerate(results['metadatas'][0], 1):
            if meta:
                print(f"\nChunk {i}:")
                print(f"  City: {meta.get('city', 'Unknown').upper()}")
                print(f"  Document: {meta.get('document', 'Unknown')}")

                # Display Boston metadata (article + section) vs Chicago metadata (hierarchical)
                if 'article' in meta and meta['article'] and 'url' in meta:  # Boston
                    print(f"  Article: {meta['article']}")
                    print(f"  Section: {meta.get('section', 'N/A')}")
                    # Display URL for Boston
                    if meta['url']:
                        print(f"  URL: {meta['url']}")
                elif 'heading' in meta:  # Chicago (hierarchical)
                    if meta.get('chapter'): print(f"  Chapter: {meta['chapter']}")
                    if meta.get('article'): print(f"  Article: {meta['article']}")
                    if meta.get('section'): print(f"  Section: {meta['section']}")
                    print(f"  Heading: {meta['heading']}")

                # Display district codes
                district_code = meta.get('district_code', '[]')
                if isinstance(district_code, str):
                    try:
                        codes = json_lib.loads(district_code)
                        if codes:
                            print(f"  District Codes: {', '.join(codes)}")
                    except:
                        if district_code and district_code != '[]':
                            print(f"  District Codes: {district_code}")
                elif isinstance(district_code, list) and district_code:
                    print(f"  District Codes: {', '.join(district_code)}")

                # Display district categories
                district_category = meta.get('district_category', '[]')
                if isinstance(district_category, str):
                    try:
                        categories = json_lib.loads(district_category)
                        if categories:
                            print(f"  District Categories: {', '.join(categories)}")
                    except:
                        if district_category and district_category != '[]':
                            print(f"  District Categories: {district_category}")
                elif isinstance(district_category, list) and district_category:
                    print(f"  District Categories: {', '.join(district_category)}")
    else:
        print("  No metadata available")
    print("=" * 50)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Query the Zoning Ordinance RAG system")
    parser.add_argument(
        "query",
        type=str,
        help="Your question about zoning ordinances"
    )
    parser.add_argument(
        "--collection",
        type=str,
        default="zoning-ordinance-collection",
        help="Collection name to query (default: zoning-ordinance-collection)"
    )
    parser.add_argument(
        "--n-results",
        type=int,
        default=15,
        help="Number of relevant chunks to retrieve (default: 15)"
    )
    parser.add_argument(
        "--city",
        type=str,
        choices=["boston", "chicago"],
        help="Filter results by city (optional)"
    )
    parser.add_argument(
        "--district-code",
        type=str,
        action="append",
        dest="district_codes",
        help="Filter by district code(s) - can be used multiple times (e.g., --district-code RS1 --district-code RM5)"
    )
    parser.add_argument(
        "--district-category",
        type=str,
        action="append",
        dest="district_categories",
        help="Filter by district category(ies) - can be used multiple times (e.g., --district-category Residential)"
    )
    parser.add_argument(
        "--article",
        type=str,
        help="Filter by article name/number (optional)"
    )
    parser.add_argument(
        "--section",
        type=str,
        help="Filter by section name/number (optional)"
    )
    parser.add_argument(
        "--no-auto-filter",
        action="store_true",
        help="Disable automatic LLM-based filter extraction (filters will only be applied if manually specified)"
    )

    args = parser.parse_args()

    main(args)
