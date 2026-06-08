from fastapi import APIRouter, Depends, HTTPException
from typing import List
from ..services.destination_service import DestinationService
from ..schemas.destination_schema import DestinationRecord

router = APIRouter(prefix="/destinations", tags=["Destinations"])

# Singleton instantiation dependency provider
def get_dest_service() -> DestinationService:
    return DestinationService()

router = APIRouter(prefix="/destinations", tags=["Destinations"])

@router.get("", response_model=List[DestinationRecord])
def list_all_destinations(service: DestinationService = Depends(get_dest_service)):
    return service.search_destinations(query="")

@router.get("/search", response_model=List[DestinationRecord])
def search_destinations(q: str, service: DestinationService = Depends(get_dest_service)):
    """Handles controlled dropdown type-ahead query blocks."""
    return service.search_destinations(query=q)

@router.get("/{destination_id}", response_model=DestinationRecord)
def get_destination_by_id(destination_id: str, service: DestinationService = Depends(get_dest_service)):
    record = service.get_destination_by_id(destination_id)
    if not record:
        raise HTTPException(status_code=404, detail="Requested destination code not found in registry.")
    return record