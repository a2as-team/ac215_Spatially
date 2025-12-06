"""
State abbreviation to FIPS code mapping for Census API.
"""

STATE_FIPS = {
    "AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06",
    "CO": "08", "CT": "09", "DE": "10", "FL": "12", "GA": "13",
    "HI": "15", "ID": "16", "IL": "17", "IN": "18", "IA": "19",
    "KS": "20", "KY": "21", "LA": "22", "ME": "23", "MD": "24",
    "MA": "25", "MI": "26", "MN": "27", "MS": "28", "MO": "29",
    "MT": "30", "NE": "31", "NV": "32", "NH": "33", "NJ": "34",
    "NM": "35", "NY": "36", "NC": "37", "ND": "38", "OH": "39",
    "OK": "40", "OR": "41", "PA": "42", "RI": "44", "SC": "45",
    "SD": "46", "TN": "47", "TX": "48", "UT": "49", "VT": "50",
    "VA": "51", "WA": "53", "WV": "54", "WI": "55", "WY": "56",
    "DC": "11", "PR": "72"
}

# State full name to abbreviation mapping
STATE_NAME_TO_ABBR = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA",
    "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "Florida": "FL", "Georgia": "GA",
    "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA",
    "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO",
    "Montana": "MT", "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ",
    "New Mexico": "NM", "New York": "NY", "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH",
    "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT",
    "Virginia": "VA", "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
    "District of Columbia": "DC", "Puerto Rico": "PR"
}

def normalize_state(state: str) -> str:
    """
    Convert state name to abbreviation.

    Accepts either full state name (e.g., "Massachusetts") or abbreviation (e.g., "MA").
    Returns the two-letter state abbreviation.

    Args:
        state: State name or abbreviation

    Returns:
        Two-letter state abbreviation (e.g., "MA")

    Raises:
        ValueError: If state is not recognized
    """
    # Try as abbreviation first (case-insensitive)
    state_upper = state.upper()
    if state_upper in STATE_FIPS:
        return state_upper

    # Try as full name (case-sensitive for title case)
    if state in STATE_NAME_TO_ABBR:
        return STATE_NAME_TO_ABBR[state]

    # Try case-insensitive full name match
    for name, abbr in STATE_NAME_TO_ABBR.items():
        if name.upper() == state.upper():
            return abbr

    raise ValueError(
        f"Unknown state: {state}. "
        f"Must be a valid state name or abbreviation."
    )

def get_fips_code(state: str) -> str:
    """
    Convert state name or abbreviation to FIPS code.

    Args:
        state: State name (e.g., "Massachusetts") or abbreviation (e.g., "MA")

    Returns:
        Two-digit FIPS code (e.g., "25", "17")

    Raises:
        ValueError: If state is not recognized
    """
    state_abbr = normalize_state(state)
    return STATE_FIPS[state_abbr]
