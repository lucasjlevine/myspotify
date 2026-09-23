from __future__ import annotations

from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ml.protocol import TrainingData, Transition
from app.models import Play

COOCCURRENCE_WINDOW = 5


def load_plays_chronological(session: Session) -> list[Play]:
    return list(
        session.scalars(select(Play).order_by(Play.played_at.asc())).all()
    )


def build_transitions(plays: list[Play]) -> list[Transition]:
    if len(plays) < 2:
        return []

    transitions: list[Transition] = []
    for previous, current in zip(plays, plays[1:]):
        if previous.track_id == current.track_id:
            continue
        transitions.append((previous.track_id, current.track_id))
    return transitions


def build_training_data(plays: list[Play]) -> TrainingData:
    return TrainingData(
        track_ids=[p.track_id for p in plays],
        artist_names=[p.artist_names for p in plays],
        album_names=[p.album_name for p in plays],
        played_ats=[p.played_at for p in plays],
        transitions=build_transitions(plays),
        n_plays=len(plays),
        track_names=[p.track_name for p in plays],
    )


def play_counts(track_ids: list[str]) -> Counter[str]:
    return Counter(track_ids)


def artist_track_counts(
    track_ids: list[str], artist_names: list[str]
) -> dict[str, Counter[str]]:
    """Map normalized artist key -> Counter of track_id play counts."""
    by_artist: dict[str, Counter[str]] = {}
    for track_id, artists in zip(track_ids, artist_names):
        key = (artists or "").strip().lower()
        if not key:
            continue
        by_artist.setdefault(key, Counter())[track_id] += 1
    return by_artist


def build_cooccurrence(
    track_ids: list[str], *, window: int = COOCCURRENCE_WINDOW
) -> dict[str, Counter[str]]:
    """Symmetric co-occurrence counts within ±window positions (excluding self)."""
    n = len(track_ids)
    co: dict[str, Counter[str]] = {}
    for i, track_id in enumerate(track_ids):
        left = max(0, i - window)
        right = min(n, i + window + 1)
        neighbor_counts = co.setdefault(track_id, Counter())
        for j in range(left, right):
            if j == i:
                continue
            other = track_ids[j]
            if other == track_id:
                continue
            neighbor_counts[other] += 1
    return co
