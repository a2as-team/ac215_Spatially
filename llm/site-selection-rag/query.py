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
    print("RAG (MDPI LAND)")
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

    print("\nSearching research papers...")
    query_embedding = cli.generate_query_embedding(query)

    # Build query parameters
    query_params = {
        "query_embeddings": [query_embedding],
        "n_results": args.n_results
    }

    # Add category filter if specified
    if args.category:
        query_params["where"] = {"category": args.category}
        print(f"Filtering by category: {args.category}")

    # Search
    results = collection.query(**query_params)

    print(f"Found {len(results['documents'][0])} relevant chunks")

    # Create RAG prompt
    INPUT_PROMPT = f"""
You are an AI assistant specialized in real estate and urban planning, providing research-backed advice for development projects.

Based on the following research excerpts from academic papers, please answer this question:
{query}

Provide specific, actionable insights based on the research findings.

Research excerpts:
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
    print("Sources:")
    print("-" * 50)
    if results['metadatas'] and results['metadatas'][0]:
        # Check if metadata has 'paper' key
        unique_papers = set(meta.get('paper', 'Unknown') for meta in results['metadatas'][0] if meta)
        if unique_papers:
            for paper in sorted(unique_papers):
                print(f"  • {paper}")
        else:
            print("  No source information available")
    else:
        print("  No metadata available")
    print("=" * 50)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Query the RAG system with custom questions")
    parser.add_argument(
        "query",
        type=str,
        help="Your question"
    )
    parser.add_argument(
        "--collection",
        type=str,
        default="mdpiland-semantic-split-collection",
        help="Collection name to query (optional) (default: mdpiland-semantic-split-collection)"
    )
    parser.add_argument(
        "--n-results",
        type=int,
        default=15,
        help="Number of relevant chunks to retrieve (optional) (default: 15)"
    )
    parser.add_argument(
        "--category",
        type=str,
        help="Filter results by category - matches folder name in downloads/mdpi/land (optional)"
    )

    args = parser.parse_args()

    main(args)