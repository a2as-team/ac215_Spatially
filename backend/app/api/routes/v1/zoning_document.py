from fastapi import APIRouter

router = APIRouter(prefix="/zoning-document", tags=["zoning-document"])


@router.get("/")
def get_zoning_document():
    return {"message": "Hello, World!"}
