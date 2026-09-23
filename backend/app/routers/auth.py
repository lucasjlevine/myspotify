import logging
from urllib.parse import urlencode

from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse

from app.config import settings
from app.database import session_scope
from app import repositories
from app.spotify import auth, sync

logger = logging.getLogger(__name__)
router = APIRouter(tags=["auth"])


def _frontend_callback(status: str, **extra: str) -> RedirectResponse:
    params = {"status": status, **extra}
    url = f"{settings.frontend_url.rstrip('/')}/auth/callback?{urlencode(params)}"
    return RedirectResponse(url=url)


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
    """Handle Spotify's redirect: validate state, exchange code, send user to frontend."""
    if state != settings.spotify_state:
        return _frontend_callback("error", reason="state_mismatch")
    if error is not None:
        return _frontend_callback("error", reason=error)
    if code is None:
        return _frontend_callback("error", reason="missing_code")

    try:
        auth.exchange_authorization_code(code)
    except Exception:
        logger.exception("token exchange failed")
        return _frontend_callback("error", reason="token_exchange_failed")

    try:
        sync.sync_recently_played()
    except Exception as sync_exc:
        logger.warning("post-auth sync failed: %s", sync_exc)

    return _frontend_callback("authorized")


@router.get("/auth/status")
def auth_status():
    """Return whether Spotify tokens are present (never returns token values)."""
    with session_scope() as session:
        token = repositories.get_tokens(session)
        if token is None and not settings.spotify_refresh_token:
            return {"authorized": False}
        return {
            "authorized": True,
            "expires_at": token.expires_at if token is not None else None,
        }
