"""List all tables in the database."""

import logging
from app.utils.db_accessor import DBConnector
from app.core.config import settings

logger = logging.getLogger(__name__)


def list_tables() -> str:
    """
    List all tables in the census database.

    This tool returns a list of all available tables that can be queried.
    Use this when you need to know what tables are available in the database.

    Returns:
        A formatted string listing all tables in the database.
    """
    try:
        db = DBConnector(db_name=settings.POSTGRES_DB)
        try:
            # Query PostgreSQL system catalog to get all tables
            query = """
                SELECT table_name, table_schema
                FROM information_schema.tables
                WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
                ORDER BY table_schema, table_name;
            """
            results = db.execute(query)

            if not results:
                return "No tables found in the database."

            # Format results
            tables = []
            for row in results:
                schema = row.get("table_schema", "public")
                table = row.get("table_name", "")
                if schema == "public":
                    tables.append(f"- {table}")
                else:
                    tables.append(f"- {schema}.{table}")

            return f"Available tables in the database:\n" + "\n".join(tables)

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error listing tables: {e}")
        return f"Error listing tables: {str(e)}"

