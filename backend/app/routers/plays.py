from fastapi import APIRouter, Query

from app.database import session_scope
from app import repositories
from app.spotify import sync

router = APIRouter(tags=["plays"])


@router.post("/sync/plays")
def sync_plays():
    """Fetch recently played tracks from Spotify and upsert into SQLite."""
    return sync.sync_recently_played()


@router.get("/plays")
def get_plays(limit: int = Query(default=50, ge=1, le=500)):
    """List accumulated plays stored locally."""
    with session_scope() as session:
        plays = repositories.list_plays(session, limit=limit)
    return {"plays": plays}
