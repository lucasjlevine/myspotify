from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import json

from app.ml.protocol import Prediction, Transition


class MarkovPredictor:
    """Next-track predictor using empirical first-order transition counts."""

    def __init__(self) -> None:
        self.transitions: dict[str, Counter[str]] = {}
        self.global_counts: Counter[str] = Counter()
        self.trained_at: str | None = None
        self.n_plays: int = 0
        self.n_transitions: int = 0

    def fit(self, transitions: list[Transition], *, n_plays: int) -> None:
        self.transitions = {}
        self.global_counts = Counter()
        for from_id, to_id in transitions:
            self.transitions.setdefault(from_id, Counter())[to_id] += 1
            self.global_counts[to_id] += 1

        self.n_plays = n_plays
        self.n_transitions = len(transitions)
        self.trained_at = datetime.now(timezone.utc).isoformat()

    def predict(self, track_id: str, k: int = 5) -> list[Prediction]:
        counts = self.transitions.get(track_id)
        if counts:
            total = sum(counts.values())
            ranked = counts.most_common(k)
            return [(track, count / total) for track, count in ranked]

        if not self.global_counts:
            return []

        total = sum(self.global_counts.values())
        ranked = self.global_counts.most_common(k)
        return [(track, count / total) for track, count in ranked]

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "trained_at": self.trained_at,
            "n_plays": self.n_plays,
            "n_transitions": self.n_transitions,
            "transitions": {
                from_id: dict(counter) for from_id, counter in self.transitions.items()
            },
            "global_counts": dict(self.global_counts),
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "MarkovPredictor":
        payload = json.loads(path.read_text(encoding="utf-8"))
        predictor = cls()
        predictor.trained_at = payload.get("trained_at")
        predictor.n_plays = int(payload.get("n_plays") or 0)
        predictor.n_transitions = int(payload.get("n_transitions") or 0)
        predictor.transitions = {
            from_id: Counter(to_counts)
            for from_id, to_counts in (payload.get("transitions") or {}).items()
        }
        predictor.global_counts = Counter(payload.get("global_counts") or {})
        return predictor
