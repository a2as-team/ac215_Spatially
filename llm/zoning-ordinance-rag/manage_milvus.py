import os
from pymilvus import MilvusClient
import argparse

def get_milvus_client():
    """Create and return a Milvus client using environment variables"""
    milvus_uri = os.environ.get("MILVUS_PUBLIC_ENDPOINT")
    milvus_token = os.environ.get("MILVUS_API_KEY")

    if not milvus_uri or not milvus_token:
        raise ValueError("MILVUS_PUBLIC_ENDPOINT and MILVUS_API_KEY must be set in environment variables")

    return MilvusClient(uri=milvus_uri, token=milvus_token)

def list_collections():
    """List all collections in Milvus"""
    client = get_milvus_client()
    collections = client.list_collections()

    if not collections:
        print("No collections found.")
        return []

    print(f"\nFound {len(collections)} collection(s):")
    for i, col_name in enumerate(collections, 1):
        stats = client.get_collection_stats(col_name)
        row_count = stats.get('row_count', 'unknown')
        print(f"  {i}. {col_name} ({row_count} items)")

    return collections

def delete_collection(name):
    """Delete a specific collection by name"""
    client = get_milvus_client()
    try:
        client.drop_collection(name)
        print(f"✓ Deleted collection: {name}")
        return True
    except Exception as e:
        print(f"✗ Error deleting collection '{name}': {e}")
        return False

def delete_all_collections():
    """Delete all collections in Milvus"""
    client = get_milvus_client()
    collections = client.list_collections()

    if not collections:
        print("No collections to delete.")
        return

    print(f"\nDeleting {len(collections)} collection(s)...")
    for col_name in collections:
        delete_collection(col_name)

    print(f"\n✓ All collections deleted.")

def main():
    parser = argparse.ArgumentParser(description="Manage Milvus collections")
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
