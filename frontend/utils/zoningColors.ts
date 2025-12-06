/**
 * Standard land use color mapping based on APA/planning conventions
 * Reference: De Chiara (1969), Inter-County Regional Planning Commission Denver (1965)
 *
 * Color scheme follows established planning standards:
 * - Residential: Yellows (single-family) to Browns (multi-family)
 * - Commercial: Reds and Oranges
 * - Mixed Use: Purple
 * - Industrial: Grays
 * - Institutional: Blues
 * - Public/Government: Pink
 * - Open Space/Parks: Greens
 * - Agricultural: Apple Green
 * - Transportation: Slate Gray
 */

export const ZONE_COLORS = {
  // Residential
  SINGLE_FAMILY: "#FFF44F",      // Lemon Yellow
  DUPLEX: "#E6B800",             // Dark Yellow
  MULTI_FAMILY: "#8B4513",       // Dark Brown
  MOBILE_HOME: "#E6E6FA",        // Lavender
  RESIDENTIAL_DEFAULT: "#FFDB58", // Default yellow

  // Commercial
  LIGHT_COMMERCIAL: "#FF6B6B",   // Light Red
  OFFICE: "#FF4444",             // Vermilion Red
  INTENSIVE_COMMERCIAL: "#DC143C", // Crimson Lake
  COMMERCIAL_DEFAULT: "#FF0000", // Scarlet Red

  // Mixed Use
  MIXED_USE: "#800080",          // Purple

  // Industrial
  HEAVY_INDUSTRIAL: "#1C1C1C",   // Near black
  LIGHT_INDUSTRIAL: "#A9A9A9",   // Light Gray
  INDUSTRIAL_DEFAULT: "#696969", // Medium Gray

  // Institutional
  INSTITUTIONAL: "#4169E1",      // True Blue

  // Public/Government
  PUBLIC: "#FFB6C1",             // Pink

  // Open Space/Parks
  OPEN_SPACE: "#228B22",         // True Green

  // Educational
  EDUCATION: "#7CFC00",          // Grass Green

  // Religious
  RELIGIOUS: "#4B0082",          // Indigo Blue

  // Agricultural
  AGRICULTURAL: "#8DB600",       // Apple Green

  // Transportation
  TRANSPORTATION: "#708090",     // Slate Gray

  // Waterfront
  WATERFRONT: "#7FFFD4",         // Aquamarine

  // Health
  HEALTH: "#008B8B",             // Peacock Green

  // Cemetery
  CEMETERY: "#7FFFD4",           // Aquamarine

  // Unknown/Default
  UNKNOWN: "#888888",            // Gray
} as const;

/**
 * Category matching rules - order matters (first match wins within category)
 * Each category has keywords to match and optional sub-categories
 */
type CategoryRule = {
  keywords: string[];
  color: string;
  subCategories?: { keywords: string[]; color: string }[];
};

const CATEGORY_RULES: CategoryRule[] = [
  // RESIDENTIAL - check for residence/residential/dwelling/family/home
  // Must come before commercial since "c-1(residence)" should be residential
  {
    keywords: ["residen", "dwelling", "family", "home", "housing", "apartment", "r-1", "r-2", "r-3", "r-4", "r-5"],
    color: ZONE_COLORS.RESIDENTIAL_DEFAULT,
    subCategories: [
      { keywords: ["single", "one", "1-", "sf", "r-1", "r1"], color: ZONE_COLORS.SINGLE_FAMILY },
      { keywords: ["duplex", "two", "2-", "r-2", "r2"], color: ZONE_COLORS.DUPLEX },
      { keywords: ["multi", "apartment", "3-", "4-", "5-", "mf", "r-3", "r-4", "r-5"], color: ZONE_COLORS.MULTI_FAMILY },
      { keywords: ["mobile", "manufactured", "trailer"], color: ZONE_COLORS.MOBILE_HOME },
    ],
  },
  // COMMERCIAL - check for commercial/business/retail/shop/store
  {
    keywords: ["commercial", "business", "retail", "shop", "store", "merchant", "c-1", "c-2", "c-3"],
    color: ZONE_COLORS.COMMERCIAL_DEFAULT,
    subCategories: [
      { keywords: ["light", "neighborhood", "local", "convenience"], color: ZONE_COLORS.LIGHT_COMMERCIAL },
      { keywords: ["office", "professional", "service"], color: ZONE_COLORS.OFFICE },
      { keywords: ["central", "downtown", "intensive", "heavy", "general"], color: ZONE_COLORS.INTENSIVE_COMMERCIAL },
    ],
  },
  // MIXED USE
  {
    keywords: ["mixed", "mu-", "mxd"],
    color: ZONE_COLORS.MIXED_USE,
  },
  // INDUSTRIAL
  {
    keywords: ["industrial", "manufacturing", "warehouse", "factory", "i-1", "i-2", "m-1", "m-2"],
    color: ZONE_COLORS.INDUSTRIAL_DEFAULT,
    subCategories: [
      { keywords: ["heavy", "general", "intensive"], color: ZONE_COLORS.HEAVY_INDUSTRIAL },
      { keywords: ["light", "limited", "restricted"], color: ZONE_COLORS.LIGHT_INDUSTRIAL },
    ],
  },
  // INSTITUTIONAL
  {
    keywords: ["institutional", "civic", "government", "municipal", "community"],
    color: ZONE_COLORS.INSTITUTIONAL,
  },
  // PUBLIC (but not open space)
  {
    keywords: ["public"],
    color: ZONE_COLORS.PUBLIC,
  },
  // OPEN SPACE/PARKS
  {
    keywords: ["open", "park", "recreation", "conservation", "green", "os-"],
    color: ZONE_COLORS.OPEN_SPACE,
  },
  // EDUCATION
  {
    keywords: ["school", "education", "university", "college", "campus", "academic"],
    color: ZONE_COLORS.EDUCATION,
  },
  // RELIGIOUS
  {
    keywords: ["church", "religious", "worship", "temple", "mosque", "synagogue"],
    color: ZONE_COLORS.RELIGIOUS,
  },
  // AGRICULTURAL
  {
    keywords: ["agricultural", "farm", "rural", "ag-", "agri"],
    color: ZONE_COLORS.AGRICULTURAL,
  },
  // TRANSPORTATION
  {
    keywords: ["transport", "railroad", "utility", "infrastructure", "transit"],
    color: ZONE_COLORS.TRANSPORTATION,
  },
  // WATERFRONT
  {
    keywords: ["waterfront", "marine", "harbor", "water", "coastal", "maritime", "port"],
    color: ZONE_COLORS.WATERFRONT,
  },
  // HEALTH
  {
    keywords: ["health", "hospital", "medical", "clinic", "healthcare"],
    color: ZONE_COLORS.HEALTH,
  },
  // CEMETERY
  {
    keywords: ["cemetery", "memorial", "burial"],
    color: ZONE_COLORS.CEMETERY,
  },
];

/**
 * Check if text contains any of the keywords
 */
function matchesKeywords(text: string, keywords: string[]): boolean {
  return keywords.some((keyword) => text.includes(keyword));
}

/**
 * Get the standard land use color for a zone subtype
 * Uses fuzzy matching with category rules
 * @param zoneSubtype - The zone subtype string from the database
 * @returns Hex color code
 */
export function getZoneSubtypeColor(zoneSubtype: string | null | undefined): string {
  if (!zoneSubtype) return ZONE_COLORS.UNKNOWN;

  const text = zoneSubtype.toLowerCase();

  for (const rule of CATEGORY_RULES) {
    if (matchesKeywords(text, rule.keywords)) {
      // Check sub-categories first for more specific match
      if (rule.subCategories) {
        for (const sub of rule.subCategories) {
          if (matchesKeywords(text, sub.keywords)) {
            return sub.color;
          }
        }
      }
      return rule.color;
    }
  }

  return ZONE_COLORS.UNKNOWN;
}

/**
 * Convert ZONE_COLORS key to a readable label
 * e.g., "SINGLE_FAMILY" -> "Single Family"
 */
function keyToLabel(key: string): string {
  return key
    .split("_")
    .map((word) => word.charAt(0) + word.slice(1).toLowerCase())
    .join(" ");
}

/**
 * Map from color hex to category label, auto-generated from ZONE_COLORS
 */
export const COLOR_TO_CATEGORY: Record<string, string> = Object.entries(ZONE_COLORS)
  .reduce((acc, [key, color]) => {
    // Only set if not already defined (first match wins)
    if (!acc[color]) {
      // Remove "_DEFAULT" suffix for cleaner labels
      const cleanKey = key.replace("_DEFAULT", "");
      acc[color] = keyToLabel(cleanKey);
    }
    return acc;
  }, {} as Record<string, string>);
