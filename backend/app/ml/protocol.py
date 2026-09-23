from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


Prediction = tuple[str, float]  # (track_id, score)
Transition = tuple[str, str]  # (from_track_id, to_track_id)


@dataclass(frozen=True)
class PredictContext:
    """Inference context.

    `track_id` is the primary (most recent) seed. `recent_track_ids` is the
    full window oldest→newest (including primary). Prompted / sequence-aware
    models should prefer the window; single-seed models use `track_id`.
    """

    track_id: str
    artist_names: str = ""
    album_name: str = ""
    played_at: str | None = None
    recent_track_ids: tuple[str, ...] = ()
    recent_texts: tuple[str, ...] = ()


@dataclass
class TrainingData:
    """Shared bundle built once from chronological plays."""

    track_ids: list[str]
    artist_names: list[str]
    album_names: list[str]
    played_ats: list[str]
    transitions: list[Transition]
    n_plays: int
    track_names: list[str] = field(default_factory=list)


class NextSongPredictor(Protocol):
    model_id: str

    def fit(self, data: TrainingData) -> None: ...

    def predict(self, context: PredictContext, k: int = 5) -> list[Prediction]: ...

    def save(self, path: Path) -> None: ...

    @classmethod
    def load(cls, path: Path) -> NextSongPredictor: ...
