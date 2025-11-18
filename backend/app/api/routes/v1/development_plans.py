from fastapi import APIRouter

router = APIRouter(prefix="/development-plans", tags=["development-plans"])


@router.get("/")
def get_development_plans():
    return {"message": "Hello, World!"}
