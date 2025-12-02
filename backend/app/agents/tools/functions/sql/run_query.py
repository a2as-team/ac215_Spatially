"""Execute a SQL query and return results."""

import logging
from typing import Optional
from app.utils.db_accessor import DBConnector
from app.core.config import settings

logger = logging.getLogger(__name__)


def run_query(sql_query: str, limit: Optional[int] = 100) -> str:
    """
    Execute a SQL SELECT query and return the results.

    This tool executes a validated SQL query and returns the results.
    The query should have been validated using check_query first.

    Args:
        sql_query: The SQL SELECT query to execute
        limit: Optional limit on number of rows to return (default: 100, max: 1000)

    Returns:
        A formatted string with the query results or an error message.
    """
    try:
        # Apply safety limit
        if limit is None:
            limit = 100
        limit = min(limit, 1000)  # Max 1000 rows

        # Add LIMIT if not present (for safety)
        sql_upper = sql_query.upper().strip()
        if "LIMIT" not in sql_upper:
            # Try to add LIMIT before any trailing semicolon
            if sql_query.rstrip().endswith(";"):
                sql_query = sql_query.rstrip()[:-1] + f" LIMIT {limit};"
            else:
                sql_query = sql_query.rstrip() + f" LIMIT {limit}"

        db = DBConnector(db_name=settings.POSTGRES_DB)
        try:
            results = db.execute(sql_query)

            if not results:
                return "Query executed successfully but returned no results."

            # Format results
            if len(results) == 0:
                return "Query executed successfully but returned no rows."

            # Get column names from first row
            columns = list(results[0].keys())
            num_rows = len(results)

            # Format as a simple table
            lines = [f"Query executed successfully. Returned {num_rows} row(s):\n"]

            # Header
            header = " | ".join(columns)
            lines.append(header)
            lines.append("-" * len(header))

            # Rows (limit display to first 50 rows for readability)
            display_limit = min(50, num_rows)
            for i, row in enumerate(results[:display_limit]):
                values = [str(row.get(col, "")) for col in columns]
                # Truncate long values
                values = [v[:50] + "..." if len(v) > 50 else v for v in values]
                lines.append(" | ".join(values))

            if num_rows > display_limit:
                lines.append(f"\n... ({num_rows - display_limit} more rows)")

            return "\n".join(lines)

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error executing query: {e}")
        return f"Error executing query: {str(e)}"

