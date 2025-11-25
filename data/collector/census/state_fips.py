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

def get_fips_code(state_abbr: str) -> str:
    """
    Convert state abbreviation to FIPS code.

    Args:
        state_abbr: Two-letter state abbreviation (e.g., "MA", "IL")

    Returns:
        Two-digit FIPS code (e.g., "25", "17")

    Raises:
        ValueError: If state abbreviation is not recognized
    """
    state_abbr = state_abbr.upper()
    if state_abbr not in STATE_FIPS:
        raise ValueError(
            f"Unknown state abbreviation: {state_abbr}. "
            f"Valid options: {', '.join(sorted(STATE_FIPS.keys()))}"
        )
    return STATE_FIPS[state_abbr]
