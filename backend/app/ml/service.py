from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import DATA_DIR
from app.database import session_scope
from app.ml.markov import MarkovPredictor
from app.models import Play

DEFAULT_MODEL_PATH = DATA_DIR / "models" / "markov.json"


def model_path() -> Path:
    return DEFAULT_MODEL_PATH


def load_predictor(path: Path | None = None) -> MarkovPredictor:
    artifact = path or model_path()
    if not artifact.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                "no_trained_model: run "
                "`uv run python -m app.ml.train` from the backend directory"
            ),
        )
    return MarkovPredictor.load(artifact)


def _play_to_dict(play: Play) -> dict:
    return {
        "played_at": play.played_at,
        "track_id": play.track_id,
        "track_name": play.track_name,
        "artist_names": play.artist_names,
        "album_name": play.album_name,
        "duration_ms": play.duration_ms,
        "context_uri": play.context_uri,
    }


def _latest_play(session: Session) -> Play | None:
    return session.scalars(
        select(Play).order_by(Play.played_at.desc()).limit(1)
    ).first()


def _track_meta_map(session: Session, track_ids: list[str]) -> dict[str, dict]:
    if not track_ids:
        return {}

    rows = session.scalars(
        select(Play).where(Play.track_id.in_(track_ids)).order_by(Play.played_at.desc())
    ).all()

    meta: dict[str, dict] = {}
    for row in rows:
        if row.track_id in meta:
            continue
        meta[row.track_id] = {
            "track_name": row.track_name,
            "artist_names": row.artist_names,
            "album_name": row.album_name,
        }
    return meta


def predict_next(k: int = 5, *, path: Path | None = None) -> dict:
    predictor = load_predictor(path)

    with session_scope() as session:
        latest = _latest_play(session)
        if latest is None:
            raise HTTPException(
                status_code=404,
                detail="no_plays: sync listening history before predicting",
            )

        context = _play_to_dict(latest)
        ranked = predictor.predict(latest.track_id, k=k)
        meta = _track_meta_map(session, [track_id for track_id, _ in ranked])

    predictions = []
    for track_id, score in ranked:
        item = {"track_id": track_id, "score": score}
        item.update(meta.get(track_id, {}))
        predictions.append(item)

    return {
        "context": context,
        "model": {
            "path": str(path or model_path()),
            "trained_at": predictor.trained_at,
            "n_plays": predictor.n_plays,
            "n_transitions": predictor.n_transitions,
        },
        "predictions": predictions,
    }
