from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import json

import joblib
from scipy import sparse
from sklearn.neighbors import NearestNeighbors

from app.config import DATA_DIR
from app.ml.dataset import COOCCURRENCE_WINDOW, build_cooccurrence, play_counts
from app.ml.protocol import PredictContext, Prediction, TrainingData


class ItemKnnPredictor:
    """Cosine kNN over sparse track co-occurrence vectors."""

    model_id = "item_knn"

    def __init__(self, *, window: int = COOCCURRENCE_WINDOW, n_neighbors: int = 50) -> None:
        self.window = window
        self.n_neighbors = n_neighbors
        self.track_index: dict[str, int] = {}
        self.index_track: list[str] = []
        self.matrix: sparse.csr_matrix | None = None
        self.nn: NearestNeighbors | None = None
        self.global_counts: Counter[str] = Counter()
        self.trained_at: str | None = None
        self.n_plays: int = 0

    def fit(self, data: TrainingData) -> None:
        co = build_cooccurrence(data.track_ids, window=self.window)
        self.global_counts = play_counts(data.track_ids)
        self.index_track = sorted(co.keys())
        self.track_index = {t: i for i, t in enumerate(self.index_track)}
        n = len(self.index_track)

        if n == 0:
            self.matrix = sparse.csr_matrix((0, 0))
            self.nn = None
            self.n_plays = data.n_plays
            self.trained_at = datetime.now(timezone.utc).isoformat()
            return

        rows: list[int] = []
        cols: list[int] = []
        vals: list[float] = []
        for track_id, neighbors in co.items():
            i = self.track_index[track_id]
            for other, count in neighbors.items():
                j = self.track_index.get(other)
                if j is None:
                    continue
                rows.append(i)
                cols.append(j)
                vals.append(float(count))

        self.matrix = sparse.csr_matrix((vals, (rows, cols)), shape=(n, n))
        # Add tiny self-weight so isolated rows are non-zero for cosine.
        self.matrix = self.matrix + sparse.eye(n, format="csr") * 1e-6

        n_neighbors = min(self.n_neighbors, n)
        self.nn = NearestNeighbors(
            n_neighbors=n_neighbors, metric="cosine", algorithm="brute"
        )
        self.nn.fit(self.matrix)
        self.n_plays = data.n_plays
        self.trained_at = datetime.now(timezone.utc).isoformat()

    def predict(self, context: PredictContext, k: int = 5) -> list[Prediction]:
        idx = self.track_index.get(context.track_id)
        if idx is None or self.nn is None or self.matrix is None or self.matrix.shape[0] == 0:
            total = sum(self.global_counts.values()) or 1
            return [
                (t, c / total)
                for t, c in self.global_counts.most_common(k + 1)
                if t != context.track_id
            ][:k]

        distances, indices = self.nn.kneighbors(
            self.matrix[idx], n_neighbors=min(k + 1, self.matrix.shape[0])
        )
        results: list[Prediction] = []
        for dist, neighbor_idx in zip(distances[0], indices[0]):
            track_id = self.index_track[int(neighbor_idx)]
            if track_id == context.track_id:
                continue
            # cosine distance -> similarity in [0, 1] roughly
            score = float(1.0 - dist)
            results.append((track_id, max(score, 0.0)))
            if len(results) >= k:
                break
        return results

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "window": self.window,
                "n_neighbors": self.n_neighbors,
                "track_index": self.track_index,
                "index_track": self.index_track,
                "matrix": self.matrix,
                "nn": self.nn,
                "global_counts": dict(self.global_counts),
                "trained_at": self.trained_at,
                "n_plays": self.n_plays,
            },
            path,
        )
        meta = DATA_DIR / "models" / f"{self.model_id}.meta.json"
        meta.write_text(
            json.dumps(
                {
                    "model_id": self.model_id,
                    "trained_at": self.trained_at,
                    "n_plays": self.n_plays,
                    "n_tracks": len(self.index_track),
                    "window": self.window,
                    "artifact": path.name,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> ItemKnnPredictor:
        payload = joblib.load(path)
        predictor = cls(
            window=int(payload.get("window") or COOCCURRENCE_WINDOW),
            n_neighbors=int(payload.get("n_neighbors") or 50),
        )
        predictor.track_index = dict(payload.get("track_index") or {})
        predictor.index_track = list(payload.get("index_track") or [])
        predictor.matrix = payload.get("matrix")
        predictor.nn = payload.get("nn")
        predictor.global_counts = Counter(payload.get("global_counts") or {})
        predictor.trained_at = payload.get("trained_at")
        predictor.n_plays = int(payload.get("n_plays") or 0)
        return predictor
