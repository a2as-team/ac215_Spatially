"""
Centralized city registry for all collectors.

City data is stored in cities.json for easy maintenance.
To add a new city, simply edit cities.json.
"""

import json
from pathlib import Path

# Load cities from JSON file
_CITIES_FILE = Path(__file__).parent / "cities.json"

try:
    with open(_CITIES_FILE, "r") as f:
        CITIES = json.load(f)
except FileNotFoundError:
    raise FileNotFoundError(
        f"cities.json not found at {_CITIES_FILE}. "
        "Please create it with city definitions."
    )


class City:
    """
    City registry with auto-generated constants.

    City data is loaded from cities.json.

    Usage:
        from shared_config.cities import City

        # Use constants (IDE autocomplete!)
        city = City.BOSTON  # "boston"

        # Get display name
        name = City.get_display_name(City.BOSTON)  # "Boston"

        # Validate
        if City.is_valid("boston"):
            ...
    """

    @classmethod
    def get_display_name(cls, city: str) -> str:
        """
        Get display name for a city.

        Args:
            city: City key (e.g., "boston")

        Returns:
            Display name (e.g., "Boston")

        Raises:
            ValueError: If city not found
        """
        if city not in CITIES:
            available = ", ".join(sorted(CITIES.keys()))
            raise ValueError(f"Unknown city '{city}'. Available: {available}")
        return CITIES[city].get("display_name", city.title())

    @classmethod
    def get_all(cls) -> list[str]:
        """Get list of all registered city keys."""
        return sorted(CITIES.keys())

    @classmethod
    def is_valid(cls, city: str) -> bool:
        """Check if a city is registered."""
        return city in CITIES

    @classmethod
    def get_metadata(cls, city: str) -> dict:
        """
        Get full metadata dictionary for a city.

        Args:
            city: City key

        Returns:
            Dictionary with all city metadata

        Raises:
            ValueError: If city not found
        """
        if city not in CITIES:
            available = ", ".join(sorted(CITIES.keys()))
            raise ValueError(f"Unknown city '{city}'. Available: {available}")
        return CITIES[city]

    @classmethod
    def get_state(cls, city: str) -> str | None:
        """
        Get state for a city (if available).

        Args:
            city: City key (e.g., "boston")

        Returns:
            State code (e.g., "MA") or None if not available

        Raises:
            ValueError: If city not found
        """
        if city not in CITIES:
            available = ", ".join(sorted(CITIES.keys()))
            raise ValueError(f"Unknown city '{city}'. Available: {available}")
        return CITIES[city].get("state")


# Auto-generate City.BOSTON, City.CHICAGO, etc. from cities.json
for city_key in CITIES.keys():
    setattr(City, city_key, city_key)