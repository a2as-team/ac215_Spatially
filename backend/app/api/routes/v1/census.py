from fastapi import APIRouter

router = APIRouter(prefix="/census", tags=["census"])


@router.get("/")
def get_census():
    return {"message": "Hello, World!"}
