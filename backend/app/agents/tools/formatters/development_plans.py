"""Formatters for development plans data results."""

from typing import List


def format_development_plans_results(
    results: List[dict],
    max_results: int = 5,
    include_distance: bool = False,
) -> str:
    """
    Format development plans query results into readable text.

    Args:
        results: List of result dictionaries from vector search
        max_results: Maximum number of results to display (default: 5)
        include_distance: Whether to include distance in output (for proximity queries)

    Returns:
        Formatted string representation of results
    """
    if not results:
        return "No results found."

    formatted_lines = []
    for i, result in enumerate(results[:max_results], 1):
        text_chunk = result.get("text_chunk", "")
        project_name = result.get("project_name", "Unknown Project")
        file_name = result.get("file_name", "")
        article_refs = result.get("article_reference", [])
        zoning_codes = result.get("zoning_codes", [])
        similarity = result.get("similarity_score", 0)
        distance_km = result.get("distance_km")

        # Build header
        header = f"  [{i}] {project_name}"
        if file_name:
            # Shorten file name if too long
            display_file = file_name if len(file_name) <= 40 else file_name[:37] + "..."
            header += f" ({display_file})"

        # Add article references if present
        if article_refs:
            # Limit to first 3 article refs to avoid clutter
            refs_display = ", ".join(article_refs[:3])
            if len(article_refs) > 3:
                refs_display += f", +{len(article_refs) - 3} more"
            header += f" [Articles: {refs_display}]"

        # Add zoning codes if present
        if zoning_codes:
            # Limit to first 2 zoning codes
            codes_display = ", ".join(zoning_codes[:2])
            if len(zoning_codes) > 2:
                codes_display += f", +{len(zoning_codes) - 2} more"
            header += f" [Zones: {codes_display}]"

        # Add distance if available
        if include_distance and distance_km is not None:
            header += f" [{distance_km:.2f}km away]"

        header += f" [Relevance: {similarity:.2%}]"

        # Truncate text if too long
        if len(text_chunk) > 500:
            text_chunk = text_chunk[:500] + "..."

        formatted_lines.append(header)
        formatted_lines.append(f"     {text_chunk}")
        formatted_lines.append("")  # Empty line between results

    result_text = "\n".join(formatted_lines)
    if len(results) > max_results:
        result_text += f"\n  ... and {len(results) - max_results} more results"

    return result_text


def format_development_plans_summary(results: List[dict]) -> str:
    """
    Format development plans results as a summary.

    Args:
        results: List of result dictionaries from vector search

    Returns:
        Summary string highlighting key findings
    """
    if not results:
        return "No development plans found."

    # Collect unique projects
    unique_projects = set()
    for result in results:
        project_name = result.get("project_name")
        if project_name:
            unique_projects.add(project_name)

    # Collect unique article references
    all_articles = set()
    for result in results:
        articles = result.get("article_reference", [])
        all_articles.update(articles)

    # Collect unique zoning codes
    all_codes = set()
    for result in results:
        codes = result.get("zoning_codes", [])
        all_codes.update(codes)

    summary = f"Found {len(results)} relevant passages from {len(unique_projects)} project(s)\n"
    if all_articles:
        summary += f"Article references mentioned: {', '.join(sorted(all_articles)[:5])}\n"
    if all_codes:
        summary += f"Zoning codes mentioned: {', '.join(sorted(all_codes)[:5])}"

    return summary

