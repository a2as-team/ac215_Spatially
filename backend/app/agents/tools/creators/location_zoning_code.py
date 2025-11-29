"""Tool creator for getting exact zoning codes at a location."""

from typing import Callable
from app.agents.tools.functions import get_zoning_codes_at_location


def create_location_zoning_code_tool(
    latitude: float,
    longitude: float,
    city: str,
) -> Callable:
    """
    Create a tool that returns the exact zoning code(s) at a location.

    Args:
        latitude: Latitude coordinate to bind
        longitude: Longitude coordinate to bind
        city: City name to bind

    Returns:
        A callable tool function with location pre-bound
    """

    def get_zoning_code_at_location() -> str:
        """Get the exact zoning code(s) at the configured location."""
        codes = get_zoning_codes_at_location(
            latitude=latitude,
            longitude=longitude,
            city=city,
        )

        if not codes:
            return (
                f"No zoning codes found for location ({latitude}, {longitude}) "
                f"in {city.title()}. The location may be outside zoned areas."
            )

        # Format the zoning codes
        code_list = []
        for item in codes:
            code = item.get("code") or item.get("zone_code") or item.get("zoning_code")
            if code:
                code_list.append(code)

        if not code_list:
            return (
                f"Zoning data found but no code field at location ({latitude}, {longitude}) "
                f"in {city.title()}. Raw data: {codes}"
            )

        codes_str = ", ".join(code_list)
        return (
            f"The exact zoning code(s) at location ({latitude}, {longitude}) "
            f"in {city.title()} is: {codes_str}\n\n"
            f"Use this code to search for specific regulations in the zoning ordinance."
        )

    get_zoning_code_at_location.__name__ = "get_zoning_code_at_location"
    get_zoning_code_at_location.__doc__ = f"""Get the exact zoning code(s) at location ({latitude}, {longitude}) in {city.title()}.

IMPORTANT: Use this tool FIRST to get the exact zoning code (e.g., "H-3-65", "R-1", "MU-10")
before searching the zoning ordinance. This tells you the specific zoning district.

The location has already been set to:
- Latitude: {latitude}
- Longitude: {longitude}
- City: {city.title()}

Returns:
    The exact zoning code(s) that apply to this location from the zoning map.
"""

    return get_zoning_code_at_location
