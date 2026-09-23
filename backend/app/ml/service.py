from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import session_scope
from app.ml.protocol import NextSongPredictor, PredictContext
from app.ml.registry import (
    DEFAULT_MODEL_ID,
    REGISTRY,
    artifact_path,
    create_predictor,
    is_trained,
    list_model_ids,
    metadata_path,
)
from app.models import Play


def load_predictor(model_id: str = DEFAULT_MODEL_ID) -> NextSongPredictor:
    if model_id not in list_model_ids():
        raise HTTPException(
            status_code=400,
            detail=f"unknown_model: {model_id}. Choose from {list_model_ids()}",
        )
    path = artifact_path(model_id)
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                f"no_trained_model:{model_id}: run "
                f"`uv run python -m app.ml.train --model {model_id}` "
                "from the backend directory"
            ),
        )
    return REGISTRY[model_id].load(path)  # type: ignore[return-value]


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
        select(Play)
        .where(Play.track_id.in_(track_ids))
        .order_by(Play.played_at.desc())
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


def _read_model_meta(model_id: str) -> dict:
    if model_id == "item_knn":
        meta_file = metadata_path(model_id)
        if meta_file.exists():
            import json

            return json.loads(meta_file.read_text(encoding="utf-8"))
        return {}

    path = artifact_path(model_id)
    if not path.exists():
        return {}
    import json

    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        "model_id": model_id,
        "trained_at": payload.get("trained_at"),
        "n_plays": payload.get("n_plays"),
        "n_transitions": payload.get("n_transitions"),
    }


def list_models() -> dict:
    models = []
    for model_id in list_model_ids():
        trained = is_trained(model_id)
        entry: dict = {
            "id": model_id,
            "trained": trained,
            "artifact": str(artifact_path(model_id)),
        }
        if trained:
            meta = {
                k: v
                for k, v in _read_model_meta(model_id).items()
                if k != "model_id" and v is not None
            }
            entry.update(meta)
        models.append(entry)
    return {"default": DEFAULT_MODEL_ID, "models": models}


def predict_next(
    k: int = 5,
    *,
    model: str = DEFAULT_MODEL_ID,
    path: Path | None = None,
    track_id: str | None = None,
) -> dict:
    if path is not None:
        # Legacy/test override: load markov-style from explicit path via given model class
        predictor = create_predictor(model)
        predictor = type(predictor).load(path)  # type: ignore[misc]
        model_id = model
    else:
        predictor = load_predictor(model)
        model_id = model

    with session_scope() as session:
        if track_id is not None:
            seed = session.scalars(
                select(Play)
                .where(Play.track_id == track_id)
                .order_by(Play.played_at.desc())
                .limit(1)
            ).first()
            if seed is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"unknown_track:{track_id}",
                )
        else:
            seed = _latest_play(session)
            if seed is None:
                raise HTTPException(
                    status_code=404,
                    detail="no_plays: sync listening history before predicting",
                )

        context_play = _play_to_dict(seed)
        context = PredictContext(
            track_id=seed.track_id,
            artist_names=seed.artist_names or "",
            album_name=seed.album_name or "",
            played_at=seed.played_at,
        )
        ranked = predictor.predict(context, k=k)
        meta = _track_meta_map(session, [tid for tid, _ in ranked])

    predictions = []
    for tid, score in ranked:
        item = {"track_id": tid, "score": score}
        item.update(meta.get(tid, {}))
        predictions.append(item)

    model_info = {
        "id": model_id,
        "path": str(path or artifact_path(model_id)),
        "trained_at": getattr(predictor, "trained_at", None),
        "n_plays": getattr(predictor, "n_plays", None),
    }
    if hasattr(predictor, "n_transitions"):
        model_info["n_transitions"] = predictor.n_transitions

    return {
        "context": context_play,
        "model": model_info,
        "predictions": predictions,
    }
