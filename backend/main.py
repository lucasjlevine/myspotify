import asyncio
import base64
import logging
import os
import re
import time
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlencode

import requests
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import RedirectResponse

import db

load_dotenv()

logger = logging.getLogger(__name__)

SPOTIFY_AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_RECENTLY_PLAYED_URL = (
    "https://api.spotify.com/v1/me/player/recently-played"
)

SPOTIFY_STATE = os.environ["SPOTIFY_STATE"]
SPOTIFY_CLIENT_ID = os.environ["SPOTIFY_CLIENT_ID"]
SPOTIFY_CLIENT_SECRET = os.environ["SPOTIFY_CLIENT_SECRET"]
SPOTIFY_REDIRECT_URI = os.environ["SPOTIFY_REDIRECT_URI"]
SPOTIFY_API_SCOPE = os.environ["SPOTIFY_API_SCOPE"]

ENV_PATH = Path(__file__).resolve().parent / ".env"
POLL_INTERVAL_SECONDS = 15 * 60
TOKEN_EXPIRY_SKEW_SECONDS = 60


def _basic_auth_header(client_id: str, client_secret: str) -> str:
    credentials = f"{client_id}:{client_secret}".encode()
    return "Basic " + base64.b64encode(credentials).decode()


def _update_env_refresh_token(refresh_token: str) -> None:
    """Persist refresh token to .env for restarts."""
    if not ENV_PATH.exists():
        ENV_PATH.write_text(f"SPOTIFY_REFRESH_TOKEN={refresh_token}\n", encoding="utf-8")
        return

    content = ENV_PATH.read_text(encoding="utf-8")
    pattern = re.compile(r"^SPOTIFY_REFRESH_TOKEN=.*$", re.MULTILINE)
    replacement = f"SPOTIFY_REFRESH_TOKEN={refresh_token}"
    if pattern.search(content):
        content = pattern.sub(replacement, content)
    else:
        if content and not content.endswith("\n"):
            content += "\n"
        content += replacement + "\n"
    ENV_PATH.write_text(content, encoding="utf-8")
    os.environ["SPOTIFY_REFRESH_TOKEN"] = refresh_token


def _store_token_response(token_payload: dict, *, fallback_refresh: str | None = None) -> None:
    refresh_token = token_payload.get("refresh_token") or fallback_refresh
    if not refresh_token:
        raise HTTPException(status_code=500, detail="missing_refresh_token")

    expires_at = time.time() + float(token_payload["expires_in"])
    db.save_tokens(
        access_token=token_payload["access_token"],
        refresh_token=refresh_token,
        expires_at=expires_at,
    )
    _update_env_refresh_token(refresh_token)


def _request_token(data: dict) -> dict:
    response = requests.post(
        SPOTIFY_TOKEN_URL,
        data=data,
        headers={
            "Authorization": _basic_auth_header(
                SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET
            ),
            "Content-Type": "application/x-www-form-urlencoded",
        },
        timeout=30,
    )
    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.json() if response.content else response.text,
        )
    return response.json()


def get_access_token() -> str:
    """Return a valid access token, refreshing when needed."""
    row = db.get_tokens()
    refresh_token = None
    if row is not None:
        if row["expires_at"] > time.time() + TOKEN_EXPIRY_SKEW_SECONDS:
            return row["access_token"]
        refresh_token = row["refresh_token"]
    else:
        refresh_token = os.getenv("SPOTIFY_REFRESH_TOKEN") or None

    if not refresh_token:
        raise HTTPException(
            status_code=401,
            detail="not_authorized: visit /authorize first",
        )

    payload = _request_token(
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
    )
    _store_token_response(payload, fallback_refresh=refresh_token)
    return payload["access_token"]


def _normalize_play(item: dict) -> dict | None:
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


def sync_recently_played() -> dict:
    access_token = get_access_token()
    response = requests.get(
        SPOTIFY_RECENTLY_PLAYED_URL,
        params={"limit": 50},
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.json() if response.content else response.text,
        )

    items = response.json().get("items") or []
    plays = [play for item in items if (play := _normalize_play(item)) is not None]
    inserted, skipped = db.upsert_plays(plays)
    return {"fetched": len(plays), "inserted": inserted, "skipped": skipped}


async def _poll_recently_played() -> None:
    while True:
        try:
            result = await asyncio.to_thread(sync_recently_played)
            logger.info("play sync: %s", result)
        except HTTPException as exc:
            logger.warning("play sync skipped: %s", exc.detail)
        except Exception:
            logger.exception("play sync failed")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.init_db()
    # Seed SQLite from .env refresh token if we have no stored tokens yet.
    if db.get_tokens() is None:
        env_refresh = os.getenv("SPOTIFY_REFRESH_TOKEN") or ""
        if env_refresh.strip():
            try:
                get_access_token()
            except HTTPException as exc:
                logger.warning("startup token refresh failed: %s", exc.detail)

    poll_task = asyncio.create_task(_poll_recently_played())
    try:
        yield
    finally:
        poll_task.cancel()
        try:
            await poll_task
        except asyncio.CancelledError:
            pass


app = FastAPI(lifespan=lifespan)


@app.get("/authorize")
def authorize():
    """Redirect the user to Spotify to grant access (Authorization Code Flow)."""
    params = {
        "client_id": SPOTIFY_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": SPOTIFY_REDIRECT_URI,
        "state": SPOTIFY_STATE,
        "scope": SPOTIFY_API_SCOPE,
    }
    return RedirectResponse(url=f"{SPOTIFY_AUTHORIZE_URL}?{urlencode(params)}")


@app.get("/authorize/callback")
def authorize_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
):
    """Handle Spotify's redirect: validate state and exchange code for tokens."""
    if state != SPOTIFY_STATE:
        raise HTTPException(status_code=400, detail="state_mismatch")

    if error is not None:
        raise HTTPException(status_code=400, detail=error)

    if code is None:
        raise HTTPException(status_code=400, detail="missing_code")

    payload = _request_token(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": SPOTIFY_REDIRECT_URI,
        }
    )
    _store_token_response(payload)

    sync_result = None
    try:
        sync_result = sync_recently_played()
    except HTTPException as exc:
        logger.warning("post-auth sync failed: %s", exc.detail)

    return {
        "status": "authorized",
        "expires_in": payload.get("expires_in"),
        "scope": payload.get("scope"),
        "sync": sync_result,
    }


@app.post("/sync/plays")
def sync_plays():
    """Fetch recently played tracks from Spotify and upsert into SQLite."""
    return sync_recently_played()


@app.get("/plays")
def get_plays(limit: int = Query(default=50, ge=1, le=500)):
    """List accumulated plays stored locally."""
    return {"plays": db.list_plays(limit=limit)}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
