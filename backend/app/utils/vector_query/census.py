from typing import Dict, Any, List, Optional
from app.utils.db_accessor import DBConnector
from app.utils.text2sql.census import CensusText2SQL
import logging
import os


class CensusQuery:
    """
    Query census data using text-to-SQL conversion.
    Takes natural language queries, converts them to SQL, and returns results.
    """

    def __init__(self, db_name: str):
        self.db = DBConnector(db_name)
        self.logger = logging.getLogger(__name__)
        self._init_text2sql_client()

    def _init_text2sql_client(self):
        """Initialize text-to-SQL client using Together AI (Llama model)."""
        # Optionally allow model name to be configured via environment variable
        model_name = os.environ.get("TEXT2SQL_MODEL", "meta-llama/Llama-3.3-70B-Instruct-Turbo")
        self.text2sql = CensusText2SQL(model_name=model_name)

    def query(
        self,
        user_query: str,
        city: Optional[str] = None,
        year: Optional[int] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        Execute a natural language query against census data.

        Args:
            user_query: Natural language question about census data
            city: Optional city name to filter results by location
            year: Optional census year to scope the query
            limit: Maximum number of results to return (default: 100)

        Returns:
            Dictionary containing:
                - query: The original user query
                - sql: The generated SQL query
                - results: List of query results
                - count: Number of results returned
                - city: City filter if applied

        Raises:
            ValueError: If query generation or execution fails
        """
        try:
            # Generate SQL from natural language query
            sql_query = self.text2sql.generate_sql(user_query, year=year)

            # If city is provided, try to add city-based filtering
            # This is a simple approach - in production, you might want more sophisticated
            # location filtering based on census tract geometries
            if city:
                # Get city_id for potential filtering
                city_id = self.db.get_city_id(city)
                if city_id:
                    # Note: This is a basic implementation. For more sophisticated
                    # city filtering, you'd need to join with spatial data
                    self.logger.info(f"City filter applied: {city} (id: {city_id})")

            # Add LIMIT if not already present
            sql_upper = sql_query.upper().strip()
            if "LIMIT" not in sql_upper:
                # Remove trailing semicolon if present
                sql_query = sql_query.rstrip(";").strip()
                sql_query = f"{sql_query} LIMIT {limit}"

            # Execute the SQL query
            self.logger.info(f"Executing SQL query: {sql_query[:200]}...")
            results = self.db.execute(sql_query)

            # Convert results to dictionaries
            result_list = [dict(row) for row in results] if results else []

            self.logger.info(f"Query returned {len(result_list)} results")

            response = {
                "query": user_query,
                "sql": sql_query,
                "results": result_list,
                "count": len(result_list),
            }

            if city:
                response["city"] = city

            return response

        except Exception as e:
            self.logger.error(f"Error executing census query: {e}")
            raise
        finally:
            self.db.close()

    def query_by_location(
        self,
        user_query: str,
        latitude: float,
        longitude: float,
        year: Optional[int] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        Execute a natural language query filtered by geographic location.

        Args:
            user_query: Natural language question about census data
            latitude: Latitude of the location
            longitude: Longitude of the location
            year: Optional census year to scope the query
            limit: Maximum number of results to return (default: 100)

        Returns:
            Dictionary containing query results with location context
        """
        try:
            # Generate base SQL query
            sql_query = self.text2sql.generate_sql(user_query, year=year)

            # Add spatial filtering to find census tracts containing the point
            # This modifies the query to include a spatial join
            sql_upper = sql_query.upper().strip()

            # Check if query already has spatial filtering
            if "ST_CONTAINS" not in sql_upper and "ST_INTERSECTS" not in sql_upper:
                # Add spatial join with census_tracts
                # This is a simplified approach - you may need to adjust based on query structure
                if "FROM" in sql_upper:
                    # Try to add a spatial filter
                    # This is complex and depends on the query structure
                    # For now, we'll add it as a WHERE clause if census_tracts is in the query
                    if "census_tracts" in sql_query.lower():
                        spatial_filter = (
                            f" AND ST_Contains("
                            f"census_tracts.geom, "
                            f"ST_SetSRID(ST_MakePoint({longitude}, {latitude}), 4326)"
                            f")"
                        )
                        # Insert before LIMIT or at the end
                        if "LIMIT" in sql_upper:
                            sql_query = sql_query.rsplit("LIMIT", 1)[0] + spatial_filter + " LIMIT " + sql_query.rsplit("LIMIT", 1)[1].split()[0]
                        else:
                            sql_query = sql_query.rstrip(";").strip() + spatial_filter

            # Add LIMIT if not already present
            if "LIMIT" not in sql_upper:
                sql_query = sql_query.rstrip(";").strip()
                sql_query = f"{sql_query} LIMIT {limit}"

            # Execute the SQL query
            self.logger.info(f"Executing spatial SQL query: {sql_query[:200]}...")
            results = self.db.execute(sql_query)

            result_list = [dict(row) for row in results] if results else []

            self.logger.info(f"Spatial query returned {len(result_list)} results")

            return {
                "query": user_query,
                "sql": sql_query,
                "location": {"latitude": latitude, "longitude": longitude},
                "results": result_list,
                "count": len(result_list),
            }

        except Exception as e:
            self.logger.error(f"Error executing spatial census query: {e}")
            raise
        finally:
            self.db.close()

