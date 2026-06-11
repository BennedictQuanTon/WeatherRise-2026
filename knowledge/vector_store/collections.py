"""
Qdrant Collection Definitions — V3
Defines all KB collections, their text fields used for embedding,
and metadata filters available for search.
"""
from typing import Dict, Any

COLLECTIONS: Dict[str, Dict[str, Any]] = {
    "tourism_knowledge": {
        "description": "Tourist attractions, places, locations in Vietnam",
        "text_fields": ["name_vi", "name_en", "sub_category", "highlights", "vibe_tags", "city"],
        "vector_size": 1024,   # NV-EmbedQA-E5-v5 output dim
        "metadata_filters": ["city", "is_indoor", "sub_category", "source"],
    },
    "construction_knowledge": {
        "description": "Construction sites, project risk zones",
        "text_fields": ["name", "description", "location", "hazard_type"],
        "vector_size": 1024,
        "metadata_filters": ["city", "risk_level", "project_type"],
    },
    "agriculture_knowledge": {
        "description": "Agricultural areas, crop zones, farming sites",
        "text_fields": ["name", "crop_type", "location", "notes"],
        "vector_size": 1024,
        "metadata_filters": ["city", "crop_type"],
    },
    "weather_rules": {
        "description": "Domain-specific weather risk rules and thresholds",
        "text_fields": ["domain", "rule_name", "description", "condition"],
        "vector_size": 1024,
        "metadata_filters": ["domain", "risk_type"],
    },
}

COLLECTION_NAMES = list(COLLECTIONS.keys())
