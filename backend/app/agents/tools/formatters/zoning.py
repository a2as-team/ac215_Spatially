"""Formatters for zoning data results."""

from typing import List


def format_zoning_results(results: List[dict], max_results: int = 5) -> str:
    """
    Format zoning query results into readable text.

    Args:
        results: List of result dictionaries from vector search
        max_results: Maximum number of results to display (default: 5)

    Returns:
        Formatted string representation of results
    """
    if not results:
        return "No results found."

    formatted_lines = []
    for i, result in enumerate(results[:max_results], 1):
        text_chunk = result.get("text_chunk", "")
        doc_title = result.get("document_title", "Unknown")
        doc_subtitle = result.get("document_subtitle", "")
        zoning_codes = result.get("zoning_codes", [])
        similarity = result.get("similarity_score", 0)

        # Build header
        header = f"  [{i}] {doc_title}"
        if doc_subtitle:
            header += f" - {doc_subtitle}"
        if zoning_codes:
            header += f" (Zones: {', '.join(zoning_codes)})"
        header += f" [Relevance: {similarity:.2%}]"

        # Truncate text if too long (use higher limit for tables)
        if len(text_chunk) > 2000:
            text_chunk = text_chunk[:2000] + "..."

        formatted_lines.append(header)
        formatted_lines.append(f"     {text_chunk}")
        formatted_lines.append("")  # Empty line between results

    result_text = "\n".join(formatted_lines)
    if len(results) > max_results:
        result_text += f"\n  ... and {len(results) - max_results} more results"

    return result_text


def format_zoning_codes_list(zoning_codes: List[dict]) -> str:
    """
    Format a list of zoning codes found at a location.

    Args:
        zoning_codes: List of zoning code dictionaries with 'code' and optional 'description'

    Returns:
        Formatted string listing the zoning codes
    """
    if not zoning_codes:
        return "No zoning codes found."

    lines = ["Zoning codes at this location:"]
    for code in zoning_codes:
        code_str = code.get("code", "Unknown")
        description = code.get("description", "")
        if description:
            lines.append(f"  - {code_str}: {description}")
        else:
            lines.append(f"  - {code_str}")

    return "\n".join(lines)


def format_zoning_summary(results: List[dict]) -> str:
    """
    Format zoning results as a summary.

    Args:
        results: List of result dictionaries from vector search

    Returns:
        Summary string highlighting key findings
    """
    if not results:
        return "No zoning information found."

    # Collect unique zoning codes
    all_codes = set()
    for result in results:
        codes = result.get("zoning_codes", [])
        all_codes.update(codes)

    # Collect unique document titles
    doc_titles = set()
    for result in results:
        title = result.get("document_title", "")
        if title:
            doc_titles.add(title)

    summary = f"Found {len(results)} relevant passages\n"
    if all_codes:
        summary += f"Zoning codes mentioned: {', '.join(sorted(all_codes))}\n"
    if doc_titles:
        summary += f"Source documents: {', '.join(sorted(doc_titles))}"

    return summary
