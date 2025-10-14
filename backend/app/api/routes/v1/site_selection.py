from fastapi import APIRouter

router = APIRouter(prefix="/site-selection", tags=["site-selection"])


@router.get("/")
def get_site_selection():
    return {"message": "Hello, World!"}
