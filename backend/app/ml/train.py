"""Train the Markov next-song baseline from accumulated plays.

Usage (from backend/):
    uv run python -m app.ml.train
"""

from __future__ import annotations

from app.database import init_db, session_scope
from app.ml.dataset import build_transitions, load_plays_chronological
from app.ml.markov import MarkovPredictor
from app.ml.service import model_path


def train(*, output_path=None) -> dict:
    init_db()
    artifact = output_path or model_path()

    with session_scope() as session:
        plays = load_plays_chronological(session)
        transitions = build_transitions(plays)

    if len(plays) < 2:
        raise SystemExit(
            "Need at least 2 stored plays to train. "
            "Run the server, authorize, and sync plays first."
        )

    predictor = MarkovPredictor()
    predictor.fit(transitions, n_plays=len(plays))
    predictor.save(artifact)

    summary = {
        "model_path": str(artifact),
        "n_plays": predictor.n_plays,
        "n_transitions": predictor.n_transitions,
        "trained_at": predictor.trained_at,
    }
    return summary


def main() -> None:
    summary = train()
    print(
        f"Trained Markov predictor: "
        f"{summary['n_transitions']} transitions from {summary['n_plays']} plays"
    )
    print(f"Wrote {summary['model_path']}")


if __name__ == "__main__":
    main()
