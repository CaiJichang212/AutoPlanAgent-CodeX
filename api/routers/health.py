from fastapi import APIRouter

router = APIRouter()


@router.get("/healthz")
def health():
    return {"status": "ok"}
