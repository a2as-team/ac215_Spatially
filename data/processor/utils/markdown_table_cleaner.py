"""
Utility to clean up malformed markdown tables.

MarkItDown and other DOCX-to-markdown converters often produce tables with
excessive empty columns when the source document has merged cells or complex
formatting. This module provides utilities to clean up such tables.
"""

import re
from typing import List


def clean_markdown_tables(content: str) -> str:
    """
    Clean up malformed markdown tables in content.

    This function:
    1. Identifies markdown tables
    2. Removes columns that are entirely empty
    3. Preserves the table structure with remaining columns

    Args:
        content: Markdown content potentially containing malformed tables

    Returns:
        Cleaned markdown content with fixed tables
    """
    lines = content.split("\n")
    result_lines = []
    table_buffer: List[str] = []
    in_table = False

    for line in lines:
        stripped = line.strip()

        # Check if this is a table row
        if stripped.startswith("|") and stripped.endswith("|"):
            in_table = True
            table_buffer.append(stripped)
        else:
            # If we were in a table, process it
            if in_table and table_buffer:
                cleaned_table = _clean_table(table_buffer)
                result_lines.extend(cleaned_table)
                table_buffer = []
                in_table = False
            result_lines.append(line)

    # Handle table at end of content
    if table_buffer:
        cleaned_table = _clean_table(table_buffer)
        result_lines.extend(cleaned_table)

    return "\n".join(result_lines)


def _is_separator_row(cells: List[str]) -> bool:
    """Check if a row is a markdown table separator (contains only dashes)."""
    for cell in cells:
        content = cell.strip()
        # Separator cells contain only dashes, colons (for alignment), or are empty
        if content and not all(c in "-:" for c in content):
            return False
    # Must have at least one cell with dashes to be a separator
    return any(cell.strip() and "-" in cell for cell in cells)


def _is_empty_row(cells: List[str]) -> bool:
    """Check if a row is completely empty (no content in any cell)."""
    return all(not cell.strip() for cell in cells)


def _clean_table(table_lines: List[str]) -> List[str]:
    """
    Clean a single markdown table by removing empty columns and empty rows.

    Args:
        table_lines: List of table row strings

    Returns:
        List of cleaned table row strings
    """
    if len(table_lines) < 2:
        return table_lines

    # Parse table into cells and identify separator rows and empty rows
    rows = []
    separator_indices = []
    empty_row_indices = []
    for idx, line in enumerate(table_lines):
        # Split by | and remove first/last empty elements
        cells = line.split("|")[1:-1]
        cells = [cell.strip() for cell in cells]
        rows.append(cells)
        if _is_separator_row(cells):
            separator_indices.append(idx)
        elif _is_empty_row(cells):
            empty_row_indices.append(idx)

    # Find max columns
    max_cols = max(len(row) for row in rows)

    # If table is small, don't modify it
    if max_cols <= 5:
        return table_lines

    # Pad rows to have same number of columns
    for row in rows:
        while len(row) < max_cols:
            row.append("")

    # Track content count per column (excluding separator rows and empty rows)
    col_content_count = [0] * max_cols
    data_row_count = 0

    for idx, row in enumerate(rows):
        if idx in separator_indices or idx in empty_row_indices:
            continue  # Skip separator rows and empty rows when checking for content
        data_row_count += 1
        for i, cell in enumerate(row):
            # Check if cell has meaningful content
            content = cell.strip()
            if content:
                col_content_count[i] += 1

    # Determine which columns to keep based on fill rate
    # Keep columns that have content in at least 10% of data rows
    min_fill_threshold = max(1, int(data_row_count * 0.10))
    col_has_content = [count >= min_fill_threshold for count in col_content_count]

    # Count empty/sparse columns
    sparse_count = sum(1 for has in col_has_content if not has)

    # Clean if ANY sparse columns exist AND table has more than 10 columns
    # (This catches zoning tables which have many sparse columns)
    if sparse_count == 0 or max_cols <= 10:
        return table_lines

    # Filter out empty columns from all rows
    cleaned_rows = []
    for row in rows:
        cleaned_row = [cell for i, cell in enumerate(row) if col_has_content[i]]
        cleaned_rows.append(cleaned_row)

    # Rebuild table lines, skipping completely empty rows and preserving separator rows
    # First, collect all data rows (non-empty, non-separator)
    data_rows = []
    for idx, row in enumerate(cleaned_rows):
        if idx in empty_row_indices:
            continue
        if idx in separator_indices:
            continue  # We'll add separator after first data row
        data_rows.append(row)

    if not data_rows:
        return table_lines  # No data rows found, return original

    # Build result: first data row, then separator, then remaining data rows
    result = []
    num_cols = len(data_rows[0])

    # Add first data row as header
    result.append("| " + " | ".join(data_rows[0]) + " |")

    # Add separator
    result.append("| " + " | ".join(["---"] * num_cols) + " |")

    # Add remaining data rows
    for row in data_rows[1:]:
        result.append("| " + " | ".join(row) + " |")

    return result


def remove_consecutive_empty_cells(content: str) -> str:
    """
    Remove patterns of multiple consecutive empty cells like '| | | | |'.

    This is a simpler approach that just removes obviously malformed patterns.

    Args:
        content: Markdown content

    Returns:
        Content with cleaned table rows
    """
    # Pattern to match multiple consecutive empty cells
    # Matches | followed by any number of | | patterns
    pattern = r'\|(\s*\|\s*){3,}'

    def replacer(match):
        # Keep just one empty cell marker (ignore match content)
        return "| |"

    return re.sub(pattern, replacer, content)


if __name__ == "__main__":
    # Test the cleaner with a simple table
    test_table = """
| DISTRICT | TYPE | | | LOT SIZE | | | HEIGHT | | |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R-1 | Residential | | | 5000 | | | 35 | | |
| B-1 | Business | | | none | | | 40 | | |
"""

    print("Test 1 - Simple table with empty columns:")
    print("Before cleaning:")
    print(test_table)
    print("\nAfter cleaning:")
    print(clean_markdown_tables(test_table))

    # Test with a more realistic zoning table (similar to TABLE E)
    test_table2 = """
| DISTRICT | | | MIN LOT AREA | | | MAX HEIGHT | | | MAX FAR | | | SETBACK FRONT | | | SETBACK SIDE | |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2F-4000 | | | 4000 | | | 35 | | | 0.5 | | | 15 | | | 5 | |
| 2F-5000 | | | 5000 | | | 35 | | | 0.5 | | | 20 | | | 5 | |
| MF-3 | | | 2000 | | | 45 | | | 1.0 | | | 10 | | | 0 | |
"""

    print("\n" + "="*60)
    print("Test 2 - Realistic zoning table:")
    print("Before cleaning:")
    print(test_table2)
    print("\nAfter cleaning:")
    print(clean_markdown_tables(test_table2))
