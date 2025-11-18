from fastapi import APIRouter

router = APIRouter(prefix="/zoning_ordinance", tags=["zoning-ordinance"])


@router.get(f"")
def get_zoning_ordinance_by_city(city: str, question: str):
    return {"message": f"Hello, {city}! {question}!"}
