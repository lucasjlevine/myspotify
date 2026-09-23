"""Listening affinity scoring — resist sleep-loop / binge inflation.

A track left on repeat overnight should not dominate tops or popularity
models. We cap contributions per calendar day (UTC) and support Spotify-like
time ranges.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Play

# Spotify-aligned windows (approx.)
TIME_RANGE_DAYS: dict[str, int | None] = {
    "short_term": 28,  # ~4 weeks
    "medium_term": 180,  # ~6 months
    "long_term": None,  # all time
}

DEFAULT_DAILY_CAP = 3


def parse_played_at(value: str) -> datetime | None:
    try:
        text = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def cutoff_for_range(time_range: str) -> datetime | None:
    days = TIME_RANGE_DAYS.get(time_range)
    if days is None and time_range == "long_term":
        return None
    if days is None:
        raise ValueError(f"unknown_time_range:{time_range}")
    return datetime.now(timezone.utc) - timedelta(days=days)


def effective_track_scores(
    session: Session,
    *,
    time_range: str = "long_term",
    daily_cap: int = DEFAULT_DAILY_CAP,
) -> dict[str, float]:
    """track_id -> capped play score within the time window."""
    cutoff = cutoff_for_range(time_range)
    rows = session.execute(select(Play.track_id, Play.played_at)).all()

    # (track_id, day) -> count
    day_counts: dict[tuple[str, str], int] = defaultdict(int)
    for track_id, played_at in rows:
        dt = parse_played_at(played_at)
        if dt is None:
            continue
        if cutoff is not None and dt < cutoff:
            continue
        day = dt.date().isoformat()
        day_counts[(track_id, day)] += 1

    scores: dict[str, float] = defaultdict(float)
    for (track_id, _day), count in day_counts.items():
        scores[track_id] += float(min(count, daily_cap))
    return dict(scores)


def effective_artist_scores(
    session: Session,
    *,
    time_range: str = "long_term",
    daily_cap: int = DEFAULT_DAILY_CAP,
) -> dict[str, float]:
    """artist_names -> capped play score within the time window."""
    cutoff = cutoff_for_range(time_range)
    rows = session.execute(
        select(Play.artist_names, Play.track_id, Play.played_at)
    ).all()

    day_counts: dict[tuple[str, str], int] = defaultdict(int)
    for artist_names, _track_id, played_at in rows:
        dt = parse_played_at(played_at)
        if dt is None:
            continue
        if cutoff is not None and dt < cutoff:
            continue
        key = artist_names or ""
        day = dt.date().isoformat()
        day_counts[(key, day)] += 1

    scores: dict[str, float] = defaultdict(float)
    for (artist, _day), count in day_counts.items():
        scores[artist] += float(min(count, daily_cap))
    return dict(scores)


def capped_play_counts_for_training(
    track_ids: list[str],
    played_ats: list[str],
    *,
    daily_cap: int = DEFAULT_DAILY_CAP,
) -> dict[str, float]:
    """Same daily-cap logic for ML training (popularity, etc.)."""
    day_counts: dict[tuple[str, str], int] = defaultdict(int)
    for tid, played_at in zip(track_ids, played_ats, strict=False):
        dt = parse_played_at(played_at)
        day = dt.date().isoformat() if dt else "unknown"
        day_counts[(tid, day)] += 1
    scores: dict[str, float] = defaultdict(float)
    for (tid, _day), count in day_counts.items():
        scores[tid] += float(min(count, daily_cap))
    return dict(scores)
