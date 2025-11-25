from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any
from app.utils.vector_query.zoning_ordinance import ZoningOrdinanceVectorQuery
from app.utils.spatial_query.zoning_map import ZoningMapSpatialQuery
from app.core.config import settings

router = APIRouter(prefix="/zoning_ordinance", tags=["zoning-ordinance"])


@router.get("/{city}")
def get_zoning_map(city: str):
    """Get all zoning data for a city"""
    try:
        zoning_query = ZoningMapSpatialQuery(db_name=settings.POSTGRES_DB)
        zoning_data = zoning_query.get_all_zoning_for_city(city)

        return {
            "city": city,
            "zoning_data": zoning_data,
            "count": len(zoning_data)
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve zoning data: {str(e)}")
