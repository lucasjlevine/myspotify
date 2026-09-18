from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.models import Play, Token


def save_tokens(
    session: Session,
    *,
    access_token: str,
    refresh_token: str,
    expires_at: float,
) -> None:
    token = session.get(Token, 1)
    if token is None:
        session.add(
            Token(
                id=1,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at,
            )
        )
        return

    token.access_token = access_token
    token.refresh_token = refresh_token
    token.expires_at = expires_at


def get_tokens(session: Session) -> Token | None:
    return session.get(Token, 1)


def upsert_plays(session: Session, plays: list[dict]) -> tuple[int, int]:
    if not plays:
        return 0, 0

    collected_at = datetime.now(timezone.utc).isoformat()
    inserted = 0
    skipped = 0

    for play in plays:
        statement = (
            sqlite_insert(Play)
            .values(
                played_at=play["played_at"],
                track_id=play["track_id"],
                track_name=play["track_name"],
                artist_names=play["artist_names"],
                album_name=play["album_name"],
                duration_ms=play["duration_ms"],
                context_uri=play.get("context_uri"),
                collected_at=collected_at,
            )
            .on_conflict_do_nothing(index_elements=["played_at", "track_id"])
        )
        result = session.execute(statement)
        if result.rowcount:
            inserted += 1
        else:
            skipped += 1

    return inserted, skipped


def list_plays(session: Session, limit: int = 50) -> list[dict]:
    rows = session.scalars(
        select(Play).order_by(Play.played_at.desc()).limit(limit)
    ).all()
    return [
        {
            "played_at": row.played_at,
            "track_id": row.track_id,
            "track_name": row.track_name,
            "artist_names": row.artist_names,
            "album_name": row.album_name,
            "duration_ms": row.duration_ms,
            "context_uri": row.context_uri,
            "collected_at": row.collected_at,
        }
        for row in rows
    ]
