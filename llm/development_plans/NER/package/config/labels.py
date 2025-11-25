# Base entity types (without BIO prefixes)
BASE_ENTITY_TYPES = [
    "CONSTRUCTION_DETAILS",
    "PROPERTY_USAGE",
    "ZONING_DISTRICT",
    "ZONING_RELIEF",
    "ARTICLE_REFERENCE",
    "EXPECTED_IMPACT",
    "LOCATION_CONTEXT",
]

# Generate BIO-tagged labels
# For each entity type, we need B- (Begin) and I- (Inside) tags
NER_LABELS = []
for entity_type in BASE_ENTITY_TYPES:
    NER_LABELS.append(f"B-{entity_type}")
    NER_LABELS.append(f"I-{entity_type}")

# Note: "O" (Outside) label is added separately in the trainer
