from fastapi import APIRouter, Query

from app.ml.registry import DEFAULT_MODEL_ID
from app.ml.service import list_models, predict_next

router = APIRouter(tags=["predict"])


@router.get("/predict/models")
def predict_models():
    """List available predictor models and training status."""
    return list_models()


@router.get("/predict/next")
def predict_next_song(
    k: int = Query(default=5, ge=1, le=50),
    model: str = Query(default=DEFAULT_MODEL_ID),
    track_id: str | None = Query(default=None),
):
    """Predict the next track(s). Defaults to the most recent stored play as seed."""
    return predict_next(k=k, model=model, track_id=track_id)
