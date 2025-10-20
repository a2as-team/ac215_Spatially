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

    print("\nSearching zoning ordinance documents...")
    query_embedding = cli.generate_query_embedding(query)

    # Build query parameters
    query_params = {
        "query_embeddings": [query_embedding],
        "n_results": args.n_results
    }

    # Add city filter if specified
    if args.city:
        query_params["where"] = {"city": args.city}
        print(f"Filtering by city: {args.city}")

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

    args = parser.parse_args()

    main(args)
