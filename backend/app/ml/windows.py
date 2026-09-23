"""Resolve listening windows for multi-seed prediction."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Play

# Presets exposed to the API / UI
WINDOW_PRESETS = {
    "latest": {"kind": "plays", "n": 1},
    "hours_4": {"kind": "hours", "n": 4},
    "today": {"kind": "today", "n": 0},
    "plays_10": {"kind": "plays", "n": 10},
    "plays_20": {"kind": "plays", "n": 20},
}


def parse_window(window: str) -> dict:
    if window in WINDOW_PRESETS:
        return dict(WINDOW_PRESETS[window])
    if window.startswith("hours:"):
        try:
            n = int(window.split(":", 1)[1])
        except ValueError as exc:
            raise HTTPException(400, detail=f"invalid_window:{window}") from exc
        if n < 1 or n > 168:
            raise HTTPException(400, detail="window_hours_out_of_range")
        return {"kind": "hours", "n": n}
    if window.startswith("plays:"):
        try:
            n = int(window.split(":", 1)[1])
        except ValueError as exc:
            raise HTTPException(400, detail=f"invalid_window:{window}") from exc
        if n < 1 or n > 100:
            raise HTTPException(400, detail="window_plays_out_of_range")
        return {"kind": "plays", "n": n}
    raise HTTPException(
        400,
        detail=f"unknown_window:{window}. Use {list(WINDOW_PRESETS)} or hours:N / plays:N",
    )


def _parse_iso(value: str) -> datetime:
    text = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def resolve_seed_plays(
    session: Session,
    *,
    window: str = "latest",
    track_id: str | None = None,
    tz_offset_minutes: int = 0,
) -> list[Play]:
    """Return seed plays oldest→newest for the chosen window.

    If `track_id` is set with window=latest, use that track's most recent play.
    For multi-play windows, `track_id` is ignored (window drives the seed set).
    """
    spec = parse_window(window)
    now = datetime.now(timezone.utc)

    if spec["kind"] == "plays" and spec["n"] == 1:
        if track_id is not None:
            seed = session.scalars(
                select(Play)
                .where(Play.track_id == track_id)
                .order_by(Play.played_at.desc())
                .limit(1)
            ).first()
            if seed is None:
                raise HTTPException(404, detail=f"unknown_track:{track_id}")
            return [seed]
        latest = session.scalars(
            select(Play).order_by(Play.played_at.desc()).limit(1)
        ).first()
        if latest is None:
            raise HTTPException(
                404, detail="no_plays: sync listening history before predicting"
            )
        return [latest]

    if spec["kind"] == "plays":
        rows = session.scalars(
            select(Play).order_by(Play.played_at.desc()).limit(spec["n"])
        ).all()
        if not rows:
            raise HTTPException(
                404, detail="no_plays: sync listening history before predicting"
            )
        return list(reversed(rows))

    if spec["kind"] == "hours":
        cutoff = now - timedelta(hours=spec["n"])
        cutoff_iso = cutoff.isoformat().replace("+00:00", "Z")
        rows = session.scalars(
            select(Play)
            .where(Play.played_at >= cutoff_iso)
            .order_by(Play.played_at.asc())
        ).all()
        if not rows:
            # Fall back to last N plays so empty windows still work
            rows = session.scalars(
                select(Play).order_by(Play.played_at.desc()).limit(10)
            ).all()
            if not rows:
                raise HTTPException(
                    404, detail="no_plays: sync listening history before predicting"
                )
            return list(reversed(rows))
        return list(rows)

    if spec["kind"] == "today":
        offset = timedelta(minutes=tz_offset_minutes)
        local_now = now + offset
        local_midnight = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        utc_start = (local_midnight - offset).astimezone(timezone.utc)
        cutoff_iso = utc_start.isoformat().replace("+00:00", "Z")
        rows = session.scalars(
            select(Play)
            .where(Play.played_at >= cutoff_iso)
            .order_by(Play.played_at.asc())
        ).all()
        if not rows:
            rows = session.scalars(
                select(Play).order_by(Play.played_at.desc()).limit(10)
            ).all()
            if not rows:
                raise HTTPException(
                    404, detail="no_plays: sync listening history before predicting"
                )
            return list(reversed(rows))
        return list(rows)

    raise HTTPException(400, detail=f"unhandled_window:{window}")


def list_window_presets() -> list[dict]:
    return [
        {"id": "latest", "label": "Latest track", "description": "Single most recent play"},
        {
            "id": "hours_4",
            "label": "Last 4 hours",
            "description": "Everything played in the last 4 hours",
        },
        {
            "id": "today",
            "label": "Today",
            "description": "Plays since local midnight",
        },
        {
            "id": "plays_10",
            "label": "Last 10 plays",
            "description": "Recent session slice",
        },
        {
            "id": "plays_20",
            "label": "Last 20 plays",
            "description": "Longer session context",
        },
    ]
