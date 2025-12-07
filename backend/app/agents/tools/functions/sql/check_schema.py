"""Get schema information for a specific table."""

import logging
from typing import Optional
from app.utils.db_accessor import DBConnector
from app.core.config import settings

logger = logging.getLogger(__name__)


def check_schema(table_name: str) -> str:
    """
    Get the schema (column names, types, constraints) for a specific table.

    Use this tool when you need to understand the structure of a table
    before writing a SQL query. This will show you:
    - Column names
    - Data types
    - Whether columns are nullable
    - Primary keys and foreign keys

    Args:
        table_name: Name of the table to get schema for (e.g., "acs_value", "census_tract")

    Returns:
        A formatted string describing the table schema.
    """
    try:
        db = DBConnector(db_name=settings.POSTGRES_DB)
        try:
            # Get column information
            column_query = """
                SELECT 
                    column_name,
                    data_type,
                    character_maximum_length,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position;
            """
            columns = db.execute(column_query, (table_name,))

            if not columns:
                return f"Table '{table_name}' not found in the database."

            # Get primary key information
            pk_query = """
                SELECT column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.constraint_column_usage ccu
                    ON tc.constraint_name = ccu.constraint_name
                WHERE tc.table_schema = 'public' 
                    AND tc.table_name = %s
                    AND tc.constraint_type = 'PRIMARY KEY';
            """
            pk_columns = db.execute(pk_query, (table_name,))
            primary_keys = [row["column_name"] for row in pk_columns] if pk_columns else []

            # Get foreign key information
            fk_query = """
                SELECT
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                    AND tc.table_schema = 'public'
                    AND tc.table_name = %s;
            """
            fk_columns = db.execute(fk_query, (table_name,))

            # Format the schema information
            lines = [f"Schema for table '{table_name}':\n"]
            lines.append("Columns:")
            for col in columns:
                col_name = col["column_name"]
                data_type = col["data_type"]
                max_length = col.get("character_maximum_length")
                nullable = col["is_nullable"]
                default = col.get("column_default")

                # Format data type
                if max_length:
                    type_str = f"{data_type}({max_length})"
                else:
                    type_str = data_type

                # Add constraints
                constraints = []
                if col_name in primary_keys:
                    constraints.append("PRIMARY KEY")
                if nullable == "NO":
                    constraints.append("NOT NULL")
                if default:
                    constraints.append(f"DEFAULT {default}")

                constraint_str = f" [{', '.join(constraints)}]" if constraints else ""
                lines.append(f"  - {col_name}: {type_str}{constraint_str}")

            # Add foreign key information
            if fk_columns:
                lines.append("\nForeign Keys:")
                for fk in fk_columns:
                    lines.append(
                        f"  - {fk['column_name']} -> {fk['foreign_table_name']}.{fk['foreign_column_name']}"
                    )

            return "\n".join(lines)

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error checking schema: {e}")
        return f"Error checking schema for table '{table_name}': {str(e)}"

