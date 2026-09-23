from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.database import session_scope
from app import repositories
from app.spotify import tracks as spotify_tracks

router = APIRouter(tags=["stats"])


@router.get("/stats/summary")
def summary():
    """Aggregate listening totals for the overview dashboard."""
    with session_scope() as session:
        return repositories.stats_summary(session)


@router.get("/stats/top-tracks")
def get_top_tracks(
    limit: int = Query(default=10, ge=1, le=100),
    time_range: str = Query(
        default="long_term",
        pattern="^(short_term|medium_term|long_term)$",
    ),
):
    """Top tracks with Spotify-like windows and daily play caps (anti sleep-loop)."""
    with session_scope() as session:
        return {
            "time_range": time_range,
            "tracks": repositories.top_tracks(
                session, limit=limit, time_range=time_range
            ),
        }


@router.get("/stats/top-artists")
def get_top_artists(
    limit: int = Query(default=10, ge=1, le=100),
    time_range: str = Query(
        default="long_term",
        pattern="^(short_term|medium_term|long_term)$",
    ),
):
    with session_scope() as session:
        return {
            "time_range": time_range,
            "artists": repositories.top_artists(
                session, limit=limit, time_range=time_range
            ),
        }


@router.get("/stats/listening-by-hour")
def get_listening_by_hour(
    tz_offset_minutes: int = Query(default=0, ge=-840, le=840),
):
    with session_scope() as session:
        return {
            "hours": repositories.listening_by_hour(
                session, tz_offset_minutes=tz_offset_minutes
            ),
            "tz_offset_minutes": tz_offset_minutes,
        }


@router.get("/stats/listening-by-day")
def get_listening_by_day(
    days: int = Query(default=30, ge=1, le=365),
    tz_offset_minutes: int = Query(default=0, ge=-840, le=840),
):
    with session_scope() as session:
        return {
            "days": repositories.listening_by_day(
                session, days=days, tz_offset_minutes=tz_offset_minutes
            ),
            "tz_offset_minutes": tz_offset_minutes,
        }


@router.get("/tracks/image-coverage")
def get_image_coverage():
    with session_scope() as session:
        return repositories.image_coverage(session)


@router.get("/tracks/meta-coverage")
def get_meta_coverage():
    with session_scope() as session:
        return repositories.meta_coverage(session)


@router.post("/tracks/enrich-features")
def enrich_track_features(
    batches: int = Query(default=5, ge=1, le=50),
    limit: int = Query(default=50, ge=1, le=50),
    genres_only: bool = Query(default=False),
):
    """Enrich genres (Spotify artists) + optional audio features (ReccoBeats)."""
    from app.enrich_features import enrich_batch

    mode = "genres" if genres_only else "features"
    total = 0
    for _ in range(batches):
        with session_scope() as session:
            missing = repositories.track_ids_missing_meta(
                session, limit=limit, mode=mode
            )
        if not missing:
            break
        total += enrich_batch(missing, genres_only=genres_only)

    with session_scope() as session:
        coverage = repositories.meta_coverage(session)
    return {"enriched": total, "genres_only": genres_only, **coverage}


class EnrichImagesBody(BaseModel):
    track_ids: list[str] | None = None
    batches: int = Field(default=1, ge=1, le=100)
    limit: int = Field(default=50, ge=1, le=50)


@router.post("/tracks/enrich-images")
def enrich_album_images(
    body: EnrichImagesBody | None = None,
    limit: int = Query(default=50, ge=1, le=50),
    batches: int = Query(default=1, ge=1, le=100),
):
    """Backfill album art from Spotify, most-played tracks first.

    Spotify allows 50 track ids per request. Pass `batches` to run multiple
    rounds in one call (e.g. batches=20 ≈ 1000 tracks). Optional `track_ids`
    in JSON body to enrich a visible list first.
    """
    payload = body or EnrichImagesBody(limit=limit, batches=batches)
    batch_limit = min(payload.limit, limit, 50)
    batch_count = max(payload.batches, batches)
    requested_ids = payload.track_ids

    total_fetched = 0
    total_updated = 0

    for _ in range(batch_count):
        with session_scope() as session:
            missing = repositories.track_ids_missing_images(
                session,
                limit=batch_limit,
                prioritize="plays",
                track_ids=requested_ids,
            )
        if not missing:
            break

        mapping = spotify_tracks.fetch_track_images(missing)
        total_fetched += len(mapping)
        with session_scope() as session:
            total_updated += repositories.apply_album_images(session, mapping)

        # After targeted ids, continue with global priority queue
        requested_ids = None

    with session_scope() as session:
        coverage = repositories.image_coverage(session)

    return {
        "fetched": total_fetched,
        "updated": total_updated,
        "batches_run": batch_count,
        **coverage,
    }
