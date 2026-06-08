import os
import json
from pathlib import Path
from typing import List, Optional
from ..schemas.destination_schema import DestinationRecord

class DestinationService:
    """Manages transactional loading and keyword lookups over the catalog shard."""
    def __init__(self):
        # 1. Establish absolute anchor and ascend 4 levels to the '/code/' root
        base_dir = Path(__file__).resolve().parent.parent.parent.parent
        
        # 2. Descend into the explicit data directory target
        self.catalog_path = base_dir / "data" / "attractions" / "danang_locations.json"
        
        self.storage = {}
        self._load_catalog_into_memory()

    def _load_catalog_into_memory(self):
        if not os.path.exists(self.catalog_path):
            raise FileNotFoundError(f"Database shard missing at location: {self.catalog_path}")
        with open(self.catalog_path, "r", encoding="utf-8") as file:
            data = json.load(file)
            for item in data:
                record = DestinationRecord(**item)
                self.storage[record.destination_id] = record

    def get_destination_by_id(self, dest_id: str) -> Optional[DestinationRecord]:
        return self.storage.get(dest_id)

    def search_destinations(self, query: str) -> List[DestinationRecord]:
        if not query:
            return list(self.storage.values())
        cleaned_query = query.lower().strip()
        return [
            rec for rec in self.storage.values()
            if cleaned_query in rec.name.lower() or any(cleaned_query in tag.lower() for tag in rec.tags)
        ]