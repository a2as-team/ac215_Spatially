"""
Simple utility functions for working with pgvector in PostgreSQL.
"""
import hashlib
from typing import List


class PgVectorUtils:
    """Utility functions for pgvector operations."""

    @staticmethod
    def enable_extension(db_accessor):
        """
        Enable pgvector extension in the database.

        Args:
            db_accessor: DBAccessor instance
        """
        db_accessor.connect()
        with db_accessor.conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            db_accessor.conn.commit()

    @staticmethod
    def embedding_to_pgvector(embedding: List[float]) -> str:
        """
        Convert a list of floats to PostgreSQL vector format.

        Args:
            embedding: List of float values

        Returns:
            String in PostgreSQL vector format: '[0.1,0.2,0.3,...]'
        """
        return '[' + ','.join(str(x) for x in embedding) + ']'

    @staticmethod
    def compute_text_hash(text: str) -> str:
        """
        Compute SHA256 hash of text for deduplication.

        Args:
            text: Text content to hash

        Returns:
            SHA256 hash as hexadecimal string
        """
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
