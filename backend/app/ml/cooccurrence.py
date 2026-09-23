from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import json

from app.ml.dataset import COOCCURRENCE_WINDOW, build_cooccurrence, play_counts
from app.ml.protocol import PredictContext, Prediction, TrainingData


class CooccurrencePredictor:
    """Tracks that co-appear within a sliding play window."""

    model_id = "cooccurrence"

    def __init__(self, *, window: int = COOCCURRENCE_WINDOW) -> None:
        self.window = window
        self.cooccurrence: dict[str, Counter[str]] = {}
        self.global_counts: Counter[str] = Counter()
        self.trained_at: str | None = None
        self.n_plays: int = 0

    def fit(self, data: TrainingData) -> None:
        self.cooccurrence = build_cooccurrence(data.track_ids, window=self.window)
        self.global_counts = play_counts(data.track_ids)
        self.n_plays = data.n_plays
        self.trained_at = datetime.now(timezone.utc).isoformat()

    def predict(self, context: PredictContext, k: int = 5) -> list[Prediction]:
        counts = self.cooccurrence.get(context.track_id)
        if counts:
            total = sum(counts.values()) or 1
            return [
                (t, c / total)
                for t, c in counts.most_common(k + 1)
                if t != context.track_id
            ][:k]

        total = sum(self.global_counts.values()) or 1
        return [
            (t, c / total)
            for t, c in self.global_counts.most_common(k + 1)
            if t != context.track_id
        ][:k]

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "model_id": self.model_id,
                    "trained_at": self.trained_at,
                    "n_plays": self.n_plays,
                    "window": self.window,
                    "cooccurrence": {
                        k: dict(v) for k, v in self.cooccurrence.items()
                    },
                    "global_counts": dict(self.global_counts),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> CooccurrencePredictor:
        payload = json.loads(path.read_text(encoding="utf-8"))
        predictor = cls(window=int(payload.get("window") or COOCCURRENCE_WINDOW))
        predictor.trained_at = payload.get("trained_at")
        predictor.n_plays = int(payload.get("n_plays") or 0)
        predictor.cooccurrence = {
            k: Counter(v) for k, v in (payload.get("cooccurrence") or {}).items()
        }
        predictor.global_counts = Counter(payload.get("global_counts") or {})
        return predictor
