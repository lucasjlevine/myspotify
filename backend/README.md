# Spotify Play History Backend

FastAPI service: Spotify OAuth, play history accumulation, Extended Streaming History import, and next-song predictors.

## Setup

1. Create `.env` (gitignored):

```env
SPOTIFY_STATE=<random-csrf-string>
SPOTIFY_CLIENT_ID=<dashboard>
SPOTIFY_CLIENT_SECRET=<dashboard>
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8000/authorize/callback
SPOTIFY_REFRESH_TOKEN=
SPOTIFY_API_SCOPE=user-read-email user-read-private user-top-read user-read-recently-played user-read-playback-state user-read-currently-playing user-library-read playlist-read-private playlist-read-collaborative user-follow-read
FRONTEND_URL=http://localhost:3000
```

2. Spotify Dashboard redirect URI must match exactly (`127.0.0.1`, not `localhost`).

3. Run:

```bash
uv sync
uv run main.py
```

API docs: http://127.0.0.1:8000/docs

## Auth

1. Open http://127.0.0.1:8000/authorize
2. Approve in Spotify
3. Tokens land in SQLite + `SPOTIFY_REFRESH_TOKEN` in `.env`
4. Recently played syncs on authorize and every 15 minutes

## Import Extended Streaming History

Put the privacy export in `data/Spotify Extended Streaming History/`:

```bash
uv run python -m app.import_history
# optional: uv run python -m app.import_history --min-ms 30000
```

Imports `spotify:track:` rows only. Upsert key: `(played_at, track_id)`.

## Next-song predictors

| id | Idea |
|----|------|
| `markov` | First-order track transitions (default) |
| `popularity` | Globally most-played tracks |
| `artist` | Other tracks by the same artist |
| `cooccurrence` | Tracks that co-appear in a ±5 play window |
| `item_knn` | sklearn cosine kNN on co-occurrence vectors |
| `prompted` | Local TF-IDF ranker over a listening-window prompt (expandable to local LLM) |

```bash
uv run python -m app.ml.train              # all models
uv run python -m app.ml.train --model markov
uv run python -m app.ml.train --model prompted
curl "http://127.0.0.1:8000/predict/models"
curl "http://127.0.0.1:8000/predict/next?k=8&model=prompted&window=hours_4&tz_offset_minutes=-240"
curl "http://127.0.0.1:8000/predict/next?k=5&model=markov&window=today"
```

Artifacts under `data/models/` (gitignored). Windows: `latest`, `hours_4`, `today`, `plays_10`, `plays_20` (or `hours:N` / `plays:N`). Classical models blend seeds with recency weights; `prompted` uses the full window as one prompt.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness |
| `GET` | `/authorize` | Start OAuth |
| `GET` | `/authorize/callback` | Store tokens, redirect to frontend |
| `GET` | `/auth/status` | Whether authorized (no tokens) |
| `POST` | `/sync/plays` | Fetch & upsert recent plays (+ images when present) |
| `GET` | `/plays?limit=50` | List stored plays |
| `GET` | `/predict/models` | List predictors + windows + train status |
| `GET` | `/predict/windows` | Window presets |
| `GET` | `/predict/next?k=5&model=markov&window=hours_4` | Predict next track(s) |
| `GET` | `/stats/summary` | Listening totals |
| `GET` | `/stats/top-tracks` | Most-played tracks |
| `GET` | `/stats/top-artists` | Most-played artists |
| `GET` | `/stats/listening-by-hour?tz_offset_minutes=` | Plays by local hour |
| `GET` | `/stats/listening-by-day?days=30&tz_offset_minutes=` | Daily play counts |
| `POST` | `/tracks/enrich-images` | Backfill album art via Spotify |

## Layout

```
backend/
  main.py
  app/
    routers/ spotify/ ml/
    import_history.py
  data/
    plays.db / models/* / Spotify Extended Streaming History/   # gitignored
```

## Notes

- Web API recently-played ≈ last 50; history grows via poll + optional export import.
- Do not commit `.env`, DBs, model artifacts, or privacy-export files.
