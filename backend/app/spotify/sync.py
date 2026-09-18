import requests
from fastapi import HTTPException

from app.config import settings
from app.database import session_scope
from app import repositories
from app.spotify.auth import get_access_token


def normalize_play(item: dict) -> dict | None:
    track = item.get("track") or {}
    track_id = track.get("id")
    played_at = item.get("played_at")
    if not track_id or not played_at:
        return None

    artists = track.get("artists") or []
    album = track.get("album") or {}
    context = item.get("context") or {}

    return {
        "played_at": played_at,
        "track_id": track_id,
        "track_name": track.get("name") or "",
        "artist_names": ", ".join(a.get("name", "") for a in artists),
        "album_name": album.get("name") or "",
        "duration_ms": int(track.get("duration_ms") or 0),
        "context_uri": context.get("uri"),
    }


def fetch_recently_played(limit: int = 50) -> list[dict]:
    access_token = get_access_token()
    response = requests.get(
        settings.spotify_recently_played_url,
        params={"limit": limit},
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.json() if response.content else response.text,
        )
    return response.json().get("items") or []


def sync_recently_played() -> dict:
    items = fetch_recently_played(limit=50)
    plays = [play for item in items if (play := normalize_play(item)) is not None]
    with session_scope() as session:
        inserted, skipped = repositories.upsert_plays(session, plays)
    return {"fetched": len(plays), "inserted": inserted, "skipped": skipped}
