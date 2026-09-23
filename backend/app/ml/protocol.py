from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


Prediction = tuple[str, float]  # (track_id, score)
Transition = tuple[str, str]  # (from_track_id, to_track_id)


@dataclass(frozen=True)
class PredictContext:
    track_id: str
    artist_names: str = ""
    album_name: str = ""
    played_at: str | None = None


@dataclass
class TrainingData:
    """Shared bundle built once from chronological plays."""

    track_ids: list[str]
    artist_names: list[str]
    album_names: list[str]
    played_ats: list[str]
    transitions: list[Transition]
    n_plays: int


class NextSongPredictor(Protocol):
    model_id: str

    def fit(self, data: TrainingData) -> None: ...

    def predict(self, context: PredictContext, k: int = 5) -> list[Prediction]: ...

    def save(self, path: Path) -> None: ...

    @classmethod
    def load(cls, path: Path) -> NextSongPredictor: ...
