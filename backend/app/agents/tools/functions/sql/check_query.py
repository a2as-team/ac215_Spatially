"""Validate a SQL query before execution."""

import logging
import re
from typing import Set, List, Tuple
from app.utils.db_accessor import DBConnector
from app.core.config import settings

logger = logging.getLogger(__name__)


def _extract_table_names(sql_query: str) -> Set[str]:
    """
    Extract table names from a SQL query.
    
    Looks for tables in FROM and JOIN clauses, handling aliases.
    
    Returns:
        Set of table names (without schema prefix, lowercased)
    """
    # Normalize the query - remove comments and extra whitespace
    sql_normalized = re.sub(r'--.*?$', '', sql_query, flags=re.MULTILINE)
    sql_normalized = re.sub(r'/\*.*?\*/', '', sql_normalized, flags=re.DOTALL)
    sql_upper = sql_normalized.upper()
    
    tables = set()
    
    # Extract FROM clause tables
    from_pattern = r'\bFROM\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)?)\s*(?:AS\s+)?([a-zA-Z_][a-zA-Z0-9_]*)?'
    for match in re.finditer(from_pattern, sql_upper):
        table_ref = match.group(1)
        # Remove schema prefix if present
        if '.' in table_ref:
            table_ref = table_ref.split('.')[-1]
        tables.add(table_ref.lower())
    
    # Extract JOIN clause tables
    join_pattern = r'\b(?:INNER|LEFT|RIGHT|FULL|CROSS)?\s*JOIN\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)?)\s*(?:AS\s+)?([a-zA-Z_][a-zA-Z0-9_]*)?'
    for match in re.finditer(join_pattern, sql_upper, re.IGNORECASE):
        table_ref = match.group(1)
        # Remove schema prefix if present
        if '.' in table_ref:
            table_ref = table_ref.split('.')[-1]
        tables.add(table_ref.lower())
    
    return tables


def _extract_column_references(sql_query: str) -> List[Tuple[str, str]]:
    """
    Extract column references from a SQL query.
    
    Returns:
        List of tuples (table_alias_or_name, column_name)
        If no table alias, table name is empty string
    """
    # This is a simplified extraction - looks for pattern table.column
    column_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)\b'
    references = []
    
    for match in re.finditer(column_pattern, sql_query):
        table_ref = match.group(1).lower()
        column_name = match.group(2).lower()
        references.append((table_ref, column_name))
    
    return references


def _validate_tables_exist(db: DBConnector, table_names: Set[str]) -> Tuple[bool, List[str]]:
    """
    Validate that all tables exist in the database.
    
    Returns:
        Tuple of (all_exist: bool, missing_tables: List[str])
    """
    if not table_names:
        return True, []
    
    # Query information_schema to check table existence
    placeholders = ','.join(['%s'] * len(table_names))
    query = f"""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND LOWER(table_name) IN ({placeholders})
    """
    results = db.execute(query, tuple(table_names))
    existing_tables = {row['table_name'].lower() for row in results}
    
    missing = [t for t in table_names if t not in existing_tables]
    return len(missing) == 0, missing


def _validate_columns_exist(db: DBConnector, column_refs: List[Tuple[str, str]], table_aliases: dict) -> Tuple[bool, List[str]]:
    """
    Validate that all column references exist in their tables.
    
    Args:
        db: Database connector
        column_refs: List of (table_ref, column_name) tuples
        table_aliases: Dictionary mapping table aliases to actual table names
    
    Returns:
        Tuple of (all_exist: bool, errors: List[str])
    """
    if not column_refs:
        return True, []
    
    errors = []
    
    # Group columns by table
    table_columns = {}
    for table_ref, column_name in column_refs:
        # Resolve table name from alias if needed
        actual_table = table_aliases.get(table_ref, table_ref)
        if actual_table not in table_columns:
            table_columns[actual_table] = []
        table_columns[actual_table].append(column_name)
    
    # Validate columns for each table
    for table_name, columns in table_columns.items():
        if not table_name:  # Skip if no table reference
            continue
            
        # Check if table exists first
        table_check = db.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND LOWER(table_name) = %s",
            (table_name,)
        )
        if not table_check:
            errors.append(f"Table '{table_name}' does not exist")
            continue
        
        # Check columns exist in this table
        placeholders = ','.join(['%s'] * len(columns))
        column_check = db.execute(
            f"""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
            AND LOWER(table_name) = %s
            AND LOWER(column_name) IN ({placeholders})
            """,
            (table_name, *columns)
        )
        existing_columns = {row['column_name'].lower() for row in column_check}
        missing_columns = [c for c in columns if c not in existing_columns]
        
        if missing_columns:
            errors.append(f"Table '{table_name}' does not have columns: {', '.join(missing_columns)}")
    
    return len(errors) == 0, errors


def check_query(sql_query: str) -> str:
    """
    Validate a SQL query for syntax errors, safety checks, and schema alignment.

    This tool checks if a SQL query is valid before executing it.
    It performs:
    - Safety checks (no DROP, DELETE, TRUNCATE, etc.)
    - Table existence validation
    - Column existence validation
    - Syntax validation using PostgreSQL's EXPLAIN

    Use this tool before running a query to ensure it's safe and valid.

    Args:
        sql_query: The SQL query to validate

    Returns:
        A string indicating whether the query is valid or what errors were found.
    """
    try:
        # Safety checks - prevent destructive operations
        dangerous_keywords = [
            "DROP",
            "DELETE",
            "TRUNCATE",
            "ALTER",
            "CREATE",
            "INSERT",
            "UPDATE",
            "GRANT",
            "REVOKE",
        ]
        sql_upper = sql_query.upper().strip()
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                return (
                    f"Query validation failed: Query contains dangerous keyword '{keyword}'. "
                    "Only SELECT queries are allowed."
                )

        # Must start with SELECT
        if not sql_upper.startswith("SELECT"):
            return (
                "Query validation failed: Query must start with SELECT. "
                "Only SELECT queries are allowed."
            )

        # Validate against database schema
        db = DBConnector(db_name=settings.POSTGRES_DB)
        try:
            # Extract and validate table names
            table_names = _extract_table_names(sql_query)
            if table_names:
                all_tables_exist, missing_tables = _validate_tables_exist(db, table_names)
                if not all_tables_exist:
                    return (
                        f"Query validation failed: The following tables do not exist in the database: "
                        f"{', '.join(missing_tables)}. "
                        f"Use the list_tables tool to see available tables."
                    )
            
            # Extract and validate column references
            # Note: This is a simplified validation - full SQL parsing would be more accurate
            # but this catches common cases
            column_refs = _extract_column_references(sql_query)
            if column_refs:
                # Build table alias map (simplified - assumes FROM/JOIN order)
                table_aliases = {}
                # For now, we'll validate columns against the tables we found
                # A more sophisticated parser would track aliases properly
                for table_name in table_names:
                    table_aliases[table_name] = table_name
                
                all_columns_exist, column_errors = _validate_columns_exist(db, column_refs, table_aliases)
                if not all_columns_exist:
                    return (
                        f"Query validation failed: Schema validation errors:\n" +
                        "\n".join(f"  - {err}" for err in column_errors) +
                        "\nUse the check_schema tool to see the correct column names for each table."
                    )
            
            # Final syntax validation using EXPLAIN
            explain_query = f"EXPLAIN {sql_query}"
            db.execute(explain_query)
            
            # Build success message
            success_msg = "Query validation passed: The SQL query is syntactically correct and safe to execute."
            if table_names:
                success_msg += f" Validated {len(table_names)} table(s): {', '.join(sorted(table_names))}."
            if column_refs:
                success_msg += f" Validated {len(column_refs)} column reference(s)."
            
            return success_msg

        except Exception as e:
            error_msg = str(e)
            # Extract useful error information
            if "syntax error" in error_msg.lower():
                return f"Query validation failed: Syntax error - {error_msg}"
            elif "does not exist" in error_msg.lower():
                # PostgreSQL error messages are usually clear about what doesn't exist
                return f"Query validation failed: {error_msg}"
            else:
                return f"Query validation failed: {error_msg}"

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error validating query: {e}")
        return f"Error validating query: {str(e)}"

