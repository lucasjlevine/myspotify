from pathlib import Path
from typing import Protocol

Prediction = tuple[str, float]  # (track_id, score)
Transition = tuple[str, str]  # (from_track_id, to_track_id)


class NextSongPredictor(Protocol):
    def fit(self, transitions: list[Transition], *, n_plays: int) -> None: ...

    def predict(self, track_id: str, k: int = 5) -> list[Prediction]: ...

    def save(self, path: Path) -> None: ...

    @classmethod
    def load(cls, path: Path) -> "NextSongPredictor": ...
