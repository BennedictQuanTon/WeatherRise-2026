import json
import os
from typing import List, Optional
from backend.schemas.destination_schema import DestinationSchema

class DestinationService:
    def __init__(self, data_path: str = None):
        if data_path is None:
            # Default to the data directory
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_path = os.path.join(base_dir, "data", "danang_locations.json")
            
        self.destinations: List[DestinationSchema] = []
        self._load_data(data_path)

    def _load_data(self, data_path: str):
        try:
            with open(data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.destinations = [DestinationSchema(**item) for item in data]
        except Exception as e:
            print(f"Error loading destinations: {e}")

    def get_all(self) -> List[DestinationSchema]:
        return self.destinations

    def get_by_id(self, destination_id: str) -> Optional[DestinationSchema]:
        for dest in self.destinations:
            if dest.destination_id == destination_id:
                return dest
        return None

    def search(self, query: str) -> List[DestinationSchema]:
        query = query.lower()
        results = []
        for dest in self.destinations:
            if query in dest.name.lower() or query in dest.destination_id.lower() or any(query in tag.lower() for tag in dest.tags):
                results.append(dest)
        return results

# Singleton instance
destination_service = DestinationService()
