import os
import chromadb
import argparse

# # Set default environment variables if not already set
# CHROMADB_HOST = os.environ.get("CHROMADB_HOST", "localhost")
# CHROMADB_PORT = int(os.environ.get("CHROMADB_PORT", "8001"))

def get_chromadb_client():
    """Create and return a ChromaDB client using environment variables"""
    chromadb_host = os.environ.get("CHROMADB_HOST", "localhost")
    chromadb_port = int(os.environ.get("CHROMADB_PORT", "8001"))
    return chromadb.HttpClient(host=chromadb_host, port=chromadb_port)

def list_collections():
    """List all collections in ChromaDB"""
    client = get_chromadb_client()
    collections = client.list_collections()

    if not collections:
        print("No collections found.")
        return []

    print(f"\nFound {len(collections)} collection(s):")
    for i, col in enumerate(collections, 1):
        count = col.count()
        print(f"  {i}. {col.name} ({count} items)")

    return collections

def delete_collection(name):
    """Delete a specific collection by name"""
    client = get_chromadb_client()
    try:
        client.delete_collection(name=name)
        print(f"✓ Deleted collection: {name}")
        return True
    except Exception as e:
        print(f"✗ Error deleting collection '{name}': {e}")
        return False

def delete_all_collections():
    """Delete all collections in ChromaDB"""
    client = get_chromadb_client()
    collections = client.list_collections()

    if not collections:
        print("No collections to delete.")
        return

    print(f"\nDeleting {len(collections)} collection(s)...")
    for col in collections:
        delete_collection(col.name)

    print(f"\n✓ All collections deleted.")

def main():
    parser = argparse.ArgumentParser(description="Delete ChromaDB collections")
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all collections"
    )
    parser.add_argument(
        "--delete",
        type=str,
        metavar="COLLECTION_NAME",
        help="Delete a specific collection by name"
    )
    parser.add_argument(
        "--delete-all",
        action="store_true",
        help="Delete all collections (use with caution!)"
    )

    args = parser.parse_args()

    if args.list:
        list_collections()
    elif args.delete:
        delete_collection(args.delete)
    elif args.delete_all:
        confirm = input("Are you sure you want to delete ALL collections? (yes/no): ")
        if confirm.lower() == "yes":
            delete_all_collections()
        else:
            print("Cancelled.")
    else:
        # Default: just list collections
        list_collections()

if __name__ == "__main__":
    main()
