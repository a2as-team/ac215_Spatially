from typing import List, Optional
from app.utils.db_accessor import DBConnector
import logging
import os
from app.utils.embeddor.google_llm_client import GoogleLLMClient
from app.utils.spatial_query.zoning_map import ZoningMapSpatialQuery


class ZoningOrdinanceVectorQuery:
    def __init__(self, db_name):
        self.db = DBConnector(db_name)
        self.logger = logging.getLogger(__name__)
        self.zoning_map_spatial_query = ZoningMapSpatialQuery(db_name)
        self.initialize_embedding_client()

    def initialize_embedding_client(self):
        self.gcp_project = os.environ.get("GCP_PROJECT")
        self.gcp_region = os.environ.get("GCP_REGION")
        if not self.gcp_project or not self.gcp_region:
            raise ValueError("GCP_PROJECT and GCP_REGION must be set")
        self.embedding_client = GoogleLLMClient(
            gcp_project=self.gcp_project,
            gcp_region=self.gcp_region,
        )

    def query(
        self,
        query_text: str,
        city: str,
        top_k: int = 5,
        similarity_threshold: float = 0.0,
        zoning_codes: Optional[List[str]] = None,
        document_title_contains: Optional[str] = None,
    ):
        """
        Query zoning ordinance embeddings using vector similarity search.

        Args:
            query_text: User's query text to search for
            city: City name to filter results (e.g., "boston", "cambridge")
            top_k: Number of top results to return (default: 5)
            similarity_threshold: Minimum similarity score (0-1, default: 0.0)
            zoning_codes: Optional list of zoning codes to filter by
            document_title_contains: Optional string to filter document titles

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
            city_id = self.db.get_city_id(city)
            if city_id is None:
                raise ValueError(f"City '{city}' not found in database")
            query_embeddings = self.embedding_client.generate_text_embeddings(
                query_text
            )
            query_embedding = query_embeddings[0]
            embedding_str = self.db.embedding_to_pgvector(query_embedding)
            # Build dynamic query with filters
            # Note: params must be in order of appearance in the SQL query
            # SELECT clause comes first, then WHERE, then ORDER BY, then LIMIT
            where_conditions = ["city_id = %s", "(1 - (embedding <=> %s::vector)) >= %s"]
            where_params = [city_id, embedding_str, similarity_threshold]
            if zoning_codes:
                where_conditions.append("zoning_codes && %s")
                where_params.append(zoning_codes)
            if document_title_contains:
                where_conditions.append("document_title ILIKE %s")
                where_params.append(f"%{document_title_contains}%")
            where_clause = " AND ".join(where_conditions)

            query = f"""
                SELECT
                    text_chunk,
                    document_title,
                    document_subtitle,
                    zoning_codes,
                    metadata,
                    1 - (embedding <=> %s::vector) AS similarity_score
                FROM zoning_ordinance_embed
                WHERE {where_clause}
                ORDER BY embedding <=> %s::vector
                LIMIT %s;
            """
            # Build params in order: SELECT, WHERE, ORDER BY, LIMIT
            params = [embedding_str] + where_params + [embedding_str, top_k]
            results = self.db.execute(query, tuple(params))

            self.logger.info(
                f"Found {len(results)} results for query in {city} "
                f"(top_k={top_k}, threshold={similarity_threshold})"
            )
            return [dict(row) for row in results]
        except Exception as e:
            self.logger.error(f"Error querying zoning ordinance: {e}")
            raise
        finally:
            self.db.close()

    def query_by_location(
        self,
        query_text: str,
        latitude: float,
        longitude: float,
        city: str,
        top_k: int = 5,
        similarity_threshold: float = 0.0,
    ):
        try:
            zoning_codes = self.zoning_map_spatial_query.get_zoning_by_location(
                latitude=latitude,
                longitude=longitude,
                city=city,
            )
            codes = [zoning_code["code"] for zoning_code in zoning_codes]
            return self.query(
                query_text=query_text,
                city=city,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
                zoning_codes=codes,
            )
        except Exception as e:
            self.logger.error(f"Error querying zoning ordinance by location: {e}")
            raise
