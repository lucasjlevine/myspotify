# AGENTS.md — Backend

Guidance for coding agents working in `backend/`.

## Purpose

Personal FastAPI backend that:

1. Completes Spotify Authorization Code Flow
2. Persists access/refresh tokens
3. Polls `/me/player/recently-played` and upserts plays into SQLite for later ML (next-song prediction)

Keep scope focused on collection and auth unless the user asks to expand.

## Stack

- Python 3.14+, `uv` for deps (`pyproject.toml` / `uv.lock`)
- FastAPI + Uvicorn
- SQLAlchemy 2.0 ORM (SQLite at `data/plays.db`)
- `pydantic-settings` + `.env` for config
- `requests` for Spotify HTTP calls

## Layout conventions

- `main.py` stays thin: create app and run uvicorn only
- HTTP routes live in `app/routers/`
- Spotify API / OAuth logic lives in `app/spotify/`
- ORM models in `app/models.py`; queries in `app/repositories.py`
- Do not dump helpers back into `main.py`

## Environment

Required `.env` keys (never commit secrets):

- `SPOTIFY_STATE`
- `SPOTIFY_CLIENT_ID`
- `SPOTIFY_CLIENT_SECRET`
- `SPOTIFY_REDIRECT_URI` — must be loopback `http://127.0.0.1:...`, not `localhost`
- `SPOTIFY_API_SCOPE`
- `SPOTIFY_REFRESH_TOKEN` — filled after successful OAuth

Redirect URI in the Spotify Dashboard must match `.env` exactly.

## Data constraints

- Spotify only exposes ~50 recent plays via the Web API
- History grows by polling (default every 15 minutes in `app/lifespan.py`)
- Upsert key is `(played_at, track_id)` — duplicates are ignored
- Do not add privacy-export import unless asked

## Working rules

- Prefer small, focused modules over large files
- Use SQLAlchemy sessions via `session_scope()`; avoid raw `sqlite3`
- Never return access/refresh tokens in API responses
- After dependency changes, update with `uv add` / `uv sync`, not ad-hoc pip-only edits
- Run from `backend/`: `uv run main.py`

## Out of scope (unless requested)

- Frontend work
- ML training / next-song model
- Pushing to remote git
- Committing `.env` or database files
