"""Tool creator for SQL agent tools."""

from app.agents.tools.functions.sql import (
    list_tables,
    check_schema,
    check_query,
    run_query,
)


def create_list_tables_tool():
    """Create a tool for listing database tables."""
    return list_tables


def create_check_schema_tool():
    """Create a tool for checking table schemas."""
    return check_schema


def create_check_query_tool():
    """Create a tool for validating SQL queries."""
    return check_query


def create_run_query_tool():
    """Create a tool for executing SQL queries."""
    return run_query

