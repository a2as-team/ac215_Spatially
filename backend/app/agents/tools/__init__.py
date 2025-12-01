"""Agent tools for Spatially.

This module provides reusable tools that can be used by various agents.

Structure:
- functions/: Core query functions (one function per file)
  - census/: Census data queries
  - zoning/: Zoning ordinance queries
- creators/: Factory functions that create tools with bound parameters
- formatters/: Result formatting utilities
"""

# Functions - raw query functions
from .functions import (
    # Census
    query_census_data,
    query_census_by_geoids,
    query_census_by_geojson,
    # Zoning
    query_zoning_ordinance,
    query_zoning_by_location,
    query_zoning_by_codes,
    query_zoning_by_geojson,
    get_zoning_codes_at_location,
)

# Creators - factory functions that bind parameters
from .creators import (
    create_census_tool,
    create_zoning_tool,
    create_location_zoning_tool,
    create_location_zoning_code_tool,
)

# Formatters
from .formatters import (
    format_census_results,
    format_zoning_results,
)

# Legacy - keep BaseTool for backwards compatibility
from .base import BaseTool

__all__ = [
    # Base
    "BaseTool",
    # Census functions
    "query_census_data",
    "query_census_by_geoids",
    "query_census_by_geojson",
    # Zoning functions
    "query_zoning_ordinance",
    "query_zoning_by_location",
    "query_zoning_by_codes",
    "query_zoning_by_geojson",
    "get_zoning_codes_at_location",
    # Creators
    "create_census_tool",
    "create_zoning_tool",
    "create_location_zoning_tool",
    "create_location_zoning_code_tool",
    # Formatters
    "format_census_results",
    "format_zoning_results",
]
