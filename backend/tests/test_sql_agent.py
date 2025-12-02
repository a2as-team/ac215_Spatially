"""Tests for SQLAgent and SQLAgentRunner."""

import pytest
from app.agents.sql_agent import SQLAgent, SQLAgentRunner
from app.agents.tools.functions.sql import (
    list_tables,
    check_schema,
    check_query,
    run_query,
)


class TestSQLAgent:
    """Tests for SQLAgent."""

    def test_init(self):
        """Test agent initialization."""
        agent = SQLAgent()
        assert agent.model == "gemini-2.0-flash"

    def test_init_custom_model(self):
        """Test agent initialization with custom model."""
        agent = SQLAgent(model="gemini-1.5-pro")
        assert agent.model == "gemini-1.5-pro"

    def test_create_returns_llm_agent(self):
        """Test that create() returns an LlmAgent."""
        agent = SQLAgent()
        llm_agent = agent.create()
        assert llm_agent is not None
        assert llm_agent.name == "SQLAgent"

    def test_get_context(self):
        """Test get_context returns correct data."""
        agent = SQLAgent()
        context = agent.get_context()
        assert context["agent_type"] == "sql"


class TestSQLTools:
    """Tests for SQL tool functions."""

    def test_list_tables(self):
        """Test list_tables tool returns table names."""
        result = list_tables()
        assert isinstance(result, str)
        assert len(result) > 0
        # Should contain common tables
        assert "census_tract" in result or "acs_value" in result or "tables" in result.lower()

    def test_check_schema_existing_table(self):
        """Test check_schema for an existing table."""
        # Test with a common table that should exist
        result = check_schema("census_tract")
        assert isinstance(result, str)
        assert len(result) > 0
        assert "census_tract" in result.lower() or "schema" in result.lower()

    def test_check_schema_nonexistent_table(self):
        """Test check_schema for a non-existent table."""
        result = check_schema("nonexistent_table_xyz")
        assert isinstance(result, str)
        assert "not found" in result.lower() or "error" in result.lower()

    def test_check_query_valid_select(self):
        """Test check_query with a valid SELECT query."""
        query = "SELECT * FROM census_tract LIMIT 1"
        result = check_query(query)
        assert isinstance(result, str)
        assert "validation passed" in result.lower() or "correct" in result.lower()

    def test_check_query_invalid_syntax(self):
        """Test check_query with invalid SQL syntax."""
        query = "SELECT * FROM nonexistent_table WHERE invalid_column ="
        result = check_query(query)
        assert isinstance(result, str)
        assert "validation failed" in result.lower() or "error" in result.lower()

    def test_check_query_dangerous_keyword(self):
        """Test check_query rejects dangerous operations."""
        dangerous_queries = [
            "DROP TABLE census_tract",
            "DELETE FROM census_tract",
            "TRUNCATE TABLE census_tract",
            "ALTER TABLE census_tract",
        ]
        for query in dangerous_queries:
            result = check_query(query)
            assert isinstance(result, str)
            assert "validation failed" in result.lower() or "dangerous" in result.lower()

    def test_check_query_non_select(self):
        """Test check_query rejects non-SELECT queries."""
        query = "INSERT INTO census_tract VALUES (1, 'test')"
        result = check_query(query)
        assert isinstance(result, str)
        assert "validation failed" in result.lower() or "select" in result.lower()

    def test_run_query_valid(self):
        """Test run_query with a valid query."""
        query = "SELECT COUNT(*) as count FROM census_tract LIMIT 1"
        result = run_query(query)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_run_query_with_limit(self):
        """Test run_query respects limit parameter."""
        query = "SELECT * FROM census_tract"
        result = run_query(query, limit=5)
        assert isinstance(result, str)
        # Should not return more than 5 rows (plus header)
        lines = result.split("\n")
        # Account for header and separator lines
        data_lines = [l for l in lines if l and not l.startswith("-") and "|" in l]
        assert len(data_lines) <= 5


class TestSQLAgentRunner:
    """Tests for SQLAgentRunner."""

    def test_init(self):
        """Test runner initialization."""
        runner = SQLAgentRunner()
        assert runner.model == "gemini-2.0-flash"
        assert runner.session_id is not None
        assert runner.user_id is not None
        assert runner.app_name == "sql-agent"

    def test_init_custom_session(self):
        """Test runner initialization with custom session ID."""
        session_id = "test-session-123"
        runner = SQLAgentRunner(session_id=session_id)
        assert runner.session_id == session_id

    def test_init_custom_model(self):
        """Test runner initialization with custom model."""
        runner = SQLAgentRunner(model="gemini-1.5-pro")
        assert runner.model == "gemini-1.5-pro"

    def test_get_history_empty(self):
        """Test get_history returns empty list initially."""
        runner = SQLAgentRunner()
        history = runner.get_history()
        assert isinstance(history, list)
        assert len(history) == 0

    def test_clear_history(self):
        """Test clear_history clears the history."""
        runner = SQLAgentRunner()
        # History should be empty initially
        assert len(runner.get_history()) == 0
        # Clear should still work
        runner.clear_history()
        assert len(runner.get_history()) == 0


@pytest.mark.asyncio
class TestSQLAgentRunnerAsync:
    """Async tests for SQLAgentRunner."""

    async def test_run_returns_response(self):
        """Test that run() returns a response string."""
        runner = SQLAgentRunner()

        question = "List all tables in the database"
        response = await runner.run(question)

        print("\n" + "=" * 60)
        print(f"QUESTION: {question}")
        print("=" * 60)
        print("RESPONSE:")
        print(response)
        print("=" * 60 + "\n")

        assert isinstance(response, str)
        assert len(response) > 0
        # Check history was updated
        history = runner.get_history()
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"

    async def test_run_simple_query(self):
        """Test running a simple SQL query question."""
        runner = SQLAgentRunner()

        question = "What tables are in the database?"
        response = await runner.run(question)

        print("\n" + "=" * 60)
        print(f"QUESTION: {question}")
        print("=" * 60)
        print("RESPONSE:")
        print(response)
        print("=" * 60 + "\n")

        assert isinstance(response, str)
        assert len(response) > 0

    async def test_run_schema_query(self):
        """Test querying about table schema."""
        runner = SQLAgentRunner()

        question = "What is the schema of the census_tract table?"
        response = await runner.run(question)

        print("\n" + "=" * 60)
        print(f"QUESTION: {question}")
        print("=" * 60)
        print("RESPONSE:")
        print(response)
        print("=" * 60 + "\n")

        assert isinstance(response, str)
        assert len(response) > 0

    async def test_run_census_query(self):
        """Test querying census data through SQL agent."""
        runner = SQLAgentRunner()

        question = "What is the total number of census tracts in the database?"
        response = await runner.run(question)

        print("\n" + "=" * 60)
        print(f"QUESTION: {question}")
        print("=" * 60)
        print("RESPONSE:")
        print(response)
        print("=" * 60 + "\n")

        assert isinstance(response, str)
        assert len(response) > 0

    async def test_run_complex_query(self):
        """Test running a more complex query."""
        runner = SQLAgentRunner()

        question = "Show me the first 5 census tracts with their geoids"
        response = await runner.run(question)

        print("\n" + "=" * 60)
        print(f"QUESTION: {question}")
        print("=" * 60)
        print("RESPONSE:")
        print(response)
        print("=" * 60 + "\n")

        assert isinstance(response, str)
        assert len(response) > 0

    async def test_run_stream(self):
        """Test streaming response."""
        runner = SQLAgentRunner()

        question = "List the tables in the database"
        chunks = []
        async for chunk in runner.run_stream(question):
            chunks.append(chunk)

        full_response = "".join(chunks)

        print("\n" + "=" * 60)
        print(f"QUESTION (streamed): {question}")
        print("=" * 60)
        print("RESPONSE:")
        print(full_response)
        print("=" * 60 + "\n")

        assert len(chunks) > 0
        assert isinstance(full_response, str)
        assert len(full_response) > 0

    async def test_conversation_history(self):
        """Test that conversation history is maintained."""
        runner = SQLAgentRunner()

        # First question
        question1 = "What tables are in the database?"
        response1 = await runner.run(question1)

        # Check history after first question
        history = runner.get_history()
        assert len(history) == 2
        assert history[0]["content"] == question1
        assert history[1]["role"] == "assistant"

        # Second question (should have context)
        question2 = "What is the schema of the first table you mentioned?"
        response2 = await runner.run(question2)

        # Check history after second question
        history = runner.get_history()
        assert len(history) == 4
        assert history[2]["content"] == question2
        assert history[3]["role"] == "assistant"

        print("\n" + "=" * 60)
        print("CONVERSATION HISTORY TEST:")
        print("=" * 60)
        print(f"Q1: {question1}")
        print(f"A1: {response1[:200]}...")
        print(f"\nQ2: {question2}")
        print(f"A2: {response2[:200]}...")
        print("=" * 60 + "\n")

    async def test_census_data_query(self):
        """Test querying census data through SQL agent."""
        runner = SQLAgentRunner()

        question = "How many census tracts are there in the database?"
        response = await runner.run(question)

        print("\n" + "=" * 60)
        print(f"QUESTION (census data): {question}")
        print("=" * 60)
        print("RESPONSE:")
        print(response)
        print("=" * 60 + "\n")

        assert isinstance(response, str)
        assert len(response) > 0

    async def test_acs_table_query(self):
        """Test querying ACS table information."""
        runner = SQLAgentRunner()

        question = "What ACS tables are available in the database?"
        response = await runner.run(question)

        print("\n" + "=" * 60)
        print(f"QUESTION (ACS tables): {question}")
        print("=" * 60)
        print("RESPONSE:")
        print(response)
        print("=" * 60 + "\n")

        assert isinstance(response, str)
        assert len(response) > 0

    async def test_query_with_validation(self):
        """Test that the agent validates queries before running them."""
        runner = SQLAgentRunner()

        # This should trigger the agent to use check_query before run_query
        question = "Show me all columns from the census_tract table"
        response = await runner.run(question)

        print("\n" + "=" * 60)
        print(f"QUESTION (with validation): {question}")
        print("=" * 60)
        print("RESPONSE:")
        print(response)
        print("=" * 60 + "\n")

        assert isinstance(response, str)
        assert len(response) > 0

    async def test_error_handling(self):
        """Test error handling for invalid queries."""
        runner = SQLAgentRunner()

        # Ask about a table that might not exist
        question = "Show me data from a table called nonexistent_table_xyz"
        response = await runner.run(question)

        print("\n" + "=" * 60)
        print(f"QUESTION (error case): {question}")
        print("=" * 60)
        print("RESPONSE:")
        print(response)
        print("=" * 60 + "\n")

        assert isinstance(response, str)
        # Should either find the table doesn't exist or handle gracefully
        assert len(response) > 0

