from fastapi import APIRouter

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
