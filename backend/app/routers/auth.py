import logging

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse

from app.config import settings
from app.spotify import auth, sync

logger = logging.getLogger(__name__)
router = APIRouter(tags=["auth"])


@router.get("/authorize")
def authorize():
    """Redirect the user to Spotify to grant access (Authorization Code Flow)."""
    return RedirectResponse(url=auth.build_authorize_url())


@router.get("/authorize/callback")
def authorize_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
):
    """Handle Spotify's redirect: validate state and exchange code for tokens."""
    if state != settings.spotify_state:
        raise HTTPException(status_code=400, detail="state_mismatch")
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    if code is None:
        raise HTTPException(status_code=400, detail="missing_code")

    payload = auth.exchange_authorization_code(code)

    sync_result = None
    try:
        sync_result = sync.sync_recently_played()
    except HTTPException as exc:
        logger.warning("post-auth sync failed: %s", exc.detail)

    return {
        "status": "authorized",
        "expires_in": payload.get("expires_in"),
        "scope": payload.get("scope"),
        "sync": sync_result,
    }
