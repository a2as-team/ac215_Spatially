from typing import Any, Dict, List, Optional

from app.utils.db_accessor import DBConnector
from app.utils.embeddor.google_llm_client import GoogleLLMClient
import logging
import os


class DevelopmentPlansVectorQuery:
    """Query development plans embeddings using vector similarity search."""

    def __init__(self, db_name: str):
        self.db = DBConnector(db_name)
        self.logger = logging.getLogger(__name__)
        self.initialize_embedding_client()

    def initialize_embedding_client(self):
        """Initialize the Google Vertex AI embedding client."""
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
        article_reference: Optional[List[str]] = None,
        project_name_contains: Optional[str] = None,
        file_name_contains: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query development plans embeddings using vector similarity search.

        Args:
            query_text: User's query text to search for
            city: City name to filter results (e.g., "boston", "cambridge")
            top_k: Number of top results to return (default: 5)
            similarity_threshold: Minimum similarity score (0-1, default: 0.0)
            article_reference: Optional list of article references to filter by
            project_name_contains: Optional string to filter project names
            file_name_contains: Optional string to filter file names

        Returns:
            List of dictionaries containing:
                - text_chunk: The relevant text chunk
                - project_name: Name of the development project
                - file_name: Source file name
                - zoning_codes: List of zoning codes mentioned (NER-extracted)
                - article_reference: List of article references (NER-extracted)
                - location_context: Location context information (NER-extracted)
                - metadata: Additional metadata including full NER entities
                - similarity_score: Similarity score (0-1, higher is better)

        Raises:
            ValueError: If city not found in database
        """
        try:
            city_id = self.db.get_city_id(city)
            if city_id is None:
                raise ValueError(f"City '{city}' not found in database")

            # Generate query embedding using Vertex AI
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

            # Add optional filters
            if article_reference:
                where_conditions.append("article_reference && %s")
                where_params.append(article_reference)

            if project_name_contains:
                where_conditions.append("project_name ILIKE %s")
                where_params.append(f"%{project_name_contains}%")

            if file_name_contains:
                where_conditions.append("file_name ILIKE %s")
                where_params.append(f"%{file_name_contains}%")

            where_clause = " AND ".join(where_conditions)

            query = f"""
                SELECT
                    text_chunk,
                    project_name,
                    file_name,
                    zoning_codes,
                    article_reference,
                    location_context,
                    metadata,
                    1 - (embedding <=> %s::vector) AS similarity_score
                FROM development_plans_embed
                WHERE {where_clause}
                ORDER BY embedding <=> %s::vector
                LIMIT %s;
            """

            # Build params in order: SELECT, WHERE, ORDER BY, LIMIT
            params = [embedding_str] + where_params + [embedding_str, top_k]
            results = self.db.execute(query, tuple(params))

            self.logger.info(
                f"Found {len(results)} development plan results for query in {city} "
                f"(top_k={top_k}, threshold={similarity_threshold})"
            )
            return [dict(row) for row in results]

        except Exception as e:
            self.logger.error(f"Error querying development plans: {e}")
            raise
        finally:
            self.db.close()

    def get_projects_by_city(self, city: str) -> List[Dict[str, Any]]:
        """
        Get all distinct development projects for a city with metadata.

        Args:
            city: City name to query (e.g., "boston", "cambridge")

        Returns:
            List of dictionaries containing:
                - project_name: Name of the development project
                - file_count: Number of files in the project
                - article_references: Unique article references mentioned across project

        Raises:
            ValueError: If city not found in database
        """
        try:
            city_id = self.db.get_city_id(city)
            if city_id is None:
                raise ValueError(f"City '{city}' not found in database")

            query = """
                WITH flattened AS (
                    SELECT
                        project_name,
                        file_name,
                        unnest(article_reference) as ref
                    FROM development_plans_embed
                    WHERE city_id = %s
                )
                SELECT
                    project_name,
                    COUNT(DISTINCT file_name) as file_count,
                    ARRAY_AGG(DISTINCT ref) FILTER (WHERE ref IS NOT NULL) as article_references
                FROM flattened
                GROUP BY project_name
                ORDER BY project_name;
            """

            results = self.db.execute(query, (city_id,))

            self.logger.info(f"Found {len(results)} projects for city {city}")
            return [dict(row) for row in results]

        except Exception as e:
            self.logger.error(f"Error getting projects for city {city}: {e}")
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
        radius_km: float = 1.0,
    ) -> List[Dict[str, Any]]:
        """
        Query development plans near a specific location using vector similarity search.

        This method filters development plans by proximity to the given coordinates
        using the latitude/longitude stored in the metadata JSONB field.

        Args:
            query_text: User's query text to search for
            latitude: Latitude of the location
            longitude: Longitude of the location
            city: City name to filter results
            top_k: Number of top results to return (default: 5)
            similarity_threshold: Minimum similarity score (0-1, default: 0.0)
            radius_km: Search radius in kilometers (default: 1.0)

        Returns:
            List of dictionaries containing development plan information
            filtered by location proximity

        Raises:
            ValueError: If city not found in database
        """
        try:
            city_id = self.db.get_city_id(city)
            if city_id is None:
                raise ValueError(f"City '{city}' not found in database")

            # Generate query embedding using Vertex AI
            query_embeddings = self.embedding_client.generate_text_embeddings(
                query_text
            )
            query_embedding = query_embeddings[0]
            embedding_str = self.db.embedding_to_pgvector(query_embedding)

            # Calculate approximate lat/lon bounds for the radius
            # 1 degree latitude ≈ 111 km
            # 1 degree longitude ≈ 111 km * cos(latitude)
            import math

            lat_delta = radius_km / 111.0
            lon_delta = radius_km / (111.0 * math.cos(math.radians(latitude)))

            min_lat = latitude - lat_delta
            max_lat = latitude + lat_delta
            min_lon = longitude - lon_delta
            max_lon = longitude + lon_delta

            # Query with location filtering using JSONB metadata
            # Filter by bounding box for performance, then calculate actual distance
            query = """
                WITH filtered_plans AS (
                    SELECT
                        text_chunk,
                        project_name,
                        file_name,
                        zoning_codes,
                        article_reference,
                        location_context,
                        metadata,
                        embedding,
                        CAST(metadata->>'latitude' AS FLOAT) as lat,
                        CAST(metadata->>'longitude' AS FLOAT) as lon
                    FROM development_plans_embed
                    WHERE city_id = %s
                      AND metadata->>'latitude' IS NOT NULL
                      AND metadata->>'longitude' IS NOT NULL
                      AND CAST(metadata->>'latitude' AS FLOAT) BETWEEN %s AND %s
                      AND CAST(metadata->>'longitude' AS FLOAT) BETWEEN %s AND %s
                ),
                with_distance AS (
                    SELECT
                        text_chunk,
                        project_name,
                        file_name,
                        zoning_codes,
                        article_reference,
                        location_context,
                        metadata,
                        1 - (embedding <=> %s::vector) AS similarity_score,
                        -- Haversine distance in km
                        6371 * acos(
                            cos(radians(%s)) * cos(radians(lat)) *
                            cos(radians(lon) - radians(%s)) +
                            sin(radians(%s)) * sin(radians(lat))
                        ) as distance_km
                    FROM filtered_plans
                    WHERE (1 - (embedding <=> %s::vector)) >= %s
                )
                SELECT
                    text_chunk,
                    project_name,
                    file_name,
                    zoning_codes,
                    article_reference,
                    location_context,
                    metadata,
                    similarity_score,
                    distance_km
                FROM with_distance
                WHERE distance_km <= %s
                ORDER BY similarity_score DESC, distance_km ASC
                LIMIT %s;
            """

            params = (
                city_id,
                min_lat,
                max_lat,
                min_lon,
                max_lon,
                embedding_str,
                latitude,
                longitude,
                latitude,
                embedding_str,
                similarity_threshold,
                radius_km,
                top_k,
            )

            results = self.db.execute(query, params)

            self.logger.info(
                f"Found {len(results)} development plans near ({latitude}, {longitude}) "
                f"within {radius_km}km in {city} (top_k={top_k}, threshold={similarity_threshold})"
            )
            return [dict(row) for row in results]

        except Exception as e:
            self.logger.error(f"Error querying development plans by location: {e}")
            raise
        finally:
            self.db.close()

    def query_by_zoning_district(
        self,
        query_text: str,
        latitude: float,
        longitude: float,
        city: str,
        top_k: int = 10,
        similarity_threshold: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """
        Query development plans within the same zoning district as the location.

        This method finds all development plans that fall within the same zoning
        district boundary as the provided coordinates, using spatial containment
        rather than radius-based filtering.

        Args:
            query_text: User's query text to search for
            latitude: Latitude of the location
            longitude: Longitude of the location
            city: City name to filter results
            top_k: Number of top results to return (default: 10)
            similarity_threshold: Minimum similarity score (0-1, default: 0.0)

        Returns:
            List of dictionaries containing development plan information
            filtered by zoning district containment, with _zoning_code added

        Raises:
            ValueError: If city not found in database or no zoning at location
        """
        try:
            from app.utils.spatial_query.zoning_map import ZoningMapSpatialQuery

            city_id = self.db.get_city_id(city)
            if city_id is None:
                raise ValueError(f"City '{city}' not found in database")

            # Get zoning district(s) at the location
            zoning_query = ZoningMapSpatialQuery(db_name=self.db.db_name)
            zoning_data = zoning_query.get_zoning_by_location(
                latitude=latitude,
                longitude=longitude,
                city=city.lower(),
            )

            if not zoning_data:
                raise ValueError(
                    f"No zoning district found at location ({latitude}, {longitude}) in {city}"
                )

            # Extract zoning codes and geometry
            zoning_codes = [z.get("code") for z in zoning_data if z.get("code")]
            if not zoning_codes:
                raise ValueError(
                    f"No valid zoning codes at location ({latitude}, {longitude}) in {city}"
                )

            # Use the first zoning geometry for containment query
            zoning_geom_json = zoning_data[0].get("geometry")
            if not zoning_geom_json:
                raise ValueError("No geometry available for zoning district")

            # Generate query embedding using Vertex AI
            query_embeddings = self.embedding_client.generate_text_embeddings(
                query_text
            )
            query_embedding = query_embeddings[0]
            embedding_str = self.db.embedding_to_pgvector(query_embedding)

            # Query development plans within the zoning district boundary
            # Uses ST_Contains to check if dev plan location is within zoning geometry
            query = """
                WITH zoning_boundary AS (
                    SELECT ST_GeomFromGeoJSON(%s) as geom
                ),
                filtered_plans AS (
                    SELECT
                        dp.text_chunk,
                        dp.project_name,
                        dp.file_name,
                        dp.zoning_codes,
                        dp.article_reference,
                        dp.location_context,
                        dp.metadata,
                        dp.embedding,
                        CAST(dp.metadata->>'latitude' AS FLOAT) as lat,
                        CAST(dp.metadata->>'longitude' AS FLOAT) as lon
                    FROM development_plans_embed dp
                    CROSS JOIN zoning_boundary zb
                    WHERE dp.city_id = %s
                      AND dp.metadata->>'latitude' IS NOT NULL
                      AND dp.metadata->>'longitude' IS NOT NULL
                      AND ST_Contains(
                            zb.geom,
                            ST_SetSRID(
                                ST_MakePoint(
                                    CAST(dp.metadata->>'longitude' AS FLOAT),
                                    CAST(dp.metadata->>'latitude' AS FLOAT)
                                ),
                                4326
                            )
                        )
                )
                SELECT
                    text_chunk,
                    project_name,
                    file_name,
                    zoning_codes,
                    article_reference,
                    location_context,
                    metadata,
                    1 - (embedding <=> %s::vector) AS similarity_score
                FROM filtered_plans
                WHERE (1 - (embedding <=> %s::vector)) >= %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s;
            """

            import json
            geom_json_str = json.dumps(zoning_geom_json)

            params = (
                geom_json_str,
                city_id,
                embedding_str,
                embedding_str,
                similarity_threshold,
                embedding_str,
                top_k,
            )

            results = self.db.execute(query, params)

            # Add zoning code info to results for better formatting
            results_with_zone = []
            for row in results:
                result_dict = dict(row)
                result_dict["_zoning_code"] = zoning_codes[0]
                results_with_zone.append(result_dict)

            self.logger.info(
                f"Found {len(results_with_zone)} development plans in zoning district "
                f"{zoning_codes[0]} at ({latitude}, {longitude}) in {city} "
                f"(top_k={top_k}, threshold={similarity_threshold})"
            )
            return results_with_zone

        except Exception as e:
            self.logger.error(f"Error querying development plans by zoning district: {e}")
            raise
        finally:
            self.db.close()
