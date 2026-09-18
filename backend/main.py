import base64
import os
from urllib.parse import urlencode

import requests
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import RedirectResponse

SPOTIFY_AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"

SPOTIFY_STATE = os.environ["SPOTIFY_STATE"]
SPOTIFY_CLIENT_ID = os.environ["SPOTIFY_CLIENT_ID"]
SPOTIFY_CLIENT_SECRET = os.environ["SPOTIFY_CLIENT_SECRET"]
SPOTIFY_REDIRECT_URI = os.environ["SPOTIFY_REDIRECT_URI"]
SPOTIFY_API_SCOPE = os.environ["SPOTIFY_API_SCOPE"]

app = FastAPI()


def _basic_auth_header(client_id: str, client_secret: str) -> str:
    credentials = f"{client_id}:{client_secret}".encode()
    return "Basic " + base64.b64encode(credentials).decode()


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

    response = requests.post(
        SPOTIFY_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": SPOTIFY_REDIRECT_URI,
        },
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


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
