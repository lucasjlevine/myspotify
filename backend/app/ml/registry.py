from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from app.config import DATA_DIR
from app.ml.artist import ArtistPredictor
from app.ml.cooccurrence import CooccurrencePredictor
from app.ml.item_knn import ItemKnnPredictor
from app.ml.markov import MarkovPredictor
from app.ml.popularity import PopularityPredictor
from app.ml.protocol import NextSongPredictor

MODELS_DIR = DATA_DIR / "models"

Factory = Callable[[], NextSongPredictor]

REGISTRY: dict[str, Factory] = {
    "markov": MarkovPredictor,
    "popularity": PopularityPredictor,
    "artist": ArtistPredictor,
    "cooccurrence": CooccurrencePredictor,
    "item_knn": ItemKnnPredictor,
}

DEFAULT_MODEL_ID = "markov"


def list_model_ids() -> list[str]:
    return list(REGISTRY.keys())


def create_predictor(model_id: str) -> NextSongPredictor:
    try:
        factory = REGISTRY[model_id]
    except KeyError as exc:
        raise KeyError(f"unknown_model: {model_id}") from exc
    return factory()


def artifact_path(model_id: str) -> Path:
    if model_id == "item_knn":
        return MODELS_DIR / "item_knn.joblib"
    return MODELS_DIR / f"{model_id}.json"


def metadata_path(model_id: str) -> Path:
    """Sidecar JSON for models that use binary artifacts (item_knn)."""
    return MODELS_DIR / f"{model_id}.meta.json"


def is_trained(model_id: str) -> bool:
    path = artifact_path(model_id)
    if not path.exists():
        return False
    if model_id == "item_knn":
        return metadata_path(model_id).exists()
    return True
