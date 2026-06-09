from fastapi import APIRouter, HTTPException, Query
from typing import List
from backend.schemas.destination_schema import DestinationSchema
from backend.services.destination_service import destination_service
from backend.schemas.response_schema import StandardResponse, success_response, error_response

router = APIRouter(prefix="/destinations", tags=["Destinations"])

@router.get("", response_model=StandardResponse)
async def get_all_destinations():
    try:
        data = destination_service.get_all()
        return success_response(data=[d.model_dump() for d in data])
    except Exception as e:
        return error_response(code="fetch_failed", message=str(e))

@router.get("/search", response_model=StandardResponse)
async def search_destinations(q: str = Query(..., description="Search keyword")):
    try:
        results = destination_service.search(q)
        return success_response(data=[d.model_dump() for d in results])
    except Exception as e:
        return error_response(code="search_failed", message=str(e))

@router.get("/{destination_id}", response_model=StandardResponse)
async def get_destination(destination_id: str):
    dest = destination_service.get_by_id(destination_id)
    if not dest:
        return error_response(code="destination_not_found", message="Destination not found")
    return success_response(data=dest.model_dump())
