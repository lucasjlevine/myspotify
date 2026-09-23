from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.models import Play, Token

UPSERT_BATCH_SIZE = 1000


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

    for start in range(0, len(plays), UPSERT_BATCH_SIZE):
        batch = plays[start : start + UPSERT_BATCH_SIZE]
        rows = [
            {
                "played_at": play["played_at"],
                "track_id": play["track_id"],
                "track_name": play["track_name"],
                "artist_names": play["artist_names"],
                "album_name": play["album_name"],
                "duration_ms": play["duration_ms"],
                "context_uri": play.get("context_uri"),
                "collected_at": collected_at,
            }
            for play in batch
        ]
        statement = (
            sqlite_insert(Play)
            .values(rows)
            .on_conflict_do_nothing(index_elements=["played_at", "track_id"])
        )
        result = session.execute(statement)
        inserted += int(result.rowcount or 0)

    skipped = len(plays) - inserted
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


def count_plays(session: Session) -> int:
    return int(session.scalar(select(func.count()).select_from(Play)) or 0)


def get_play_by_track_id(session: Session, track_id: str) -> dict | None:
    row = session.scalars(
        select(Play)
        .where(Play.track_id == track_id)
        .order_by(Play.played_at.desc())
        .limit(1)
    ).first()
    if row is None:
        return None
    return {
        "played_at": row.played_at,
        "track_id": row.track_id,
        "track_name": row.track_name,
        "artist_names": row.artist_names,
        "album_name": row.album_name,
        "duration_ms": row.duration_ms,
        "context_uri": row.context_uri,
        "collected_at": row.collected_at,
    }


def stats_summary(session: Session) -> dict:
    total_plays = count_plays(session)
    unique_tracks = int(
        session.scalar(select(func.count(func.distinct(Play.track_id)))) or 0
    )
    unique_artists = int(
        session.scalar(select(func.count(func.distinct(Play.artist_names)))) or 0
    )
    first_played_at = session.scalar(select(func.min(Play.played_at)))
    last_played_at = session.scalar(select(func.max(Play.played_at)))
    total_ms = int(session.scalar(select(func.coalesce(func.sum(Play.duration_ms), 0))) or 0)
    return {
        "total_plays": total_plays,
        "unique_tracks": unique_tracks,
        "unique_artists": unique_artists,
        "first_played_at": first_played_at,
        "last_played_at": last_played_at,
        "total_ms": total_ms,
    }


def top_tracks(session: Session, limit: int = 10) -> list[dict]:
    rows = session.execute(
        select(
            Play.track_id,
            Play.track_name,
            Play.artist_names,
            Play.album_name,
            func.count().label("play_count"),
        )
        .group_by(Play.track_id)
        .order_by(func.count().desc())
        .limit(limit)
    ).all()
    return [
        {
            "track_id": row.track_id,
            "track_name": row.track_name,
            "artist_names": row.artist_names,
            "album_name": row.album_name,
            "play_count": int(row.play_count),
        }
        for row in rows
    ]


def top_artists(session: Session, limit: int = 10) -> list[dict]:
    rows = session.execute(
        select(
            Play.artist_names,
            func.count().label("play_count"),
            func.count(func.distinct(Play.track_id)).label("unique_tracks"),
        )
        .group_by(Play.artist_names)
        .order_by(func.count().desc())
        .limit(limit)
    ).all()
    return [
        {
            "artist_names": row.artist_names,
            "play_count": int(row.play_count),
            "unique_tracks": int(row.unique_tracks),
        }
        for row in rows
    ]


def listening_by_hour(session: Session) -> list[dict]:
    # played_at is ISO8601; substr positions 12-13 are the hour for "YYYY-MM-DDTHH:..."
    hour_expr = func.substr(Play.played_at, 12, 2)
    rows = session.execute(
        select(hour_expr.label("hour"), func.count().label("play_count"))
        .group_by(hour_expr)
        .order_by(hour_expr)
    ).all()
    counts = {int(row.hour): int(row.play_count) for row in rows if row.hour and row.hour.isdigit()}
    return [{"hour": hour, "play_count": counts.get(hour, 0)} for hour in range(24)]


def listening_by_day(session: Session, days: int = 30) -> list[dict]:
    day_expr = func.substr(Play.played_at, 1, 10)
    rows = session.execute(
        select(day_expr.label("day"), func.count().label("play_count"))
        .group_by(day_expr)
        .order_by(day_expr.desc())
        .limit(days)
    ).all()
    # Return chronological ascending for charts
    items = [
        {"day": row.day, "play_count": int(row.play_count)}
        for row in rows
        if row.day
    ]
    items.reverse()
    return items
