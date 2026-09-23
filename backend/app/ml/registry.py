from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from app.config import DATA_DIR
from app.ml.artist import ArtistPredictor
from app.ml.cooccurrence import CooccurrencePredictor
from app.ml.embedding import EmbeddingPredictor
from app.ml.item_knn import ItemKnnPredictor
from app.ml.markov import MarkovPredictor
from app.ml.popularity import PopularityPredictor
from app.ml.prompted import PromptedPredictor
from app.ml.protocol import NextSongPredictor

MODELS_DIR = DATA_DIR / "models"

Factory = Callable[[], NextSongPredictor]

REGISTRY: dict[str, Factory] = {
    "markov": MarkovPredictor,
    "popularity": PopularityPredictor,
    "artist": ArtistPredictor,
    "cooccurrence": CooccurrencePredictor,
    "item_knn": ItemKnnPredictor,
    "prompted": PromptedPredictor,
    "embedding": EmbeddingPredictor,
}

DEFAULT_MODEL_ID = "markov"

_BINARY_MODELS = {"item_knn", "prompted", "embedding"}


def list_model_ids() -> list[str]:
    return list(REGISTRY.keys())


def create_predictor(model_id: str) -> NextSongPredictor:
    try:
        factory = REGISTRY[model_id]
    except KeyError as exc:
        raise KeyError(f"unknown_model: {model_id}") from exc
    return factory()


def artifact_path(model_id: str) -> Path:
    if model_id in _BINARY_MODELS:
        return MODELS_DIR / f"{model_id}.joblib"
    return MODELS_DIR / f"{model_id}.json"


def metadata_path(model_id: str) -> Path:
    """Sidecar JSON for models that use binary artifacts."""
    return MODELS_DIR / f"{model_id}.meta.json"


def is_trained(model_id: str) -> bool:
    path = artifact_path(model_id)
    if not path.exists():
        return False
    if model_id in _BINARY_MODELS:
        return metadata_path(model_id).exists()
    return True
