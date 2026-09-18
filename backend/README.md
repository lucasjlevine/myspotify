# Spotify Play History Backend

FastAPI service that authorizes with Spotify (Authorization Code Flow), stores OAuth tokens, and accumulates listening history by polling recently played tracks into SQLite via SQLAlchemy.

## Setup

1. Copy env vars into `.env` (gitignored):

```env
SPOTIFY_STATE=<random-csrf-string>
SPOTIFY_CLIENT_ID=<from Spotify Developer Dashboard>
SPOTIFY_CLIENT_SECRET=<from Spotify Developer Dashboard>
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8000/authorize/callback
SPOTIFY_REFRESH_TOKEN=
SPOTIFY_API_SCOPE=user-read-email user-read-private user-top-read user-read-recently-played user-read-playback-state user-read-currently-playing user-library-read playlist-read-private playlist-read-collaborative user-follow-read
```

2. In the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard), add the exact redirect URI `http://127.0.0.1:8000/authorize/callback` (use `127.0.0.1`, not `localhost`).

3. Install and run from this directory:

```bash
uv sync
uv run main.py
```

API docs: http://127.0.0.1:8000/docs

## First-time auth

1. Open http://127.0.0.1:8000/authorize
2. Approve the app in Spotify
3. Tokens are saved to SQLite (`data/plays.db`) and `SPOTIFY_REFRESH_TOKEN` is written into `.env`
4. Recently played tracks are synced after authorize and every 15 minutes while the server runs

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/authorize` | Start Spotify OAuth |
| `GET` | `/authorize/callback` | OAuth callback; stores tokens |
| `POST` | `/sync/plays` | Manually fetch & upsert recent plays |
| `GET` | `/plays?limit=50` | List stored plays |

## Layout

```
backend/
  main.py                 # App entrypoint
  app/
    config.py             # Settings from .env
    database.py           # SQLAlchemy engine / sessions
    models.py             # Token, Play ORM models
    repositories.py       # DB access helpers
    lifespan.py           # Startup + background poller
    routers/              # HTTP routes
    spotify/              # OAuth + recently-played sync
  data/plays.db           # Local SQLite (gitignored)
```

## Notes

- Spotify’s Web API only returns about the last 50 plays per request. This service accumulates history over time by polling.
- Do not commit `.env` or `data/*.db`.
