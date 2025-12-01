"""API v1 routes"""

from fastapi import APIRouter

from app.api.routes.v1 import development_plans, census, zoning_ordinance, chat, cities

router = APIRouter()
router.include_router(cities.router)
router.include_router(development_plans.router)
router.include_router(census.router)
router.include_router(zoning_ordinance.router)
router.include_router(chat.router)
