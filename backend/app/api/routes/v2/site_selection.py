"""Site selection v2 endpoints with enhanced features"""

from fastapi import APIRouter

router = APIRouter(prefix="/site-selection", tags=["site-selection-v2"])


@router.get("/")
def get_site_selection_v2():
    """Enhanced site selection endpoint with new features"""
    return {
        "message": "Site Selection V2",
        "version": "2.0",
        "features": ["enhanced search", "ML recommendations", "faster processing"],
    }


@router.get("/advanced")
def get_advanced_features():
    """New endpoint only available in v2"""
    return {
        "message": "Advanced features available in v2",
        "capabilities": ["AI analysis", "bulk processing"],
    }
