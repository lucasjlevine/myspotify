from fastapi import APIRouter, Query

from app.ml import predict_next

router = APIRouter(tags=["predict"])


@router.get("/predict/next")
def predict_next_song(k: int = Query(default=5, ge=1, le=50)):
    """Predict the next track(s) given the most recent stored play."""
    return predict_next(k=k)
