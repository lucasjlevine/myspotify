from fastapi import APIRouter, Query

from app.database import session_scope
from app import repositories

router = APIRouter(tags=["stats"])


@router.get("/stats/summary")
def summary():
    """Aggregate listening totals for the overview dashboard."""
    with session_scope() as session:
        return repositories.stats_summary(session)


@router.get("/stats/top-tracks")
def get_top_tracks(limit: int = Query(default=10, ge=1, le=50)):
    with session_scope() as session:
        return {"tracks": repositories.top_tracks(session, limit=limit)}


@router.get("/stats/top-artists")
def get_top_artists(limit: int = Query(default=10, ge=1, le=50)):
    with session_scope() as session:
        return {"artists": repositories.top_artists(session, limit=limit)}


@router.get("/stats/listening-by-hour")
def get_listening_by_hour():
    with session_scope() as session:
        return {"hours": repositories.listening_by_hour(session)}


@router.get("/stats/listening-by-day")
def get_listening_by_day(days: int = Query(default=30, ge=1, le=365)):
    with session_scope() as session:
        return {"days": repositories.listening_by_day(session, days=days)}
