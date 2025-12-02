"""SQL Agent using Google ADK.

This agent helps users query census data by writing and executing SQL queries
using a set of tools: list_tables, check_schema, check_query, and run_query.
"""

from google.adk.agents import LlmAgent
from app.agents.tools.creators.sql import (
    create_list_tables_tool,
    create_check_schema_tool,
    create_check_query_tool,
    create_run_query_tool,
)
from .prompts import INSTRUCTION, DESCRIPTION


class SQLAgent:
    """Agent for SQL-based census data queries.

    This agent uses Gemini 2.0 Flash to help users write and execute SQL queries
    for census and demographic data. It has access to 4 tools:
    - list_tables: List all available tables
    - check_schema: Get schema for a specific table
    - check_query: Validate a SQL query before execution
    - run_query: Execute a validated SQL query

    Usage:
        agent = SQLAgent()
        llm_agent = agent.create()
    """

    def __init__(
        self,
        model: str = "gemini-2.0-flash",
    ):
        """
        Initialize the SQL agent.

        Args:
            model: Gemini model to use (default: gemini-2.0-flash)
        """
        self.model = model

    def create(self) -> LlmAgent:
        """
        Create the LlmAgent with SQL tools.

        Returns:
            LlmAgent configured for SQL queries
        """
        # Create all SQL tools
        list_tables_tool = create_list_tables_tool()
        check_schema_tool = create_check_schema_tool()
        check_query_tool = create_check_query_tool()
        run_query_tool = create_run_query_tool()

        agent = LlmAgent(
            name="SQLAgent",
            model=self.model,
            instruction=INSTRUCTION,
            tools=[
                list_tables_tool,
                check_schema_tool,
                check_query_tool,
                run_query_tool,
            ],
        )

        return agent

    def get_context(self) -> dict:
        """Get the agent's context for session transfer."""
        return {
            "agent_type": "sql",
        }

