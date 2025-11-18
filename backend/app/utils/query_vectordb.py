"""
Utility for querying pgvector database using embeddings.
"""
import os
import logging
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from app.utils.embeddor.google_llm_client import GoogleLLMClient
from app.utils.zoning_map_spatial_query import ZoningMapSpatialQuery

logger = logging.getLogger(__name__)


class VectorDBQuery:
    """Query zoning ordinance embeddings using vector similarity search."""

    def __init__(
        self,
        gcp_project: str,
        gcp_region: str,
        db_name: str | None = None,
        db_user: str | None = None,
        db_password: str | None = None,
        db_host: str | None = None,
        db_port: str | None = None,
    ):
        """
        Initialize VectorDB query client.

        Args:
            gcp_project: GCP project ID for Vertex AI
            gcp_region: GCP region for Vertex AI
            db_name: Database name (defaults to env var APP_DB_NAME)
            db_user: Database user (defaults to env var POSTGRE_USER)
            db_password: Database password (defaults to env var POSTGRE_PASSWORD)
            db_host: Database host (defaults to env var POSTGRE_HOST)
            db_port: Database port (defaults to env var POSTGRE_PORT)
        """
        self.gcp_project = gcp_project
        self.gcp_region = gcp_region

        # Initialize embedding client
        self.embedding_client = GoogleLLMClient(
            gcp_project=gcp_project, gcp_region=gcp_region
        )

        # Database configuration - using same env vars as data processing
        self.db_name = db_name or os.environ.get("APP_DB_NAME")
        self.db_user = db_user or os.environ.get("POSTGRE_USER")
        self.db_password = db_password or os.environ.get("POSTGRE_PASSWORD")
        self.db_host = db_host or os.environ.get("POSTGRE_HOST")
        self.db_port = db_port or os.environ.get("POSTGRE_PORT", "5432")

        if not all([self.db_name, self.db_user, self.db_password, self.db_host]):
            raise ValueError(
                "Database credentials not fully configured. "
                "Please set environment variables: APP_DB_NAME, POSTGRE_USER, "
                "POSTGRE_PASSWORD, POSTGRE_HOST"
            )

        self.conn = None

    def _connect(self):
        """Establish database connection."""
        if self.conn is None or self.conn.closed:
            try:
                self.conn = psycopg2.connect(
                    dbname=self.db_name,
                    user=self.db_user,
                    password=self.db_password,
                    host=self.db_host,
                    port=self.db_port,
                    sslmode='prefer',  # Use SSL if available (required for AWS RDS)
                    cursor_factory=RealDictCursor,  # Return results as dictionaries
                )
                logger.info(f"Connected to database: {self.db_name}")
            except Exception as e:
                logger.error(f"Failed to connect to database: {e}")
                raise
        return self.conn

    def _close(self):
        """Close database connection."""
        if self.conn and not self.conn.closed:
            self.conn.close()
            self.conn = None
            logger.info("Database connection closed")

    def _get_city_id(self, city_name: str) -> Optional[int]:
        """
        Get city_id from city name.

        Args:
            city_name: Name of the city (e.g., "boston", "cambridge")

        Returns:
            City ID or None if not found
        """
        self._connect()
        with self.conn.cursor() as cur:
            cur.execute("SELECT id FROM cities WHERE name = %s", (city_name.lower(),))
            result = cur.fetchone()
            if result:
                return result["id"]
            return None

    def _embedding_to_pgvector(self, embedding: List[float]) -> str:
        """
        Convert embedding list to pgvector format.

        Args:
            embedding: List of float values

        Returns:
            String in PostgreSQL vector format: '[0.1,0.2,0.3,...]'
        """
        return "[" + ",".join(str(x) for x in embedding) + "]"

    def query_zoning_ordinance(
        self,
        query_text: str,
        city: str,
        top_k: int = 5,
        similarity_threshold: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """
        Query zoning ordinance embeddings using vector similarity search.

        Args:
            query_text: User's query text to search for
            city: City name to filter results (e.g., "boston", "cambridge")
            top_k: Number of top results to return (default: 5)
            similarity_threshold: Minimum similarity score (0-1, default: 0.0)
                                Higher values return only more similar results

        Returns:
            List of dictionaries containing:
                - text_chunk: The relevant text chunk
                - document_title: Title of the source document
                - document_subtitle: Subtitle of the source document
                - zoning_codes: List of zoning codes mentioned
                - similarity_score: Similarity score (0-1, higher is better)
                - metadata: Additional metadata

        Raises:
            ValueError: If city not found in database
        """
        try:
            # Get city ID
            city_id = self._get_city_id(city)
            if city_id is None:
                raise ValueError(f"City '{city}' not found in database")

            # Generate embedding for query
            logger.info(f"Generating embedding for query: {query_text[:100]}...")
            query_embeddings = self.embedding_client.generate_text_embeddings(
                query_text
            )
            query_embedding = query_embeddings[0]  # Get first embedding

            # Convert to pgvector format
            embedding_str = self._embedding_to_pgvector(query_embedding)

            # Query database using vector similarity (cosine distance)
            # Lower distance = higher similarity, so we'll convert to similarity score
            self._connect()
            with self.conn.cursor() as cur:
                query = """
                    SELECT
                        text_chunk,
                        document_title,
                        document_subtitle,
                        zoning_codes,
                        metadata,
                        1 - (embedding <=> %s::vector) as similarity_score
                    FROM zoning_ordinance_embed
                    WHERE city_id = %s
                        AND (1 - (embedding <=> %s::vector)) >= %s
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s;
                """
                cur.execute(
                    query,
                    (
                        embedding_str,
                        city_id,
                        embedding_str,
                        similarity_threshold,
                        embedding_str,
                        top_k,
                    ),
                )
                results = cur.fetchall()

            logger.info(
                f"Found {len(results)} results for query in {city} "
                f"(top_k={top_k}, threshold={similarity_threshold})"
            )

            # Convert to list of dicts (RealDictCursor already returns dicts)
            return [dict(row) for row in results]

        except Exception as e:
            logger.error(f"Error querying vector database: {e}")
            raise
        finally:
            self._close()

    def query_with_filters(
        self,
        query_text: str,
        city: str,
        top_k: int = 5,
        similarity_threshold: float = 0.0,
        zoning_codes: Optional[List[str]] = None,
        document_title_contains: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query zoning ordinance with additional filters.

        Args:
            query_text: User's query text to search for
            city: City name to filter results
            top_k: Number of top results to return (default: 5)
            similarity_threshold: Minimum similarity score (0-1, default: 0.0)
            zoning_codes: Optional list of zoning codes to filter by
            document_title_contains: Optional string to filter document titles

        Returns:
            List of matching results with similarity scores
        """
        try:
            # Get city ID
            city_id = self._get_city_id(city)
            if city_id is None:
                raise ValueError(f"City '{city}' not found in database")

            # Generate embedding
            query_embeddings = self.embedding_client.generate_text_embeddings(
                query_text
            )
            query_embedding = query_embeddings[0]
            embedding_str = self._embedding_to_pgvector(query_embedding)

            # Build dynamic query with filters
            conditions = ["city_id = %s", "(1 - (embedding <=> %s::vector)) >= %s"]
            params = [city_id, embedding_str, similarity_threshold]

            if zoning_codes:
                # Check if any of the zoning codes match
                conditions.append("zoning_codes && %s")
                params.append(zoning_codes)

            if document_title_contains:
                conditions.append("document_title ILIKE %s")
                params.append(f"%{document_title_contains}%")

            where_clause = " AND ".join(conditions)

            self._connect()
            with self.conn.cursor() as cur:
                query = f"""
                    SELECT
                        text_chunk,
                        document_title,
                        document_subtitle,
                        zoning_codes,
                        metadata,
                        1 - (embedding <=> %s::vector) as similarity_score
                    FROM zoning_ordinance_embed
                    WHERE {where_clause}
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s;
                """
                # Add embedding_str for similarity calculation and ordering
                cur.execute(query, [embedding_str] + params + [embedding_str, top_k])
                results = cur.fetchall()

            logger.info(f"Found {len(results)} filtered results")
            return [dict(row) for row in results]

        except Exception as e:
            logger.error(f"Error querying with filters: {e}")
            raise
        finally:
            self._close()

    def query_by_location(
        self,
        query_text: str,
        latitude: float,
        longitude: float,
        city: str,
        top_k: int = 5,
        similarity_threshold: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Query zoning ordinance by location (lat/lon).
        First finds zoning codes at the location, then searches ordinances for those codes.

        Args:
            query_text: User's query text to search for
            latitude: Latitude of the location
            longitude: Longitude of the location
            city: City name to filter results
            top_k: Number of top results to return (default: 5)
            similarity_threshold: Minimum similarity score (0-1, default: 0.0)

        Returns:
            Dictionary containing:
                - location: The queried location (lat, lon)
                - zoning_codes: List of zoning codes found at location
                - results: List of matching zoning ordinance chunks
                - count: Number of results returned

        Raises:
            ValueError: If city not found
        """
        try:
            # Use spatial query utility to get zoning codes at location
            with ZoningMapSpatialQuery(
                db_name=self.db_name,
                db_user=self.db_user,
                db_password=self.db_password,
                db_host=self.db_host,
                db_port=self.db_port,
            ) as spatial_query:
                zoning_codes = spatial_query.get_zoning_codes_by_location(
                    latitude=latitude,
                    longitude=longitude,
                    city=city,
                )

            if not zoning_codes:
                return {
                    "location": {"latitude": latitude, "longitude": longitude},
                    "zoning_codes": [],
                    "results": [],
                    "count": 0,
                    "message": f"No zoning codes found at location ({latitude}, {longitude})",
                }

            # Query ordinances filtered by those zoning codes
            results = self.query_with_filters(
                query_text=query_text,
                city=city,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
                zoning_codes=zoning_codes,
            )

            return {
                "location": {"latitude": latitude, "longitude": longitude},
                "zoning_codes": zoning_codes,
                "results": results,
                "count": len(results),
            }

        except Exception as e:
            logger.error(f"Error querying by location: {e}")
            raise

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure connection is closed."""
        self._close()
