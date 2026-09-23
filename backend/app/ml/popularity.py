from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import json

from app.ml.dataset import play_counts
from app.ml.protocol import PredictContext, Prediction, TrainingData


class PopularityPredictor:
    """Globally most-played tracks (excludes the seed track)."""

    model_id = "popularity"

    def __init__(self) -> None:
        self.counts: Counter[str] = Counter()
        self.trained_at: str | None = None
        self.n_plays: int = 0

    def fit(self, data: TrainingData) -> None:
        self.counts = play_counts(data.track_ids)
        self.n_plays = data.n_plays
        self.trained_at = datetime.now(timezone.utc).isoformat()

    def predict(self, context: PredictContext, k: int = 5) -> list[Prediction]:
        total = sum(self.counts.values()) or 1
        ranked = [
            (track_id, count / total)
            for track_id, count in self.counts.most_common(k + 1)
            if track_id != context.track_id
        ]
        return ranked[:k]

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "model_id": self.model_id,
                    "trained_at": self.trained_at,
                    "n_plays": self.n_plays,
                    "counts": dict(self.counts),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> PopularityPredictor:
        payload = json.loads(path.read_text(encoding="utf-8"))
        predictor = cls()
        predictor.trained_at = payload.get("trained_at")
        predictor.n_plays = int(payload.get("n_plays") or 0)
        predictor.counts = Counter(payload.get("counts") or {})
        return predictor
