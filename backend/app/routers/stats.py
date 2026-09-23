from fastapi import APIRouter, Query

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
def get_top_tracks(limit: int = Query(default=10, ge=1, le=100)):
    with session_scope() as session:
        return {"tracks": repositories.top_tracks(session, limit=limit)}


@router.get("/stats/top-artists")
def get_top_artists(limit: int = Query(default=10, ge=1, le=100)):
    with session_scope() as session:
        return {"artists": repositories.top_artists(session, limit=limit)}


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


@router.post("/tracks/enrich-images")
def enrich_album_images(limit: int = Query(default=100, ge=1, le=200)):
    """Fetch album art from Spotify for tracks missing images."""
    with session_scope() as session:
        missing = repositories.track_ids_missing_images(session, limit=limit)
    if not missing:
        return {"fetched": 0, "updated": 0, "remaining": 0}

    mapping = spotify_tracks.fetch_track_images(missing)
    with session_scope() as session:
        updated = repositories.apply_album_images(session, mapping)
        still_missing = repositories.track_ids_missing_images(session, limit=200)
    return {
        "fetched": len(mapping),
        "updated": updated,
        "remaining_sample": len(still_missing),
    }
