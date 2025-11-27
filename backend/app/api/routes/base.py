from fastapi import APIRouter, HTTPException
from app.core.config import settings
from app.utils.db_accessor import DBConnector

router = APIRouter(tags=["base"])


@router.get("/")
def root():
    """Public root endpoint"""
    return {
        "message": "Welcome to Spatially API",
        "status": "ok",
        "docs": "/docs",
    }


@router.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@router.get("/readiness")
async def readiness_check():
    try:
        db = DBConnector(db_name=settings.POSTGRES_DB)
        cities = db.get_all_cities()
        print("cities", cities)
        db.close()
        return {"status": "ready"}
    except Exception:
        raise HTTPException(status_code=503, detail="db_unavailable")
