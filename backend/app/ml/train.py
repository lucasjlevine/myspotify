"""Train next-song predictors from accumulated plays.

Usage (from backend/):
    uv run python -m app.ml.train
    uv run python -m app.ml.train --model markov
    uv run python -m app.ml.train --model all
"""

from __future__ import annotations

import argparse

from app.database import init_db, session_scope
from app.ml.dataset import build_training_data, load_plays_chronological
from app.ml.registry import (
    artifact_path,
    create_predictor,
    list_model_ids,
)


def train_models(model_ids: list[str]) -> list[dict]:
    init_db()
    with session_scope() as session:
        plays = load_plays_chronological(session)
        if len(plays) < 2:
            raise SystemExit(
                "Need at least 2 stored plays to train. "
                "Import history or sync recently-played first."
            )
        data = build_training_data(plays)

    summaries: list[dict] = []

    for model_id in model_ids:
        predictor = create_predictor(model_id)
        predictor.fit(data)
        path = artifact_path(model_id)
        predictor.save(path)
        summaries.append(
            {
                "model_id": model_id,
                "model_path": str(path),
                "n_plays": getattr(predictor, "n_plays", data.n_plays),
                "n_transitions": getattr(predictor, "n_transitions", None),
                "trained_at": getattr(predictor, "trained_at", None),
            }
        )
    return summaries


def main() -> None:
    parser = argparse.ArgumentParser(description="Train next-song predictors")
    parser.add_argument(
        "--model",
        default="all",
        help=f"Model id or 'all' (available: {', '.join(list_model_ids())})",
    )
    args = parser.parse_args()

    if args.model == "all":
        model_ids = list_model_ids()
    else:
        if args.model not in list_model_ids():
            raise SystemExit(
                f"Unknown model {args.model!r}. Choose from {list_model_ids()} or 'all'."
            )
        model_ids = [args.model]

    summaries = train_models(model_ids)
    for summary in summaries:
        extra = ""
        if summary.get("n_transitions") is not None:
            extra = f", {summary['n_transitions']} transitions"
        print(
            f"[{summary['model_id']}] n_plays={summary['n_plays']}{extra} "
            f"-> {summary['model_path']}"
        )


if __name__ == "__main__":
    main()
