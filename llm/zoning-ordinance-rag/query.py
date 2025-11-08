import os
from pymilvus import MilvusClient
import argparse

# Set default environment variables if not already set
if "GCP_PROJECT" not in os.environ:
    os.environ["GCP_PROJECT"] = "our-dominion-471022-n9"
if "MILVUS_PUBLIC_ENDPOINT" not in os.environ:
    os.environ["MILVUS_PUBLIC_ENDPOINT"] = os.getenv("MILVUS_PUBLIC_ENDPOINT")
if "MILVUS_API_KEY" not in os.environ:
    os.environ["MILVUS_API_KEY"] = os.getenv("MILVUS_API_KEY")
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
    "district_codes": []
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
            "district_codes": extracted_filters.get("district_codes", [])
        }
    except Exception as e:
        print(f"Warning: Failed to extract filters with LLM: {e}")
        # Return empty filters on error
        return {
            "city": None,
            "district_categories": [],
            "district_codes": []
        }


def main(args=None):
    """Main function to query the RAG system"""
    print("=" * 50)
    print("RAG (ZONING ORDINANCES)")
    print("=" * 50)

    # Connect to Milvus - use environment variables for flexibility
    milvus_uri = os.environ.get("MILVUS_PUBLIC_ENDPOINT")
    milvus_token = os.environ.get("MILVUS_API_KEY")

    if not milvus_uri or not milvus_token:
        raise ValueError("MILVUS_PUBLIC_ENDPOINT and MILVUS_API_KEY must be set in environment variables")

    print(f"Connecting to Milvus at {milvus_uri}")
    client = MilvusClient(uri=milvus_uri, token=milvus_token)

    query = args.query

    print(f"\nUser Question:")
    print("-" * 50)
    print(query)

    # LLM-based automatic filter extraction (Smart Hybrid Filtering)
    # Track which filters were auto-applied
    llm_applied_filters = {}
    manual_filters = {}

    # Track which filters were manually specified
    if args.city:
        manual_filters["city"] = args.city
    if args.district_codes:
        manual_filters["district_codes"] = args.district_codes
    if args.district_categories:
        manual_filters["district_categories"] = args.district_categories

    # Always run LLM extraction unless explicitly disabled
    # Manual filters override only their specific type, not all filters
    if not args.no_auto_filter:
        print("\nExtracting relevant filters from query...")
        extracted_filters = extract_filters_from_query(query)

        # Apply extracted filters ONLY if user didn't manually specify that filter type
        if extracted_filters["city"] and not args.city:
            args.city = extracted_filters["city"]
            llm_applied_filters["city"] = extracted_filters["city"]

        if extracted_filters["district_categories"] and not args.district_categories:
            args.district_categories = extracted_filters["district_categories"]
            llm_applied_filters["district_categories"] = extracted_filters["district_categories"]

        if extracted_filters["district_codes"] and not args.district_codes:
            args.district_codes = extracted_filters["district_codes"]
            llm_applied_filters["district_codes"] = extracted_filters["district_codes"]

    print("\nSearching zoning ordinance documents...")
    query_embedding = cli.generate_query_embedding(query)

    # Build list of active filters for display
    active_filters = []
    if args.city:
        active_filters.append(f"City: {args.city}")
    if args.district_codes:
        active_filters.append(f"District Code(s): {', '.join(args.district_codes)}")
    if args.district_categories:
        active_filters.append(f"District Category(ies): {', '.join(args.district_categories)}")

    # Display active filters
    if active_filters:
        print("\nActive Filters:")
        for filter_desc in active_filters:
            print(f"  - {filter_desc}")

    # Build Milvus filter expression for server-side filtering
    filter_expressions = []

    # Add city filter
    if args.city:
        filter_expressions.append(f'city == "{args.city}"')

    # Add district code filters using ARRAY_CONTAINS_ANY
    if args.district_codes:
        codes_str = ', '.join([f'"{code}"' for code in args.district_codes])
        filter_expressions.append(f'ARRAY_CONTAINS_ANY(district_codes, [{codes_str}])')

    # Add district category filters using ARRAY_CONTAINS_ANY
    if args.district_categories:
        cats_str = ', '.join([f'"{cat}"' for cat in args.district_categories])
        filter_expressions.append(f'ARRAY_CONTAINS_ANY(district_categories, [{cats_str}])')

    # Combine all filters with AND
    milvus_filter = ' && '.join(filter_expressions) if filter_expressions else None

    # Search in Milvus with server-side filtering
    search_results = client.search(
        collection_name=args.collection,
        data=[query_embedding],
        limit=args.n_results,
        filter=milvus_filter,
        output_fields=["text", "city", "document", "district_codes", "district_categories",
                      "heading_1", "heading_2", "url"]
    )

    # Convert Milvus results to ChromaDB-like format for backward compatibility
    results = {
        "documents": [[]],
        "metadatas": [[]]
    }

    if search_results and len(search_results) > 0:
        for hit in search_results[0]:
            entity = hit["entity"]
            results["documents"][0].append(entity["text"])

            # Build metadata dict from fields (convert Protobuf arrays to Python lists)
            metadata = {
                "city": entity.get("city", ""),
                "document": entity.get("document", ""),
                "district_code": list(entity.get("district_codes", [])),  # Convert to Python list
                "district_category": list(entity.get("district_categories", [])),  # Convert to Python list
                "heading_1": entity.get("heading_1", ""),  # Boston: Article, Chicago: Title
                "heading_2": entity.get("heading_2", ""),  # Boston: Section, Chicago: Chapter
                "url": entity.get("url", "")               # Boston-specific
            }
            results["metadatas"][0].append(metadata)

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

    # Display filter sources (manual vs LLM) if any filters were used
    if llm_applied_filters or manual_filters:
        print("\n" + "=" * 50)
        print("Filter Sources:")
        print("-" * 50)

        # Display manual filters
        if manual_filters:
            print("\n  Manual Filters (user-specified):")
            if "city" in manual_filters:
                print(f"    City: {manual_filters['city']}")
            if "district_categories" in manual_filters:
                print(f"    District Categories: {', '.join(manual_filters['district_categories'])}")
            if "district_codes" in manual_filters:
                print(f"    District Codes: {', '.join(manual_filters['district_codes'])}")

        # Display LLM-applied filters
        if llm_applied_filters:
            print("\n  Automatic Filters (LLM-extracted):")
            if "city" in llm_applied_filters:
                print(f"    City: {llm_applied_filters['city']}")
            if "district_categories" in llm_applied_filters:
                print(f"    District Categories: {', '.join(llm_applied_filters['district_categories'])}")
            if "district_codes" in llm_applied_filters:
                print(f"    District Codes: {', '.join(llm_applied_filters['district_codes'])}")

    print("\n" + "=" * 50)
    print("Sources & Metadata:")
    print("-" * 50)
    if results['metadatas'] and results['metadatas'][0]:
        # Display detailed metadata for each chunk
        for i, meta in enumerate(results['metadatas'][0], 1):
            if meta:
                print(f"\nChunk {i}:")
                print(f"  City: {meta.get('city', 'Unknown').upper()}")
                print(f"  Document: {meta.get('document', 'Unknown')}")

                # Display standardized hierarchical metadata
                # Boston: heading_1 = Article, heading_2 = Section
                # Chicago: heading_1 = Title, heading_2 = Chapter
                city = meta.get('city', '').lower()

                if meta.get('heading_1'):
                    label_1 = "Article" if city == "boston" else "Title"
                    print(f"  {label_1}: {meta['heading_1']}")

                if meta.get('heading_2'):
                    label_2 = "Section" if city == "boston" else "Chapter"
                    print(f"  {label_2}: {meta['heading_2']}")

                # Display URL for Boston (Boston-specific field)
                if meta.get('url'):
                    print(f"  URL: {meta['url']}")

                # Display district codes (now always a list from array field)
                district_codes = meta.get('district_code', [])
                if district_codes and isinstance(district_codes, list):
                    print(f"  District Codes: {', '.join(district_codes)}")

                # Display district categories (now always a list from array field)
                district_categories = meta.get('district_category', [])
                if district_categories and isinstance(district_categories, list):
                    print(f"  District Categories: {', '.join(district_categories)}")
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
        default="zoning_ordinance_collection",
        help="Collection name to query (default: zoning_ordinance_collection)"
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
        "--no-auto-filter",
        action="store_true",
        help="Disable automatic LLM-based filter extraction (filters will only be applied if manually specified)"
    )

    args = parser.parse_args()

    main(args)
