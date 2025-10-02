import os
import re

# Expected sections from desc.txt (excluding the 5 that should NOT be downloaded)
EXPECTED_SECTIONS = [
    "Enabling Act - CHAPTER 665 OF THE ACTS OF 1956",
    "ARTICLE 1 - TITLE, PURPOSE AND SCOPE",
    "ARTICLE 2 - DEFINITIONS",
    "ARTICLE 3 - ESTABLISHMENT OF ZONING DISTRICTS",
    "ARTICLE 4 - APPLICATION OF REGULATIONS",
    "ARTICLE 5 - ADMINISTRATION AND PROCEDURE",
    "ARTICLE 6 - CONDITIONAL USES",
    "ARTICLE 6A - OTHER EXCEPTIONS",
    "ARTICLE 7 - VARIANCES",
    "ARTICLE 8 - REGULATION OF USES",
    "ARTICLE 9 - NONCONFORMING USES",
    "ARTICLE 11 - SIGNS",
    "ARTICLE 11 - APPENDIX",
    "ARTICLE 12 - TRANSITION ZONING",
    "ARTICLE 13 - DIMENSIONAL REQUIREMENTS",
    "ARTICLE 13 - TABLES",
    "ARTICLE 14 - LOT SIZE, AREA AND WIDTH",
    "ARTICLE 15 - BUILDING BULK",
    "ARTICLE 16 - HEIGHT OF BUILDINGS",
    "ARTICLE 17 - OPEN SPACE REQUIREMENT FOR RESIDENCES",
    "ARTICLE 18 - FRONT YARDS",
    "ARTICLE 19 - SIDE YARDS",
    "ARTICLE 20 - REAR YARDS",
    "ARTICLE 21 - SETBACKS",
    "ARTICLE 22 - YARD REGULATIONS",
    "ARTICLE 23 - OFF-STREET PARKING",
    "ARTICLE 24 - OFF-STREET LOADING",
    "ARTICLE 25 - FLOOD HAZARD DISTRICTS",
    "ARTICLE 25A - COASTAL FLOOD RESILIENCE OVERLAY DISTRICT",
    "ARTICLE 26 - SQUARES + STREETS DISTRICTS",
    "ARTICLE 27 - INTERIM PLANNING OVERLAY DISTRICT",
    "ARTICLE 28 - DESIGN REVIEW",
    "ARTICLE 29 - GREENBELT PROTECTION OVERLAY DISTRICT",
    "ARTICLE 30 - BARRIER-FREE ACCESS",
    "ARTICLE 32 - GROUNDWATER CONSERVATION OVERLAY DISTRICT",
    "ARTICLE 32 - APPENDIX",
    "ARTICLE 33 - OPEN SPACE SUBDISTRICTS",
    "ARTICLE 36 - LIGHT MANUFACTURING DISTRICT",
    "ARTICLE 37 - GREEN BUILDINGS AND NET ZERO CARBON",
    "ARTICLE 37 - APPENDIX",
    "ARTICLE 38 - MIDTOWN CULTURAL DISTRICT",
    "ARTICLE 38 - APPENDICES",
    "ARTICLE 39 - NORTH STATION ECONOMIC DEVELOPMENT AREA",
    "APPENDICES to ARTICLE 39",
    "ARTICLE 40 - SOUTH STATION ECONOMIC DEVELOPMENT AREA",
    "ARTICLE 40 - APPENDICES",
    "ARTICLE 41 - HUNTINGTON AVENUE/PRUDENTIAL CENTER DISTRICT",
    "ARTICLE 41 - APPENDICES",
    "ARTICLE 42A - HARBORPARK DISTRICT, NORTH END/DOWNTOWN WATERFRONT AND, DORCHESTER BAY/NEPONSET RIVER WATERFRONT",
    "ARTICLE 42A - APPENDICES",
    "ARTICLE 42B - HARBORPARK DISTRICT - CHARLESTOWN WATERFRONT",
    "ARTICLE 42C - WATERFRONT SERVICE DISTRICT",
    "ARTICLE 42D - WATERFRONT MANUFACTURING DISTRICT",
    "ARTICLE 42E - HARBORPARK DISTRICT - FORT POINT WATERFRONT",
    "ARTICLE 42E - APPENDICES",
    "ARTICLE 42F - HARBORPARK DISTRICT - CHARLESTOWN NAVY YARD",
    "ARTICLE 42F - APPENDICES",
    "ARTICLE 43 - CHINATOWN DISTRICT",
    "ARTICLE 43 - APPENDICES",
    "ARTICLE 44 - LEATHER DISTRICT",
    "ARTICLE 44 - APPENDICES",
    "ARTICLE 45 - GOVERNMENT CENTER/MARKETS DISTRICT",
    "ARTICLE 45 - APPENDICES",
    "ARTICLE 46 - BULFINCH TRIANGLE DISTRICT",
    "ARTICLE 46 - APPENDICES",
    "ARTICLE 47A - CAMBRIDGE STREET NORTH DISTRICT",
    "ARTICLE 47A - APPENDICES",
    "ARTICLE 48 - STUART STREET DISTRICT",
    "ARTICLE 48 - APPENDIX",
    "ARTICLE 49 - CENTRAL ARTERY SPECIAL DISTRICT",
    "ARTICLE 49 - APPENDIX",
    "ARTICLE 49A - GREENWAY OVERLAY DISTRICT",
    "ARTICLE 49A - APPENDICES",
    "ARTICLE 50 - ROXBURY NEIGHBORHOOD DISTRICT",
    "ARTICLE 50 - TABLES",
    "ARTICLE 51 - ALLSTON-BRIGHTON NEIGHBORHOOD DISTRICT",
    "ARTICLE 51 - APPENDIX",
    "ARTICLE 51 - TABLES",
    "ARTICLE 53 - EAST BOSTON NEIGHBORHOOD DISTRICT",
    "ARTICLE 53 - APPENDIX",
    "ARTICLE 53 - TABLES",
    "ARTICLE 54 - NORTH END NEIGHBORHOOD DISTRICT",
    "ARTICLE 54 - TABLES",
    "ARTICLE 55 - JAMAICA PLAIN NEIGHBORHOOD DISTRICT",
    "ARTICLE 55 - APPENDIX",
    "ARTICLE 55 - TABLES",
    "ARTICLE 56 - WEST ROXBURY NEIGHBORHOOD DISTRICT",
    "ARTICLE 56 - TABLES",
    "ARTICLE 59 - MISSION HILL NEIGHBORHOOD DISTRICT",
    "ARTICLE 59 - APPENDIX",
    "ARTICLE 59 - TABLES",
    "ARTICLE 60. - GREATER MATTAPAN NEIGHBORHOOD DISTRICT",
    "ARTICLE 60 - TABLES",
    "ARTICLE 61 - AUDUBON CIRCLE NEIGHBORHOOD DISTRICT",
    "ARTICLE 61 - APPENDIX",
    "ARTICLE 61 - TABLES",
    "ARTICLE 62 - CHARLESTOWN NEIGHBORHOOD DISTRICT",
    "ARTICLE 62 - TABLES",
    "ARTICLE 63 - BAY VILLAGE NEIGHBORHOOD DISTRICT",
    "ARTICLE 63 - TABLES",
    "ARTICLE 64 - SOUTH END NEIGHBORHOOD DISTRICT",
    "ARTICLE 64 - APPENDIX",
    "ARTICLE 64 - TABLES",
    "ARTICLE 65 - DORCHESTER NEIGHBORHOOD DISTRICT",
    "ARTICLE 65 - TABLES",
    "ARTICLE 66 - FENWAY NEIGHBORHOOD DISTRICT",
    "ARTICLE 66 - TABLES",
    "ARTICLE 67 - ROSLINDALE NEIGHBORHOOD DISTRICT",
    "ARTICLE 67 - APPENDIX",
    "ARTICLE 67 - TABLES",
    "ARTICLE 68 - SOUTH BOSTON NEIGHBORHOOD DISTRICT",
    "ARTICLE 68 - TABLES",
    "ARTICLE 69 - HYDE PARK NEIGHBORHOOD DISTRICT",
    "ARTICLE 69 - APPENDIX",
    "ARTICLE 69 - TABLES",
    "ARTICLE 70 - BETH ISRAEL DEACONESS MEDICAL CENTER INSTITUTIONAL DISTRICT EAST",
    "ARTICLE 70 - APPENDIX",
    "ARTICLE 70 - TABLES",
    "ARTICLE 71 - MASSACHUSETTS COLLEGE OF PHARMACY INSTITUTIONAL DISTRICT",
    "ARTICLE 71 - TABLES",
    "ARTICLE 72 - NEW ENGLAND DEACONESS HOSPITAL INSTITUTIONAL DISTRICT",
    "ARTICLE 72 - TABLES",
    "ARTICLE 73 - DANA-FARBER CANCER INSTITUTE INSTITUTIONAL DISTRICT",
    "ARTICLE 73 - TABLES",
    "Article 79 - INCLUSIONARY ZONING",
    "ARTICLE 80 - DEVELOPMENT REVIEW AND APPROVAL",
    "ARTICLE 80 - APPENDICES",
    "ARTICLE 81 - BOSTON CIVIC DESIGN COMMISSION",
    "ARTICLE 85 - DEMOLITION DELAY",
    "ARTICLE 86 - WIRELESS COMMUNICATIONS EQUIPMENT",
    "ARTICLE 87 - SMART GROWTH OVERLAY DISTRICTS",
    "ARTICLE 87 - APPENDIX",
    "ARTICLE 87A - OLMSTED GREEN SMART GROWTH OVERLAY DISTRICT",
    "ARTICLE 88 - WIND ENERGY FACILITIES",
    "ARTICLE 89 - URBAN AGRICULTURE",
    "ARTICLE 89 - APPENDIX",
    "ARTICLE 90 - NEWMARKET 21ST CENTURY INDUSTRIAL DISTRICT",
    "ARTICLE 90 - TABLES",
    "APPENDICES TO ZONING CODE",
]

def normalize_filename(section_name):
    """Convert section name to expected filename format."""
    # Sanitize the section name
    safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in section_name)
    safe_name = safe_name.strip().replace(' ', '_')
    return f"{safe_name}.xlsx"

def get_downloaded_files(directory):
    """Get list of downloaded .xlsx files."""
    files = []
    for f in os.listdir(directory):
        if f.endswith('.xlsx') and not f.startswith('~$') and not f.startswith('BostonMA'):
            files.append(f)
    return set(files)

if __name__ == "__main__":
    download_dir = os.path.join(os.path.dirname(__file__), "collected_data")

    # Get downloaded files
    downloaded_files = get_downloaded_files(download_dir)

    # Build expected filenames
    expected_filenames = set()
    for section in EXPECTED_SECTIONS:
        expected_filenames.add(normalize_filename(section))

    print("=" * 80)
    print("FILE VERIFICATION REPORT")
    print("=" * 80)
    print(f"\nTotal expected sections: {len(EXPECTED_SECTIONS)}")
    print(f"Total downloaded files (excluding temp/export files): {len(downloaded_files)}")
    print()

    # Find missing files
    missing = []
    for section in EXPECTED_SECTIONS:
        expected_file = normalize_filename(section)
        if expected_file not in downloaded_files:
            missing.append((section, expected_file))

    if missing:
        print(f"MISSING FILES: {len(missing)}")
        print("-" * 80)
        for section, filename in missing:
            print(f"  Section: {section}")
            print(f"  Expected file: {filename}")
            print()
    else:
        print("✓ ALL FILES PRESENT!")
        print()

    # Find unexpected files (not in expected list)
    unexpected = []
    for downloaded_file in downloaded_files:
        if downloaded_file not in expected_filenames:
            unexpected.append(downloaded_file)

    if unexpected:
        print(f"\nUNEXPECTED/EXTRA FILES: {len(unexpected)}")
        print("-" * 80)
        for file in sorted(unexpected):
            print(f"  {file}")

    print("\n" + "=" * 80)
    print(f"SUMMARY: {len(downloaded_files) - len(missing)} / {len(EXPECTED_SECTIONS)} files present")
    if missing:
        print(f"Missing: {len(missing)} files")
    else:
        print("Status: COMPLETE ✓")
    print("=" * 80)
