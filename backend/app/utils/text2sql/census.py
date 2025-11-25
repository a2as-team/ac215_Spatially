from typing import Optional
import os
import logging
import time
from langchain_together import ChatTogether


class CensusText2SQL:
    """
    Converts natural language queries about census data into SQL queries.
    Uses LangChain with Together AI (Llama model) for text-to-SQL generation.
    """

    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize Together AI LLM client for text-to-SQL generation.

        Args:
            model_name: Optional model name (default: meta-llama/Llama-3.3-70B-Instruct-Turbo)
        """
        self.logger = logging.getLogger(__name__)
        self.model_name = model_name or "meta-llama/Llama-3.3-70B-Instruct-Turbo"
        self._init_llm_client()

    def _init_llm_client(self):
        """Initialize Together AI LLM client."""
        together_api_key = os.environ.get("TOGETHER_API_KEY")
        if not together_api_key:
            raise ValueError(
                "TOGETHER_API_KEY environment variable must be set. "
                "Add it to secrets/ac215-spatially-project.env"
            )

        self.llm = ChatTogether(
            model=self.model_name,
            temperature=0,  # Lower temperature for more deterministic SQL
            api_key=together_api_key,
        )
        self.logger.info(f"Initialized Together AI LLM with model: {self.model_name}")

    def _get_schema_context(self) -> str:
        """
        Returns the database schema context for census tables.
        This helps the LLM understand the database structure.
        """
        return """
        Census Database Schema:
        
        Tables:
        1. census_tract
           - geoid (VARCHAR, PRIMARY KEY): Census tract geographic identifier
           - geom (GEOMETRY): PostGIS geometry of the tract
           - created_at (TIMESTAMP)
        
        2. acs_table
           - acs_table_id (STRING, PRIMARY KEY): Table identifier (e.g., 'DP04', 'S1901')
           - title (STRING): Table title
           - topic (ENUM): Topic category (DEMOGRAPHICS, HOUSEHOLD_COMPOSITION, HOUSING_STOCK, etc.)
           - table_type (STRING): Type of table
           - description (STRING): Table description
        
        3. acs_variable
           - variable_id (STRING, PRIMARY KEY): Variable identifier
           - acs_table_id (STRING, FOREIGN KEY): References acs_table.acs_table_id
           - name (STRING): Variable name
           - concept (STRING): Variable concept/description
        
        4. acs_value
           - acs_value_id (INT, PRIMARY KEY): Value identifier
           - geoid (VARCHAR, FOREIGN KEY): References census_tract.geoid
           - variable_id (STRING, FOREIGN KEY): References acs_variable.variable_id
           - year (INT): Survey year
           - value (FLOAT): The actual census value
           - ingested_at (DATETIME): When the data was ingested
        
        Alias Conventions (always use these exact aliases):
        - acs_value AS av
        - acs_variable AS avar
        - acs_table AS at
        - census_tract AS ct
        
        Common Query Patterns:
        - To get census values: JOIN acs_value with acs_variable and census_tract
        - To filter by year: Use acs_value.year
        - To filter by table: Use acs_table.acs_table_id or acs_variable.acs_table_id
        - To filter by location: Use census_tract.geoid or spatial queries with geom
        - Always use proper JOINs to connect related tables
        """

    def generate_sql(
        self,
        user_query: str,
        year: Optional[int] = None,
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

        # Format prompt similar to the example provided
        # Include year context if provided
        question_with_year = (
            f"{user_query} (Focus on ACS year {year})" if year is not None else user_query
        )

        prompt = f"""Based on the table schema below, write a SQL query that would answer the user's question; just return the SQL query and nothing else.

Schema:
{schema_context}

Question: {question_with_year}

SQL Query:"""

        retry_count = 0
        while retry_count <= max_retries:
            try:
                # Generate SQL using LangChain's invoke method
                response = self.llm.invoke(prompt)
                
                # Extract SQL from response
                # LangChain ChatTogether returns a message with content attribute
                if hasattr(response, 'content'):
                    sql_query = response.content.strip()
                else:
                    # Fallback: convert to string
                    sql_query = str(response).strip()

                # Remove markdown code blocks if present
                if sql_query.startswith("```sql"):
                    sql_query = sql_query[6:]
                elif sql_query.startswith("```"):
                    sql_query = sql_query[3:]
                if sql_query.endswith("```"):
                    sql_query = sql_query[:-3]
                sql_query = sql_query.strip()

                if not sql_query:
                    raise ValueError("Generated SQL query is empty")

                self.logger.info(f"Generated SQL query: {sql_query[:200]}...")
                return sql_query

            except Exception as e:
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
                    f"Error generating SQL: {str(e)}. "
                    f"Retrying in {wait_time} seconds (attempt {retry_count}/{max_retries})..."
                )
                time.sleep(wait_time)

        raise ValueError("Failed to generate SQL query")
