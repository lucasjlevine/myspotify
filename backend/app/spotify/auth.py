import base64
import os
import re
import time
from urllib.parse import urlencode

import requests
from fastapi import HTTPException

from app.config import ENV_PATH, settings
from app.database import session_scope
from app import repositories


def _basic_auth_header() -> str:
    credentials = f"{settings.spotify_client_id}:{settings.spotify_client_secret}".encode()
    return "Basic " + base64.b64encode(credentials).decode()


def update_env_refresh_token(refresh_token: str) -> None:
    """Persist refresh token to .env for restarts."""
    if not ENV_PATH.exists():
        ENV_PATH.write_text(f"SPOTIFY_REFRESH_TOKEN={refresh_token}\n", encoding="utf-8")
        os.environ["SPOTIFY_REFRESH_TOKEN"] = refresh_token
        settings.spotify_refresh_token = refresh_token
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
    settings.spotify_refresh_token = refresh_token


def build_authorize_url() -> str:
    params = {
        "client_id": settings.spotify_client_id,
        "response_type": "code",
        "redirect_uri": settings.spotify_redirect_uri,
        "state": settings.spotify_state,
        "scope": settings.spotify_api_scope,
    }
    return f"{settings.spotify_authorize_url}?{urlencode(params)}"


def request_token(data: dict) -> dict:
    response = requests.post(
        settings.spotify_token_url,
        data=data,
        headers={
            "Authorization": _basic_auth_header(),
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


def store_token_response(
    token_payload: dict,
    *,
    fallback_refresh: str | None = None,
) -> None:
    refresh_token = token_payload.get("refresh_token") or fallback_refresh
    if not refresh_token:
        raise HTTPException(status_code=500, detail="missing_refresh_token")

    expires_at = time.time() + float(token_payload["expires_in"])
    with session_scope() as session:
        repositories.save_tokens(
            session,
            access_token=token_payload["access_token"],
            refresh_token=refresh_token,
            expires_at=expires_at,
        )
    update_env_refresh_token(refresh_token)


def exchange_authorization_code(code: str) -> dict:
    payload = request_token(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.spotify_redirect_uri,
        }
    )
    store_token_response(payload)
    return payload


def get_access_token() -> str:
    """Return a valid access token, refreshing when needed."""
    with session_scope() as session:
        token = repositories.get_tokens(session)
        if token is not None:
            if token.expires_at > time.time() + settings.token_expiry_skew_seconds:
                return token.access_token
            refresh_token = token.refresh_token
        else:
            refresh_token = settings.spotify_refresh_token or None

    if not refresh_token:
        raise HTTPException(
            status_code=401,
            detail="not_authorized: visit /authorize first",
        )

    payload = request_token(
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
    )
    store_token_response(payload, fallback_refresh=refresh_token)
    return payload["access_token"]
