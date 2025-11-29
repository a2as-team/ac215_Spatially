"""Formatters for census data results."""

from typing import List


def format_census_results(results: List[dict], max_rows: int = 10) -> str:
    """
    Format census query results into readable text.

    Args:
        results: List of result dictionaries from database query
        max_rows: Maximum number of rows to display (default: 10)

    Returns:
        Formatted string representation of results
    """
    if not results:
        return "No results found."

    formatted_lines = []
    for i, row in enumerate(results[:max_rows], 1):
        row_parts = []
        for key, value in row.items():
            if value is not None:
                # Format numbers nicely
                if isinstance(value, float):
                    value = f"{value:,.2f}"
                elif isinstance(value, int):
                    value = f"{value:,}"
                row_parts.append(f"{key}: {value}")
        formatted_lines.append(f"  {i}. " + ", ".join(row_parts))

    result_text = "\n".join(formatted_lines)
    if len(results) > max_rows:
        result_text += f"\n  ... and {len(results) - max_rows} more results"

    return result_text


def format_census_summary(results: List[dict], variable_name: str = None) -> str:
    """
    Format census results as a summary with statistics.

    Args:
        results: List of result dictionaries
        variable_name: Name of the variable being summarized

    Returns:
        Summary string with statistics
    """
    if not results:
        return "No data available for summary."

    # Try to find numeric values to summarize
    numeric_values = []
    for row in results:
        for key, value in row.items():
            if isinstance(value, (int, float)) and value is not None:
                numeric_values.append(value)
                break

    if not numeric_values:
        return format_census_results(results)

    total = sum(numeric_values)
    avg = total / len(numeric_values) if numeric_values else 0
    min_val = min(numeric_values)
    max_val = max(numeric_values)

    summary = f"Summary{' for ' + variable_name if variable_name else ''}:\n"
    summary += f"  Total: {total:,.2f}\n"
    summary += f"  Average: {avg:,.2f}\n"
    summary += f"  Range: {min_val:,.2f} - {max_val:,.2f}\n"
    summary += f"  Count: {len(numeric_values)} records"

    return summary
