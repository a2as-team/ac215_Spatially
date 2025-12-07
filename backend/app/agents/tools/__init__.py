"""Agent tools for Spatially.

This module provides reusable tools that can be used by various agents.

Structure:
- functions/: Core query functions (one function per file)
  - census/: Census data queries
  - zoning/: Zoning ordinance queries
  - development_plans/: Development plans queries
- creators/: Factory functions that create tools with bound parameters
- formatters/: Result formatting utilities
"""

# Functions - raw query functions
from .functions import (
    # Census
    query_census_data,
    # Zoning
    query_zoning_ordinance,
    query_zoning_by_location,
    query_zoning_by_codes,
    query_zoning_by_geojson,
    get_zoning_codes_at_location,
    # Development plans
    query_development_plans,
    query_development_plans_by_proximity,
    query_development_plans_by_zone,
)

# Creators - factory functions that bind parameters
from .creators import (
    create_census_tool,
    create_location_census_tool,
    create_zoning_tool,
    create_location_zoning_tool,
    create_location_zoning_code_tool,
    create_development_plans_tool,
    create_location_development_plans_proximity_tool,
    create_location_development_plans_zone_tool,
)

# Formatters
from .formatters import (
    format_census_results,
    format_zoning_results,
    format_development_plans_results,
)

# Legacy - keep BaseTool for backwards compatibility
from .base import BaseTool

__all__ = [
    # Base
    "BaseTool",
    # Census functions
    "query_census_data",
    # Zoning functions
    "query_zoning_ordinance",
    "query_zoning_by_location",
    "query_zoning_by_codes",
    "query_zoning_by_geojson",
    "get_zoning_codes_at_location",
    # Development plans functions
    "query_development_plans",
    "query_development_plans_by_proximity",
    "query_development_plans_by_zone",
    # Census creators
    "create_census_tool",
    "create_location_census_tool",
    # Zoning creators
    "create_zoning_tool",
    "create_location_zoning_tool",
    "create_location_zoning_code_tool",
    # Development plans creators
    "create_development_plans_tool",
    "create_location_development_plans_proximity_tool",
    "create_location_development_plans_zone_tool",
    # Formatters
    "format_census_results",
    "format_zoning_results",
    "format_development_plans_results",
]
