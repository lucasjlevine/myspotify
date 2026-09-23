from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import json

from app.listening import capped_play_counts_for_training
from app.ml.protocol import PredictContext, Prediction, TrainingData


class PopularityPredictor:
    """Most-played tracks using daily-capped counts (resists sleep loops)."""

    model_id = "popularity"

    def __init__(self) -> None:
        self.counts: Counter[str] = Counter()
        self.trained_at: str | None = None
        self.n_plays: int = 0

    def fit(self, data: TrainingData) -> None:
        capped = capped_play_counts_for_training(data.track_ids, data.played_ats)
        self.counts = Counter({k: int(v) for k, v in capped.items()})
        self.n_plays = int(sum(self.counts.values()))
        self.trained_at = datetime.now(timezone.utc).isoformat()

    def predict(self, context: PredictContext, k: int = 5) -> list[Prediction]:
        total = sum(self.counts.values()) or 1
        exclude = set(context.recent_track_ids) | {context.track_id}
        ranked = [
            (track_id, count / total)
            for track_id, count in self.counts.most_common(k + len(exclude) + 5)
            if track_id not in exclude
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
                    "scoring": "daily_cap_3",
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
