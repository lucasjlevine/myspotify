import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from app.config import settings
from app.database import init_db, session_scope
from app import repositories
from app.spotify import auth, sync

logger = logging.getLogger(__name__)


async def _poll_recently_played() -> None:
    while True:
        try:
            result = await asyncio.to_thread(sync.sync_recently_played)
            logger.info("play sync: %s", result)
        except HTTPException as exc:
            logger.warning("play sync skipped: %s", exc.detail)
        except Exception:
            logger.exception("play sync failed")
        await asyncio.sleep(settings.poll_interval_seconds)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()

    with session_scope() as session:
        has_tokens = repositories.get_tokens(session) is not None

    if not has_tokens and settings.spotify_refresh_token.strip():
        try:
            auth.get_access_token()
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
