"""Local prompt-conditioned next-song ranker (TF-IDF).

Builds a text "prompt" from the recent listening window and ranks catalog
tracks by cosine similarity. No cloud calls — expandable later to a local
LLM backend that consumes the same prompt builder.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.config import DATA_DIR
from app.database import session_scope
from app import repositories
from app.ml.protocol import PredictContext, Prediction, TrainingData
from app.spotify.catalog import AUDIO_KEYS, build_track_document


def track_document(artist: str, album: str, name: str = "") -> str:
    return build_track_document(name=name, artist=artist, album=album).lower()


def _enriched_docs(track_ids: list[str]) -> dict[str, dict]:
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


def build_listening_prompt(texts: tuple[str, ...] | list[str]) -> str:
    """Turn a window of track texts into a single prompt string.

    Recency bias: later items are repeated so the vector leans current mood.
    """
    if not texts:
        return ""
    chunks: list[str] = []
    n = len(texts)
    for i, text in enumerate(texts):
        weight = 1 + (i // max(1, n // 4))
        chunks.extend([text] * weight)
    return " | ".join(chunks)


class PromptedPredictor:
    """TF-IDF prompt ranker — local, trainable, LLM-swappable later."""

    model_id = "prompted"
    backend = "tfidf"  # future: "ollama", etc.

    def __init__(self) -> None:
        self.vectorizer: TfidfVectorizer | None = None
        self.matrix = None
        self.index_track: list[str] = []
        self.track_index: dict[str, int] = {}
        self.trained_at: str | None = None
        self.n_plays: int = 0
        self.n_tracks: int = 0

    def fit(self, data: TrainingData) -> None:
        # One document per unique track (last-seen metadata wins).
        docs: dict[str, str] = {}
        names = data.track_names or [""] * len(data.track_ids)
        meta_text: dict[str, tuple[str, str, str]] = {}
        for tid, artist, album, name in zip(
            data.track_ids,
            data.artist_names,
            data.album_names,
            names,
            strict=False,
        ):
            meta_text[tid] = (name or "", artist or "", album or "")

        catalog = _enriched_docs(list(meta_text.keys()))
        for tid, (name, artist, album) in meta_text.items():
            info = catalog.get(tid) or {}
            docs[tid] = build_track_document(
                name=name,
                artist=artist,
                album=album,
                genres=info.get("genres"),
                features=info.get("features"),
            ).lower()

        self.index_track = sorted(docs.keys())
        self.track_index = {t: i for i, t in enumerate(self.index_track)}
        corpus = [docs[t] for t in self.index_track]

        if not corpus:
            self.vectorizer = None
            self.matrix = None
            self.n_plays = data.n_plays
            self.n_tracks = 0
            self.trained_at = datetime.now(timezone.utc).isoformat()
            return

        self.vectorizer = TfidfVectorizer(
            max_features=20_000,
            ngram_range=(1, 2),
            min_df=1,
        )
        self.matrix = self.vectorizer.fit_transform(corpus)
        self.n_plays = data.n_plays
        self.n_tracks = len(self.index_track)
        self.trained_at = datetime.now(timezone.utc).isoformat()

    def predict(self, context: PredictContext, k: int = 5) -> list[Prediction]:
        if self.vectorizer is None or self.matrix is None or not self.index_track:
            return []

        seed_texts = list(context.recent_texts) if context.recent_texts else []
        if not seed_texts:
            seed_texts = [
                track_document(context.artist_names, context.album_name, "")
            ]
        prompt = build_listening_prompt(seed_texts)
        if not prompt.strip():
            return []

        query = self.vectorizer.transform([prompt])
        sims = cosine_similarity(query, self.matrix).ravel()

        exclude = set(context.recent_track_ids) | {context.track_id}
        ranked: list[Prediction] = []
        for idx in sims.argsort()[::-1]:
            tid = self.index_track[idx]
            if tid in exclude:
                continue
            ranked.append((tid, float(sims[idx])))
            if len(ranked) >= k:
                break
        return ranked

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "model_id": self.model_id,
                "backend": self.backend,
                "vectorizer": self.vectorizer,
                "matrix": self.matrix,
                "index_track": self.index_track,
                "trained_at": self.trained_at,
                "n_plays": self.n_plays,
                "n_tracks": self.n_tracks,
            },
            path,
        )
        meta = {
            "model_id": self.model_id,
            "backend": self.backend,
            "trained_at": self.trained_at,
            "n_plays": self.n_plays,
            "n_tracks": self.n_tracks,
        }
        (DATA_DIR / "models" / f"{self.model_id}.meta.json").write_text(
            json.dumps(meta, indent=2), encoding="utf-8"
        )

    @classmethod
    def load(cls, path: Path) -> PromptedPredictor:
        payload = joblib.load(path)
        obj = cls()
        obj.vectorizer = payload.get("vectorizer")
        obj.matrix = payload.get("matrix")
        obj.index_track = payload.get("index_track") or []
        obj.track_index = {t: i for i, t in enumerate(obj.index_track)}
        obj.trained_at = payload.get("trained_at")
        obj.n_plays = int(payload.get("n_plays") or 0)
        obj.n_tracks = int(payload.get("n_tracks") or len(obj.index_track))
        return obj
