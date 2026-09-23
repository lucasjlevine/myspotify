from __future__ import annotations

from collections import defaultdict
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
from app.ml.windows import list_window_presets, resolve_seed_plays
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
        "album_image_url": getattr(play, "album_image_url", None),
    }


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
            "album_image_url": getattr(row, "album_image_url", None),
        }
    return meta


def _read_model_meta(model_id: str) -> dict:
    if model_id in ("item_knn", "prompted", "embedding"):
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
    return {
        "default": DEFAULT_MODEL_ID,
        "models": models,
        "windows": list_window_presets(),
    }


def _context_from_plays(plays: list[Play]) -> PredictContext:
    primary = plays[-1]
    texts = tuple(
        f"{(p.artist_names or '').strip()} {(p.album_name or '').strip()} "
        f"{(p.track_name or '').strip()}".strip()
        for p in plays
    )
    return PredictContext(
        track_id=primary.track_id,
        artist_names=primary.artist_names or "",
        album_name=primary.album_name or "",
        played_at=primary.played_at,
        recent_track_ids=tuple(p.track_id for p in plays),
        recent_texts=texts,
    )


def _blend_predictions(
    predictor: NextSongPredictor,
    plays: list[Play],
    *,
    k: int,
) -> list[tuple[str, float]]:
    """Recency-weighted blend of per-seed predictions for classical models."""
    model_id = getattr(predictor, "model_id", "")
    # Sequence-aware models consume the full window in one predict call
    if len(plays) == 1 or model_id in ("prompted", "embedding"):
        ctx = _context_from_plays(plays)
        return predictor.predict(ctx, k=k)

    exclude = {p.track_id for p in plays}
    scores: dict[str, float] = defaultdict(float)
    n = len(plays)
    # Fetch extra candidates so blending still fills top-k after exclusions
    fetch_k = max(k * 3, 15)

    for i, play in enumerate(plays):
        weight = (i + 1) / n  # newer seeds weigh more
        ctx = PredictContext(
            track_id=play.track_id,
            artist_names=play.artist_names or "",
            album_name=play.album_name or "",
            played_at=play.played_at,
            recent_track_ids=tuple(p.track_id for p in plays),
            recent_texts=tuple(
                f"{(p.artist_names or '')} {(p.track_name or '')}".strip()
                for p in plays
            ),
        )
        for tid, score in predictor.predict(ctx, k=fetch_k):
            if tid in exclude:
                continue
            scores[tid] += score * weight

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return ranked[:k]


def predict_next(
    k: int = 5,
    *,
    model: str = DEFAULT_MODEL_ID,
    path: Path | None = None,
    track_id: str | None = None,
    window: str = "latest",
    tz_offset_minutes: int = 0,
) -> dict:
    if path is not None:
        predictor = create_predictor(model)
        predictor = type(predictor).load(path)  # type: ignore[misc]
        model_id = model
    else:
        predictor = load_predictor(model)
        model_id = model

    with session_scope() as session:
        plays = resolve_seed_plays(
            session,
            window=window,
            track_id=track_id if window == "latest" else None,
            tz_offset_minutes=tz_offset_minutes,
        )
        ranked = _blend_predictions(predictor, plays, k=k)
        meta = _track_meta_map(session, [tid for tid, _ in ranked])
        seed_dicts = [_play_to_dict(p) for p in plays]

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
    if hasattr(predictor, "backend"):
        model_info["backend"] = predictor.backend

    return {
        "context": seed_dicts[-1],
        "seeds": seed_dicts,
        "window": window,
        "model": model_info,
        "predictions": predictions,
    }


def search_by_prompt(q: str, *, k: int = 10, model: str = "embedding") -> dict:
    """Nearest tracks to a free-text mood/phrase in embedding space."""
    text = (q or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="empty_query")

    if model not in list_model_ids():
        raise HTTPException(status_code=400, detail=f"unknown_model:{model}")

    predictor = load_predictor(model)
    search = getattr(predictor, "search_text", None)
    if search is None:
        raise HTTPException(
            status_code=400,
            detail=f"model_no_text_search:{model} — use model=embedding",
        )

    ranked = search(text, k=k)
    with session_scope() as session:
        meta = _track_meta_map(session, [tid for tid, _ in ranked])

    predictions = []
    for tid, score in ranked:
        item = {"track_id": tid, "score": score}
        item.update(meta.get(tid, {}))
        predictions.append(item)

    return {
        "query": text,
        "model": {
            "id": model,
            "path": str(artifact_path(model)),
            "backend": getattr(predictor, "backend", None),
            "model_name": getattr(predictor, "model_name", None),
            "trained_at": getattr(predictor, "trained_at", None),
            "n_tracks": getattr(predictor, "n_tracks", None),
            "dim": getattr(predictor, "dim", None),
        },
        "predictions": predictions,
    }


def project_prompt_space(
    q: str,
    *,
    k: int = 24,
    context: int = 48,
    model: str = "embedding",
) -> dict:
    """2D PCA constellation around a mood prompt."""
    text = (q or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="empty_query")
    if model not in list_model_ids():
        raise HTTPException(status_code=400, detail=f"unknown_model:{model}")

    predictor = load_predictor(model)
    project = getattr(predictor, "project_space", None)
    if project is None:
        raise HTTPException(
            status_code=400,
            detail=f"model_no_space_project:{model} — use model=embedding",
        )

    payload = project(text, k=k, context=context)
    track_ids = [
        p["id"] for p in payload.get("points") or [] if p.get("kind") != "query"
    ]
    with session_scope() as session:
        meta = _track_meta_map(session, track_ids)

    points = []
    for p in payload.get("points") or []:
        item = dict(p)
        if p.get("kind") != "query":
            item.update(meta.get(p["id"], {}))
            item["track_id"] = p["id"]
        points.append(item)

    return {
        "query": text,
        "model": {
            "id": model,
            "path": str(artifact_path(model)),
            "backend": getattr(predictor, "backend", None),
            "model_name": getattr(predictor, "model_name", None),
            "trained_at": getattr(predictor, "trained_at", None),
            "n_tracks": getattr(predictor, "n_tracks", None),
            "dim": getattr(predictor, "dim", None),
            "text_dim": getattr(predictor, "text_dim", None),
        },
        "points": points,
        "edges": payload.get("edges") or [],
    }
