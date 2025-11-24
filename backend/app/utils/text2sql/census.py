from typing import Optional
import os
import logging
from google import genai
from google.genai import types, errors
import time


class CensusText2SQL:
    """
    Converts natural language queries about census data into SQL queries.
    Uses Google's Gemini model to generate SQL from natural language.
    """

    def __init__(self, gcp_project: str, gcp_region: str):
        self.gcp_project = gcp_project
        self.gcp_region = gcp_region
        self.logger = logging.getLogger(__name__)
        if not self.gcp_project or not self.gcp_region:
            raise ValueError("GCP_PROJECT and GCP_REGION must be set")
        self._init_llm_client()

    def _init_llm_client(self):
        """Initialize Google LLM client for text-to-SQL generation."""
        self.llm_client = genai.Client(
            vertexai=True, project=self.gcp_project, location=self.gcp_region
        )
        # Use Gemini model for text-to-SQL
        self.model = "gemini-1.5-flash"

    def _get_schema_context(self) -> str:
        """
        Returns the database schema context for census tables.
        This helps the LLM understand the database structure.
        """
        return """
        Census Database Schema:
        
        Tables:
        1. census_tracts
           - geoid (VARCHAR, PRIMARY KEY): Census tract geographic identifier
           - geom (GEOMETRY): PostGIS geometry of the tract
           - created_at (TIMESTAMP)
        
        2. acs_table
           - acs_table_id (STRING, PRIMARY KEY): Table identifier (e.g., 'DP04', 'S1901')
           - title (STRING): Table title
           - topic (STRING): Topic category
           - table_type (STRING): Type of table
           - description (STRING): Table description
        
        3. acs_release
           - acs_release_id (STRING, PRIMARY KEY): Release identifier
           - acs_table_id (STRING, FOREIGN KEY): References acs_table.acs_table_id
           - year (INT): Year of the data
           - dataset (STRING): Dataset name (e.g., 'acs/acs5/profile')
           - vintage (STRING): Data vintage
        
        4. acs_variable
           - variable_id (STRING, PRIMARY KEY): Variable identifier
           - acs_table_id (STRING, FOREIGN KEY): References acs_table.acs_table_id
           - name (STRING): Variable name
           - concept (STRING): Variable concept/description
        
        5. acs_value
           - acs_value_id (INT, PRIMARY KEY): Value identifier
           - geoid (VARCHAR, FOREIGN KEY): References census_tracts.geoid
           - acs_release_id (STRING, FOREIGN KEY): References acs_release.acs_release_id
           - variable_id (STRING, FOREIGN KEY): References acs_variable.variable_id
           - value (FLOAT): The actual census value
           - ingested_at (DATETIME): When the data was ingested
        
        Common Query Patterns:
        - To get census values: JOIN acs_value with acs_variable, acs_release, and census_tracts
        - To filter by year: Use acs_release.year
        - To filter by table: Use acs_table.acs_table_id or acs_variable.acs_table_id
        - To filter by location: Use census_tracts.geoid or spatial queries with geom
        - Always use proper JOINs to connect related tables
        """

    def generate_sql(
        self,
        user_query: str,
        max_retries: int = 3,
        retry_delay: int = 2,
    ) -> str:
        """
        Generate SQL query from natural language query.

        Args:
            user_query: Natural language question about census data
            max_retries: Maximum number of retry attempts (default: 3)
            retry_delay: Initial delay in seconds between retries (default: 2)

        Returns:
            SQL query string

        Raises:
            ValueError: If SQL generation fails after all retries
        """
        schema_context = self._get_schema_context()

        prompt = f"""You are a SQL expert. Convert the following natural language query about census data into a valid PostgreSQL SQL query.

{schema_context}

Rules:
1. Generate ONLY the SQL query, no explanations or markdown formatting
2. Use proper JOINs to connect related tables
3. Use meaningful column aliases for clarity
4. Include relevant filters (e.g., year, table type) when appropriate
5. Use proper SQL syntax for PostgreSQL
6. For spatial queries, use PostGIS functions like ST_Contains, ST_Intersects
7. Return results in a readable format with appropriate column names

User Query: {user_query}

SQL Query:"""

        retry_count = 0
        while retry_count <= max_retries:
            try:
                # Generate content using the model
                # The API pattern matches embed_content, so we use generate_content similarly
                response = self.llm_client.models.generate_content(
                    model=self.model,
                    contents=[prompt],  # Contents should be a list
                    config=types.GenerateContentConfig(
                        temperature=0.1,  # Lower temperature for more deterministic SQL
                        max_output_tokens=2048,
                    ),
                )

                # Extract SQL from response
                # Response structure may vary, try common patterns
                if hasattr(response, 'text'):
                    sql_query = response.text.strip()
                elif hasattr(response, 'candidates') and response.candidates:
                    sql_query = response.candidates[0].content.parts[0].text.strip()
                else:
                    # Fallback: convert response to string
                    sql_query = str(response).strip()

                # Remove markdown code blocks if present
                if sql_query.startswith("```sql"):
                    sql_query = sql_query[6:]
                elif sql_query.startswith("```"):
                    sql_query = sql_query[3:]
                if sql_query.endswith("```"):
                    sql_query = sql_query[:-3]
                sql_query = sql_query.strip()

                self.logger.info(f"Generated SQL query: {sql_query[:200]}...")
                return sql_query

            except errors.APIError as e:
                retry_count += 1
                if retry_count > max_retries:
                    error_msg = (
                        f"Failed to generate SQL after {max_retries} attempts. "
                        f"Last error: {str(e)}"
                    )
                    self.logger.error(error_msg)
                    raise ValueError(error_msg)

                # Exponential backoff
                wait_time = retry_delay * (2 ** (retry_count - 1))
                self.logger.warning(
                    f"API error (code: {e.code}): {e.message}. "
                    f"Retrying in {wait_time} seconds (attempt {retry_count}/{max_retries})..."
                )
                time.sleep(wait_time)
            except Exception as e:
                error_msg = f"Unexpected error generating SQL: {str(e)}"
                self.logger.error(error_msg)
                raise ValueError(error_msg)

        raise ValueError("Failed to generate SQL query")

