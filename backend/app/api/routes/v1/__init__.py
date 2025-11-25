"""API v1 routes"""

from fastapi import APIRouter

from app.api.routes.v1 import development_plans, census, zoning_ordinance

router = APIRouter()
router.include_router(development_plans.router)
router.include_router(census.router)
router.include_router(zoning_ordinance.router)
