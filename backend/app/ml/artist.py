from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import json

from app.ml.dataset import artist_track_counts
from app.ml.protocol import PredictContext, Prediction, TrainingData


class ArtistPredictor:
    """Other tracks by the same artist, ranked by play count."""

    model_id = "artist"

    def __init__(self) -> None:
        self.by_artist: dict[str, Counter[str]] = {}
        self.track_artists: dict[str, str] = {}
        self.global_counts: Counter[str] = Counter()
        self.trained_at: str | None = None
        self.n_plays: int = 0

    def fit(self, data: TrainingData) -> None:
        self.by_artist = artist_track_counts(data.track_ids, data.artist_names)
        self.track_artists = {}
        self.global_counts = Counter()
        for track_id, artists in zip(data.track_ids, data.artist_names):
            key = (artists or "").strip().lower()
            if key and track_id not in self.track_artists:
                self.track_artists[track_id] = key
            self.global_counts[track_id] += 1
        self.n_plays = data.n_plays
        self.trained_at = datetime.now(timezone.utc).isoformat()

    def predict(self, context: PredictContext, k: int = 5) -> list[Prediction]:
        artist_key = (context.artist_names or "").strip().lower()
        if not artist_key:
            artist_key = self.track_artists.get(context.track_id, "")

        counts = self.by_artist.get(artist_key) if artist_key else None
        if not counts:
            total = sum(self.global_counts.values()) or 1
            return [
                (t, c / total)
                for t, c in self.global_counts.most_common(k + 1)
                if t != context.track_id
            ][:k]

        total = sum(counts.values()) or 1
        return [
            (t, c / total)
            for t, c in counts.most_common(k + 1)
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
                    "by_artist": {a: dict(c) for a, c in self.by_artist.items()},
                    "track_artists": self.track_artists,
                    "global_counts": dict(self.global_counts),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> ArtistPredictor:
        payload = json.loads(path.read_text(encoding="utf-8"))
        predictor = cls()
        predictor.trained_at = payload.get("trained_at")
        predictor.n_plays = int(payload.get("n_plays") or 0)
        predictor.by_artist = {
            a: Counter(c) for a, c in (payload.get("by_artist") or {}).items()
        }
        predictor.track_artists = dict(payload.get("track_artists") or {})
        predictor.global_counts = Counter(payload.get("global_counts") or {})
        return predictor
