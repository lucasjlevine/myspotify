"""Local embedding song-space (fastembed ONNX).

Builds a vector for each unique track from metadata text, then:
- nearest neighbors for listening-window seeds
- free-text prompt search ("Rainy fall day") in the same space

Expandable later: richer docs (genres, lyrics snippets), Faiss/HNSW index,
or swap the embedder for a larger local model.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json

import joblib
import numpy as np
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import normalize

from app.config import DATA_DIR
from app.ml.protocol import PredictContext, Prediction, TrainingData

DEFAULT_EMBED_MODEL = "BAAI/bge-small-en-v1.5"
_BATCH = 64


def track_document(name: str, artist: str, album: str) -> str:
    """Compact text we embed per track — keep in sync with prompt phrasing."""
    parts = [
        (name or "").strip(),
        (artist or "").strip(),
        (album or "").strip(),
    ]
    # Light mood-ish cues from titles/albums help phrase queries land nearby
    return " — ".join(p for p in parts if p)


def _get_embedder(model_name: str = DEFAULT_EMBED_MODEL):
    from fastembed import TextEmbedding

    return TextEmbedding(model_name=model_name)


def _embed_texts(embedder, texts: list[str]) -> np.ndarray:
    if not texts:
        return np.zeros((0, 0), dtype=np.float32)
    vectors = list(embedder.embed(texts, batch_size=_BATCH))
    matrix = np.asarray(vectors, dtype=np.float32)
    return normalize(matrix, norm="l2", axis=1)


class EmbeddingPredictor:
    """Dense song-space with cosine nearest neighbors + text prompt search."""

    model_id = "embedding"
    backend = "fastembed"

    def __init__(self, *, model_name: str = DEFAULT_EMBED_MODEL) -> None:
        self.model_name = model_name
        self.index_track: list[str] = []
        self.track_index: dict[str, int] = {}
        self.matrix: np.ndarray | None = None
        self.documents: list[str] = []
        self.nn: NearestNeighbors | None = None
        self.trained_at: str | None = None
        self.n_plays: int = 0
        self.n_tracks: int = 0
        self.dim: int = 0
        self._embedder = None

    def _ensure_embedder(self):
        if self._embedder is None:
            self._embedder = _get_embedder(self.model_name)
        return self._embedder

    def _fit_nn(self) -> None:
        if self.matrix is None or self.matrix.shape[0] == 0:
            self.nn = None
            return
        n_neighbors = min(50, self.matrix.shape[0])
        self.nn = NearestNeighbors(
            n_neighbors=n_neighbors, metric="cosine", algorithm="brute"
        )
        self.nn.fit(self.matrix)

    def fit(self, data: TrainingData) -> None:
        docs: dict[str, str] = {}
        names = data.track_names or [""] * len(data.track_ids)
        for tid, artist, album, name in zip(
            data.track_ids,
            data.artist_names,
            data.album_names,
            names,
            strict=False,
        ):
            docs[tid] = track_document(name, artist, album)

        self.index_track = sorted(docs.keys())
        self.track_index = {t: i for i, t in enumerate(self.index_track)}
        self.documents = [docs[t] for t in self.index_track]
        self.n_plays = data.n_plays
        self.n_tracks = len(self.index_track)

        if not self.documents:
            self.matrix = np.zeros((0, 0), dtype=np.float32)
            self.nn = None
            self.dim = 0
            self.trained_at = datetime.now(timezone.utc).isoformat()
            return

        embedder = self._ensure_embedder()
        self.matrix = _embed_texts(embedder, self.documents)
        self.dim = int(self.matrix.shape[1]) if self.matrix.size else 0
        self._fit_nn()
        self.trained_at = datetime.now(timezone.utc).isoformat()

    def _query_neighbors(
        self,
        query: np.ndarray,
        k: int,
        *,
        exclude: set[str],
    ) -> list[Prediction]:
        if (
            self.nn is None
            or self.matrix is None
            or self.matrix.shape[0] == 0
            or query.size == 0
        ):
            return []

        n = min(max(k + len(exclude) + 5, k), self.matrix.shape[0])
        distances, indices = self.nn.kneighbors(query.reshape(1, -1), n_neighbors=n)
        ranked: list[Prediction] = []
        for dist, idx in zip(distances[0], indices[0], strict=False):
            tid = self.index_track[int(idx)]
            if tid in exclude:
                continue
            # cosine distance → similarity
            score = float(1.0 - dist)
            ranked.append((tid, score))
            if len(ranked) >= k:
                break
        return ranked

    def search_text(self, prompt: str, k: int = 10) -> list[Prediction]:
        """Embed a free-text mood/phrase and return nearest tracks."""
        text = (prompt or "").strip()
        if not text:
            return []
        embedder = self._ensure_embedder()
        query = _embed_texts(embedder, [text])
        if query.shape[0] == 0:
            return []
        return self._query_neighbors(query[0], k, exclude=set())

    def predict(self, context: PredictContext, k: int = 5) -> list[Prediction]:
        exclude = set(context.recent_track_ids) | {context.track_id}
        vectors: list[np.ndarray] = []

        # Prefer vectors already in the catalog for seed tracks
        for tid in context.recent_track_ids or (context.track_id,):
            idx = self.track_index.get(tid)
            if idx is not None and self.matrix is not None:
                vectors.append(self.matrix[idx])

        # Fall back / blend with seed text docs
        if not vectors and context.recent_texts:
            embedder = self._ensure_embedder()
            texts = [t for t in context.recent_texts if t.strip()]
            if texts:
                embedded = _embed_texts(embedder, texts)
                vectors.extend(list(embedded))

        if not vectors and (context.artist_names or context.album_name):
            embedder = self._ensure_embedder()
            doc = track_document("", context.artist_names, context.album_name)
            embedded = _embed_texts(embedder, [doc])
            if embedded.shape[0]:
                vectors.append(embedded[0])

        if not vectors:
            return []

        # Recency-weighted mean in embedding space
        stacked = np.stack(vectors, axis=0)
        weights = np.linspace(0.5, 1.0, num=stacked.shape[0], dtype=np.float32)
        weights = weights / weights.sum()
        query = normalize((stacked * weights[:, None]).sum(axis=0, keepdims=True), norm="l2")[0]
        return self._query_neighbors(query, k, exclude=exclude)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "model_id": self.model_id,
                "backend": self.backend,
                "model_name": self.model_name,
                "index_track": self.index_track,
                "matrix": self.matrix,
                "documents": self.documents,
                "trained_at": self.trained_at,
                "n_plays": self.n_plays,
                "n_tracks": self.n_tracks,
                "dim": self.dim,
            },
            path,
        )
        meta = {
            "model_id": self.model_id,
            "backend": self.backend,
            "model_name": self.model_name,
            "trained_at": self.trained_at,
            "n_plays": self.n_plays,
            "n_tracks": self.n_tracks,
            "dim": self.dim,
        }
        (DATA_DIR / "models" / f"{self.model_id}.meta.json").write_text(
            json.dumps(meta, indent=2), encoding="utf-8"
        )

    @classmethod
    def load(cls, path: Path) -> EmbeddingPredictor:
        payload = joblib.load(path)
        obj = cls(model_name=payload.get("model_name") or DEFAULT_EMBED_MODEL)
        obj.index_track = payload.get("index_track") or []
        obj.track_index = {t: i for i, t in enumerate(obj.index_track)}
        obj.matrix = payload.get("matrix")
        obj.documents = payload.get("documents") or []
        obj.trained_at = payload.get("trained_at")
        obj.n_plays = int(payload.get("n_plays") or 0)
        obj.n_tracks = int(payload.get("n_tracks") or len(obj.index_track))
        obj.dim = int(payload.get("dim") or (obj.matrix.shape[1] if obj.matrix is not None and obj.matrix.size else 0))
        obj._fit_nn()
        return obj
