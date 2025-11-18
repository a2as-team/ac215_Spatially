from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any
from app.utils.query_vectordb import VectorDBQuery
from app.utils.zoning_map_spatial_query import ZoningMapSpatialQuery
from app.core.config import settings

router = APIRouter(prefix="/zoning_ordinance", tags=["zoning-ordinance"])
