"""API v1 routes"""

from fastapi import APIRouter

from app.api.routes.v1 import site_selection, zoning_document

router = APIRouter()
router.include_router(site_selection.router)
router.include_router(zoning_document.router)
