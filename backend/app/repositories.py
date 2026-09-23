from datetime import datetime, timedelta, timezone
from collections import Counter

from sqlalchemy import func, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.listening import (
    DEFAULT_DAILY_CAP,
    TIME_RANGE_DAYS,
    effective_artist_scores,
    effective_track_scores,
    parse_played_at,
)
from app.models import Play, Token, TrackMeta

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


def _play_row(play: dict, collected_at: str) -> dict:
    return {
        "played_at": play["played_at"],
        "track_id": play["track_id"],
        "track_name": play["track_name"],
        "artist_names": play["artist_names"],
        "album_name": play["album_name"],
        "duration_ms": play["duration_ms"],
        "context_uri": play.get("context_uri"),
        "collected_at": collected_at,
        "album_image_url": play.get("album_image_url"),
    }


def upsert_plays(session: Session, plays: list[dict]) -> tuple[int, int]:
    if not plays:
        return 0, 0

    collected_at = datetime.now(timezone.utc).isoformat()
    inserted = 0

    for start in range(0, len(plays), UPSERT_BATCH_SIZE):
        batch = plays[start : start + UPSERT_BATCH_SIZE]
        rows = [_play_row(play, collected_at) for play in batch]
        statement = (
            sqlite_insert(Play)
            .values(rows)
            .on_conflict_do_nothing(index_elements=["played_at", "track_id"])
        )
        result = session.execute(statement)
        inserted += int(result.rowcount or 0)

    skipped = len(plays) - inserted
    return inserted, skipped


def fill_missing_album_images(session: Session, plays: list[dict]) -> int:
    """Backfill album_image_url for existing rows of these tracks when missing."""
    updated = 0
    for play in plays:
        url = play.get("album_image_url")
        tid = play.get("track_id")
        if not url or not tid:
            continue
        result = session.execute(
            update(Play)
            .where(Play.track_id == tid)
            .where(
                (Play.album_image_url.is_(None)) | (Play.album_image_url == "")
            )
            .values(album_image_url=url)
        )
        updated += int(result.rowcount or 0)
    return updated


def apply_album_images(session: Session, mapping: dict[str, str]) -> int:
    applied = 0
    for track_id, url in mapping.items():
        if not url:
            continue
        session.execute(
            update(Play)
            .where(Play.track_id == track_id)
            .where(
                (Play.album_image_url.is_(None)) | (Play.album_image_url == "")
            )
            .values(album_image_url=url)
        )
        applied += 1
    return applied


def track_ids_missing_images(
    session: Session,
    limit: int = 200,
    *,
    prioritize: str = "plays",
    track_ids: list[str] | None = None,
) -> list[str]:
    """Return track ids missing art. Default: most-played first."""
    missing = (Play.album_image_url.is_(None)) | (Play.album_image_url == "")
    if track_ids:
        rows = session.execute(
            select(Play.track_id)
            .where(Play.track_id.in_(track_ids))
            .where(missing)
            .group_by(Play.track_id)
            .limit(limit)
        ).all()
        return [row[0] for row in rows]

    if prioritize == "plays":
        rows = session.execute(
            select(Play.track_id, func.count().label("n"))
            .where(missing)
            .group_by(Play.track_id)
            .order_by(func.count().desc())
            .limit(limit)
        ).all()
        return [row[0] for row in rows]

    rows = session.execute(
        select(Play.track_id)
        .where(missing)
        .group_by(Play.track_id)
        .limit(limit)
    ).all()
    return [row[0] for row in rows]


def image_coverage(session: Session) -> dict:
    total_tracks = int(
        session.scalar(select(func.count(func.distinct(Play.track_id)))) or 0
    )
    with_image = int(
        session.scalar(
            select(func.count(func.distinct(Play.track_id))).where(
                Play.album_image_url.isnot(None),
                Play.album_image_url != "",
            )
        )
        or 0
    )
    return {
        "unique_tracks": total_tracks,
        "with_image": with_image,
        "missing": max(0, total_tracks - with_image),
    }


def _serialize_play(row: Play) -> dict:
    return {
        "played_at": row.played_at,
        "track_id": row.track_id,
        "track_name": row.track_name,
        "artist_names": row.artist_names,
        "album_name": row.album_name,
        "duration_ms": row.duration_ms,
        "context_uri": row.context_uri,
        "collected_at": row.collected_at,
        "album_image_url": row.album_image_url,
    }


def list_plays(session: Session, limit: int = 50) -> list[dict]:
    rows = session.scalars(
        select(Play).order_by(Play.played_at.desc()).limit(limit)
    ).all()
    return [_serialize_play(row) for row in rows]


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
    return _serialize_play(row)


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


def top_tracks(
    session: Session,
    limit: int = 10,
    *,
    time_range: str = "long_term",
    daily_cap: int = DEFAULT_DAILY_CAP,
) -> list[dict]:
    if time_range not in TIME_RANGE_DAYS:
        time_range = "long_term"

    scores = effective_track_scores(
        session, time_range=time_range, daily_cap=daily_cap
    )
    if not scores:
        return []

    ranked_ids = sorted(scores.keys(), key=lambda t: scores[t], reverse=True)[
        :limit
    ]

    # Latest metadata per track
    meta_rows = session.execute(
        select(
            Play.track_id,
            Play.track_name,
            Play.artist_names,
            Play.album_name,
            func.max(Play.album_image_url).label("album_image_url"),
            func.sum(Play.duration_ms).label("total_ms"),
            func.max(Play.played_at).label("last_played_at"),
            func.count().label("raw_play_count"),
        )
        .where(Play.track_id.in_(ranked_ids))
        .group_by(Play.track_id)
    ).all()
    by_id = {row.track_id: row for row in meta_rows}

    results: list[dict] = []
    for tid in ranked_ids:
        row = by_id.get(tid)
        if row is None:
            continue
        results.append(
            {
                "track_id": tid,
                "track_name": row.track_name,
                "artist_names": row.artist_names,
                "album_name": row.album_name,
                "play_count": int(scores[tid]),
                "raw_play_count": int(row.raw_play_count),
                "album_image_url": row.album_image_url,
                "total_ms": int(row.total_ms or 0),
                "last_played_at": row.last_played_at,
                "time_range": time_range,
                "daily_cap": daily_cap,
            }
        )
    return results


def top_artists(
    session: Session,
    limit: int = 10,
    *,
    time_range: str = "long_term",
    daily_cap: int = DEFAULT_DAILY_CAP,
) -> list[dict]:
    if time_range not in TIME_RANGE_DAYS:
        time_range = "long_term"

    scores = effective_artist_scores(
        session, time_range=time_range, daily_cap=daily_cap
    )
    if not scores:
        return []

    ranked = sorted(scores.keys(), key=lambda a: scores[a], reverse=True)[:limit]
    meta_rows = session.execute(
        select(
            Play.artist_names,
            func.count(func.distinct(Play.track_id)).label("unique_tracks"),
            func.sum(Play.duration_ms).label("total_ms"),
            func.max(Play.played_at).label("last_played_at"),
            func.max(Play.album_image_url).label("album_image_url"),
            func.count().label("raw_play_count"),
        )
        .where(Play.artist_names.in_(ranked))
        .group_by(Play.artist_names)
    ).all()
    by_name = {row.artist_names: row for row in meta_rows}

    results: list[dict] = []
    for name in ranked:
        row = by_name.get(name)
        if row is None:
            continue
        results.append(
            {
                "artist_names": name,
                "play_count": int(scores[name]),
                "raw_play_count": int(row.raw_play_count),
                "unique_tracks": int(row.unique_tracks),
                "total_ms": int(row.total_ms or 0),
                "last_played_at": row.last_played_at,
                "album_image_url": row.album_image_url,
                "time_range": time_range,
                "daily_cap": daily_cap,
            }
        )
    return results


def upsert_track_meta(session: Session, rows: list[dict]) -> int:
    if not rows:
        return 0
    written = 0
    for row in rows:
        existing = session.get(TrackMeta, row["track_id"])
        if existing is None:
            session.add(TrackMeta(**row))
        else:
            for key, value in row.items():
                if key == "track_id":
                    continue
                if value is not None:
                    setattr(existing, key, value)
        written += 1
    return written


def track_ids_missing_meta(
    session: Session,
    limit: int = 100,
    *,
    retry_after_minutes: int = 45,
) -> list[str]:
    """Most-played tracks lacking audio features.

    Prefer never-seen tracks, then feature-less rows whose last enrich
    attempt is older than ``retry_after_minutes`` (avoids hot-looping the
    same ids when ReccoBeats is down).
    """
    have_features = {
        r[0]
        for r in session.execute(
            select(TrackMeta.track_id).where(TrackMeta.energy.isnot(None))
        ).all()
    }
    meta_rows = session.execute(
        select(TrackMeta.track_id, TrackMeta.enriched_at)
    ).all()
    have_meta = {tid for tid, _ in meta_rows}
    cooldown_cutoff = (
        datetime.now(timezone.utc) - timedelta(minutes=retry_after_minutes)
    ).isoformat()
    recently_attempted = {
        tid
        for tid, enriched_at in meta_rows
        if tid not in have_features
        and enriched_at
        and enriched_at >= cooldown_cutoff
    }

    ranked = session.execute(
        select(Play.track_id, func.count().label("n"))
        .group_by(Play.track_id)
        .order_by(func.count().desc())
    ).all()

    never_seen = [tid for tid, _ in ranked if tid not in have_meta]
    if never_seen:
        return never_seen[:limit]

    missing_features = [
        tid
        for tid, _ in ranked
        if tid not in have_features and tid not in recently_attempted
    ]
    return missing_features[:limit]


def get_track_meta_map(
    session: Session, track_ids: list[str]
) -> dict[str, TrackMeta]:
    if not track_ids:
        return {}
    rows = session.scalars(
        select(TrackMeta).where(TrackMeta.track_id.in_(track_ids))
    ).all()
    return {row.track_id: row for row in rows}


def meta_coverage(session: Session) -> dict:
    total = int(
        session.scalar(select(func.count(func.distinct(Play.track_id)))) or 0
    )
    with_meta = int(session.scalar(select(func.count()).select_from(TrackMeta)) or 0)
    with_features = int(
        session.scalar(
            select(func.count()).select_from(TrackMeta).where(TrackMeta.energy.isnot(None))
        )
        or 0
    )
    with_genres = int(
        session.scalar(
            select(func.count())
            .select_from(TrackMeta)
            .where(TrackMeta.genres.isnot(None), TrackMeta.genres != "")
        )
        or 0
    )
    return {
        "unique_tracks": total,
        "with_meta": with_meta,
        "with_features": with_features,
        "with_genres": with_genres,
        "missing_features": max(0, total - with_features),
    }


def _parse_played_at(value: str) -> datetime | None:
    return parse_played_at(value)


def listening_by_hour(
    session: Session, *, tz_offset_minutes: int = 0
) -> list[dict]:
    """Bucket plays by local hour using client timezone offset from UTC."""
    offset = timedelta(minutes=tz_offset_minutes)
    counts: Counter[int] = Counter()
    rows = session.scalars(select(Play.played_at)).all()
    for raw in rows:
        dt = _parse_played_at(raw)
        if dt is None:
            continue
        local = dt + offset
        counts[local.hour] += 1
    return [{"hour": hour, "play_count": counts.get(hour, 0)} for hour in range(24)]


def listening_by_day(
    session: Session, *, days: int = 30, tz_offset_minutes: int = 0
) -> list[dict]:
    offset = timedelta(minutes=tz_offset_minutes)
    now_local = datetime.now(timezone.utc) + offset
    start_local = (now_local - timedelta(days=days - 1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    counts: Counter[str] = Counter()
    rows = session.scalars(select(Play.played_at)).all()
    for raw in rows:
        dt = _parse_played_at(raw)
        if dt is None:
            continue
        local = dt + offset
        day_key = local.date().isoformat()
        if local >= start_local:
            counts[day_key] += 1

    items: list[dict] = []
    for i in range(days):
        day = (start_local + timedelta(days=i)).date().isoformat()
        items.append({"day": day, "play_count": counts.get(day, 0)})
    return items
