"""Query census data filtered by specific geoids."""

from typing import Optional, List
import logging
import asyncio

logger = logging.getLogger(__name__)


def query_census_by_geoids(
    question: str,
    geoids: List[str],
    year: Optional[int] = None,
) -> str:
    """
    Query census data filtered by specific census tract geoids.

    Use this tool when you have a list of census tract IDs and want
    to get demographic data specifically for those tracts.

    Args:
        question: Natural language question about census/demographic data
        geoids: List of census tract geoids to filter by (e.g., ["25025010100", "25025010200"])
        year: Optional year for the ACS data

    Returns:
        A formatted string with the census data results.

    Examples:
        - question: "What is the total population?"
          geoids: ["25025010100", "25025010200"]
    """
    try:
        logger.info(f"Census query by geoids: {question}, geoids: {geoids[:3]}...")

        if not geoids:
            return "No geoids provided. Please specify census tract IDs."

        # Build the query with geoid context
        geoid_list = ", ".join(geoids[:10])  # Show first 10 in context
        if len(geoids) > 10:
            geoid_list += f" and {len(geoids) - 10} more"
        
        query_parts = [question]
        query_parts.append(f"for census tracts with geoids: {geoid_list}")
        if year:
            query_parts.append(f"for year {year}")
        
        full_question = " ".join(query_parts)

        # Use SQL agent to answer the question
        # Lazy import to avoid circular dependency
        from app.agents.sql_agent.runner import SQLAgentRunner
        runner = SQLAgentRunner()
        
        # Run the agent (synchronous wrapper for async function)
        try:
            # Try to get existing event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running, we need to use a different approach
                # Create a new event loop in a thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, runner.run(full_question))
                    response = future.result()
            else:
                response = loop.run_until_complete(runner.run(full_question))
        except RuntimeError:
            # No event loop exists, create one
            response = asyncio.run(runner.run(full_question))
        
        return response

    except Exception as e:
        logger.error(f"Error querying census by geoids: {e}")
        return f"Error querying census data: {str(e)}"
