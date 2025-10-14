"""API v2 routes"""

from fastapi import APIRouter

from app.api.routes.v2 import site_selection

router = APIRouter()
router.include_router(site_selection.router)
