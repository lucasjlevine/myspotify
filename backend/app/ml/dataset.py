from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ml.protocol import Transition
from app.models import Play


def load_plays_chronological(session: Session) -> list[Play]:
    return list(
        session.scalars(select(Play).order_by(Play.played_at.asc())).all()
    )


def build_transitions(plays: list[Play]) -> list[Transition]:
    """Emit consecutive (from_track_id, to_track_id) pairs in play order."""
    if len(plays) < 2:
        return []

    transitions: list[Transition] = []
    for previous, current in zip(plays, plays[1:]):
        if previous.track_id == current.track_id:
            continue
        transitions.append((previous.track_id, current.track_id))
    return transitions
