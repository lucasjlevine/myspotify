from fastapi import APIRouter, Query

from app.ml.registry import DEFAULT_MODEL_ID
from app.ml.service import list_models, predict_next
from app.ml.windows import list_window_presets

router = APIRouter(tags=["predict"])


@router.get("/predict/models")
def predict_models():
    """List available predictor models, windows, and training status."""
    return list_models()


@router.get("/predict/windows")
def predict_windows():
    return {"windows": list_window_presets()}


@router.get("/predict/next")
def predict_next_song(
    k: int = Query(default=5, ge=1, le=50),
    model: str = Query(default=DEFAULT_MODEL_ID),
    track_id: str | None = Query(default=None),
    window: str = Query(default="latest"),
    tz_offset_minutes: int = Query(default=0, ge=-840, le=840),
):
    """Predict next track(s).

    `window` presets: latest, hours_4, today, plays_10, plays_20
    (or hours:N / plays:N). Multi-seed windows blend classical models
    with recency weights; `prompted` uses the full window as one prompt.
    """
    return predict_next(
        k=k,
        model=model,
        track_id=track_id,
        window=window,
        tz_offset_minutes=tz_offset_minutes,
    )
