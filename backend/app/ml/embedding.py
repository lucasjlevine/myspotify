"""Local hybrid embedding song-space (text + audio features).

Text: track/artist/album + genres + mood phrases derived from audio features.
Audio: 9-d feature vector concatenated onto the text embedding, then L2-normalized.

Free-text prompts ("Rainy fall day") hit the text subspace (padded with neutral
audio features) so moods land near tracks tagged with matching descriptors.
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
from app.database import session_scope
from app import repositories
from app.ml.protocol import PredictContext, Prediction, TrainingData
from app.spotify.catalog import (
    AUDIO_KEYS,
    audio_feature_vector,
    build_track_document,
)

DEFAULT_EMBED_MODEL = "BAAI/bge-small-en-v1.5"
_BATCH = 64
# Relative weight of the audio block vs text (after each is unit-length)
AUDIO_WEIGHT = 0.35
# Prompt search uses text subspace so mood phrases aren't diluted by neutral audio
PROMPT_TEXT_ONLY = True


def _get_embedder(model_name: str = DEFAULT_EMBED_MODEL):
    from fastembed import TextEmbedding

    return TextEmbedding(model_name=model_name)


def _embed_texts(embedder, texts: list[str]) -> np.ndarray:
    if not texts:
        return np.zeros((0, 0), dtype=np.float32)
    vectors = list(embedder.embed(texts, batch_size=_BATCH))
    matrix = np.asarray(vectors, dtype=np.float32)
    return normalize(matrix, norm="l2", axis=1)


def _hybridize(text_matrix: np.ndarray, audio_matrix: np.ndarray) -> np.ndarray:
    """Concatenate L2 text with scaled audio features, then re-normalize."""
    if text_matrix.size == 0:
        return text_matrix
    audio_n = normalize(audio_matrix.astype(np.float32), norm="l2", axis=1)
    scaled = audio_n * AUDIO_WEIGHT
    combined = np.concatenate([text_matrix, scaled], axis=1)
    return normalize(combined, norm="l2", axis=1)


def _meta_features_map(track_ids: list[str]) -> dict[str, dict]:
    with session_scope() as session:
        metas = repositories.get_track_meta_map(session, track_ids)
        out: dict[str, dict] = {}
        for tid, meta in metas.items():
            feats = {
                key: getattr(meta, key)
                for key in AUDIO_KEYS
                if getattr(meta, key, None) is not None
            }
            out[tid] = {
                "genres": meta.genres,
                "features": feats if feats else None,
            }
        return out


class EmbeddingPredictor:
    """Hybrid song-space with cosine NN + text prompt search."""

    model_id = "embedding"
    backend = "fastembed+audio"

    def __init__(self, *, model_name: str = DEFAULT_EMBED_MODEL) -> None:
        self.model_name = model_name
        self.index_track: list[str] = []
        self.track_index: dict[str, int] = {}
        self.matrix: np.ndarray | None = None
        self.documents: list[str] = []
        self.audio_matrix: np.ndarray | None = None
        self.nn: NearestNeighbors | None = None
        self.trained_at: str | None = None
        self.n_plays: int = 0
        self.n_tracks: int = 0
        self.dim: int = 0
        self.text_dim: int = 0
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

    def _prompt_vector(self, text: str) -> np.ndarray:
        embedder = self._ensure_embedder()
        text_vec = _embed_texts(embedder, [text])
        if text_vec.shape[0] == 0:
            return np.zeros((0,), dtype=np.float32)
        if PROMPT_TEXT_ONLY and self.matrix is not None and self.text_dim > 0:
            # Match against text dims only; zero audio so genres/moods dominate
            audio_dims = max(0, self.matrix.shape[1] - self.text_dim)
            pad = np.zeros((1, audio_dims), dtype=np.float32)
            combined = np.concatenate([text_vec, pad], axis=1)
            return normalize(combined, norm="l2", axis=1)[0]
        audio = np.asarray([audio_feature_vector(None)], dtype=np.float32)
        hybrid = _hybridize(text_vec, audio)
        return hybrid[0]

    def fit(self, data: TrainingData) -> None:
        names = data.track_names or [""] * len(data.track_ids)
        # Last-seen metadata per track
        meta_text: dict[str, tuple[str, str, str]] = {}
        for tid, artist, album, name in zip(
            data.track_ids,
            data.artist_names,
            data.album_names,
            names,
            strict=False,
        ):
            meta_text[tid] = (name or "", artist or "", album or "")

        self.index_track = sorted(meta_text.keys())
        self.track_index = {t: i for i, t in enumerate(self.index_track)}
        catalog = _meta_features_map(self.index_track)

        self.documents = []
        audio_rows: list[list[float]] = []
        for tid in self.index_track:
            name, artist, album = meta_text[tid]
            info = catalog.get(tid) or {}
            doc = build_track_document(
                name=name,
                artist=artist,
                album=album,
                genres=info.get("genres"),
                features=info.get("features"),
            )
            self.documents.append(doc)
            audio_rows.append(audio_feature_vector(info.get("features")))

        self.n_plays = data.n_plays
        self.n_tracks = len(self.index_track)

        if not self.documents:
            self.matrix = np.zeros((0, 0), dtype=np.float32)
            self.audio_matrix = np.zeros((0, 9), dtype=np.float32)
            self.nn = None
            self.dim = 0
            self.trained_at = datetime.now(timezone.utc).isoformat()
            return

        embedder = self._ensure_embedder()
        text_matrix = _embed_texts(embedder, self.documents)
        self.text_dim = int(text_matrix.shape[1])
        self.audio_matrix = np.asarray(audio_rows, dtype=np.float32)
        self.matrix = _hybridize(text_matrix, self.audio_matrix)
        self.dim = int(self.matrix.shape[1])
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
        seen: set[str] = set()
        for dist, idx in zip(distances[0], indices[0], strict=False):
            tid = self.index_track[int(idx)]
            if tid in exclude or tid in seen:
                continue
            seen.add(tid)
            ranked.append((tid, float(1.0 - dist)))
            if len(ranked) >= k:
                break
        return ranked

    def search_text(self, prompt: str, k: int = 10) -> list[Prediction]:
        text = (prompt or "").strip()
        if not text:
            return []
        query = self._prompt_vector(text)
        if query.size == 0:
            return []
        # Over-fetch then prefer tracks annotated with genres/moods
        pool = self._query_neighbors(query, max(k * 6, 30), exclude=set())
        if not pool:
            return []
        rescored: list[Prediction] = []
        for tid, score in pool:
            idx = self.track_index.get(tid)
            doc = self.documents[idx] if idx is not None else ""
            adj = float(score)
            if "Mood:" in doc:
                adj += 0.14
            if "Genres:" in doc:
                adj += 0.08
            if "Mood:" not in doc and "Genres:" not in doc:
                adj -= 0.06
            rescored.append((tid, adj))
        rescored.sort(key=lambda x: x[1], reverse=True)
        return rescored[:k]

    def project_space(
        self,
        prompt: str,
        *,
        k: int = 24,
        context: int = 48,
    ) -> dict:
        """PCA-project query + neighbors (+ background sample) into 2D.

        Returns normalized coords in [-1, 1] for constellation UIs.
        """
        from sklearn.decomposition import PCA

        text = (prompt or "").strip()
        if not text or self.matrix is None or self.matrix.shape[0] == 0:
            return {"query": text, "points": [], "edges": []}

        query = self._prompt_vector(text)
        if query.size == 0:
            return {"query": text, "points": [], "edges": []}

        neighbors = self.search_text(text, k=k)
        neighbor_ids = [tid for tid, _ in neighbors]
        neighbor_set = set(neighbor_ids)

        # Background dust: tracks far from the query for spatial contrast
        context_ids: list[str] = []
        if context > 0 and self.nn is not None:
            n_probe = min(self.matrix.shape[0], max(k + context + 20, 80))
            distances, indices = self.nn.kneighbors(
                query.reshape(1, -1), n_neighbors=n_probe
            )
            # Take from the farther half of the probe
            far = list(indices[0][::-1])
            for idx in far:
                tid = self.index_track[int(idx)]
                if tid in neighbor_set:
                    continue
                context_ids.append(tid)
                if len(context_ids) >= context:
                    break

        rows: list[np.ndarray] = [query]
        meta: list[dict] = [
            {
                "id": "__query__",
                "kind": "query",
                "label": text,
                "score": 1.0,
            }
        ]
        for tid, score in neighbors:
            idx = self.track_index.get(tid)
            if idx is None:
                continue
            rows.append(self.matrix[idx])
            doc = self.documents[idx] if idx < len(self.documents) else ""
            meta.append(
                {
                    "id": tid,
                    "kind": "neighbor",
                    "score": float(score),
                    "annotated": "Mood:" in doc or "Genres:" in doc,
                }
            )
        for tid in context_ids:
            idx = self.track_index.get(tid)
            if idx is None:
                continue
            rows.append(self.matrix[idx])
            # Cosine similarity to query for faint edges
            sim = float(np.dot(query, self.matrix[idx]))
            meta.append(
                {
                    "id": tid,
                    "kind": "context",
                    "score": sim,
                    "annotated": False,
                }
            )

        stacked = np.stack(rows, axis=0)
        n_comp = 2 if stacked.shape[0] >= 2 else 1
        coords = PCA(n_components=n_comp, random_state=0).fit_transform(stacked)
        if n_comp == 1:
            coords = np.concatenate(
                [coords, np.zeros((coords.shape[0], 1), dtype=coords.dtype)],
                axis=1,
            )
        # Center on the query, scale to roughly [-1, 1]
        coords = coords - coords[0]
        max_abs = float(np.max(np.abs(coords))) or 1.0
        coords = coords / max_abs

        points = []
        for i, info in enumerate(meta):
            points.append(
                {
                    **info,
                    "x": float(coords[i, 0]),
                    "y": float(coords[i, 1]),
                }
            )

        edges = []
        for p in points:
            if p["kind"] == "query":
                continue
            edges.append(
                {
                    "source": "__query__",
                    "target": p["id"],
                    "weight": float(p.get("score") or 0.0),
                    "kind": p["kind"],
                }
            )

        return {
            "query": text,
            "dim": self.dim,
            "text_dim": self.text_dim,
            "n_tracks": self.n_tracks,
            "points": points,
            "edges": edges,
        }

    def predict(self, context: PredictContext, k: int = 5) -> list[Prediction]:
        exclude = set(context.recent_track_ids) | {context.track_id}
        vectors: list[np.ndarray] = []

        for tid in context.recent_track_ids or (context.track_id,):
            idx = self.track_index.get(tid)
            if idx is not None and self.matrix is not None:
                vectors.append(self.matrix[idx])

        if not vectors and context.recent_texts:
            for text in context.recent_texts:
                if text.strip():
                    vectors.append(self._prompt_vector(text))

        if not vectors:
            return []

        stacked = np.stack(vectors, axis=0)
        weights = np.linspace(0.5, 1.0, num=stacked.shape[0], dtype=np.float32)
        weights = weights / weights.sum()
        query = normalize(
            (stacked * weights[:, None]).sum(axis=0, keepdims=True), norm="l2"
        )[0]
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
                "audio_matrix": self.audio_matrix,
                "documents": self.documents,
                "trained_at": self.trained_at,
                "n_plays": self.n_plays,
                "n_tracks": self.n_tracks,
                "dim": self.dim,
                "text_dim": self.text_dim,
                "audio_weight": AUDIO_WEIGHT,
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
            "text_dim": self.text_dim,
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
        obj.audio_matrix = payload.get("audio_matrix")
        obj.documents = payload.get("documents") or []
        obj.trained_at = payload.get("trained_at")
        obj.n_plays = int(payload.get("n_plays") or 0)
        obj.n_tracks = int(payload.get("n_tracks") or len(obj.index_track))
        obj.dim = int(
            payload.get("dim")
            or (
                obj.matrix.shape[1]
                if obj.matrix is not None and obj.matrix.size
                else 0
            )
        )
        obj.text_dim = int(payload.get("text_dim") or 0)
        obj._fit_nn()
        return obj
