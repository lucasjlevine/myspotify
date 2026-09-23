from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    """Liveness check for frontend boot and joint-dev scripts."""
    return {"ok": True}
