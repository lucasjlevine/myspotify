# Spotify Play History Backend

FastAPI service: Spotify OAuth, play history accumulation, Extended Streaming History import, and next-song predictors.

## Setup

1. Create `.env` (gitignored):

```env
SPOTIFY_STATE=<random-csrf-string>
SPOTIFY_CLIENT_ID=<dashboard>
SPOTIFY_CLIENT_SECRET=<dashboard>
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8000/api/authorize/callback
SPOTIFY_REFRESH_TOKEN=
SPOTIFY_API_SCOPE=user-read-email user-read-private user-top-read user-read-recently-played user-read-playback-state user-read-currently-playing user-library-read playlist-read-private playlist-read-collaborative user-follow-read
FRONTEND_URL=http://localhost:3000
# Optional extras (Silk): CORS_ORIGINS=https://YOUR_NETID.w3.uvm.edu
```

2. Spotify Dashboard redirect URI must match exactly (`127.0.0.1`, not `localhost`). All HTTP routes are under `/api/…`.

3. Run:

```bash
uv sync
uv run main.py
```

API docs: http://127.0.0.1:8000/docs

## Auth

1. Open http://127.0.0.1:8000/api/authorize (or Connect in the UI)
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

## Album artwork

Most history imports have no images. Backfill from the Spotify Web API (most-played first, 50 ids/request):

```bash
uv run python -m app.enrich_images --batches 40
# or from the UI: Top tracks → Fetch art (runs ~30 batches)
curl -X POST "http://127.0.0.1:8000/api/tracks/enrich-images?batches=20"
```

## Next-song predictors

| id | Idea |
|----|------|
| `markov` | First-order track transitions (default) |
| `popularity` | Globally most-played tracks |
| `artist` | Other tracks by the same artist |
| `cooccurrence` | Tracks that co-appear in a ±5 play window |
| `item_knn` | sklearn cosine kNN on co-occurrence vectors |
| `prompted` | Local TF-IDF ranker over a listening-window prompt |
| `embedding` | Local ONNX song-space (fastembed); neighbors + free-text mood prompts |

```bash
uv run python -m app.ml.train              # all models
uv run python -m app.ml.train --model markov
uv run python -m app.ml.train --model prompted
uv run python -m app.ml.train --model embedding
curl "http://127.0.0.1:8000/api/predict/models"
curl "http://127.0.0.1:8000/api/predict/next?k=8&model=embedding&window=hours_4&tz_offset_minutes=-240"
curl "http://127.0.0.1:8000/api/predict/prompt?q=Rainy%20fall%20day&k=10"
```

Artifacts under `data/models/` (gitignored). Windows: `latest`, `hours_4`, `today`, `plays_10`, `plays_20` (or `hours:N` / `plays:N`). Classical models blend seeds with recency weights; `prompted` / `embedding` use the full window. Phrase search uses the same embedding space via `/api/predict/prompt`.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Liveness |
| `GET` | `/api/authorize` | Start OAuth |
| `GET` | `/api/authorize/callback` | Store tokens, redirect to frontend |
| `GET` | `/api/auth/status` | Whether authorized (no tokens) |
| `POST` | `/api/sync/plays` | Fetch & upsert recent plays (+ images when present) |
| `GET` | `/api/plays?limit=50` | List stored plays |
| `GET` | `/api/predict/models` | List predictors + windows + train status |
| `GET` | `/api/predict/windows` | Window presets |
| `GET` | `/api/predict/next?k=5&model=markov&window=hours_4` | Predict next track(s) |
| `GET` | `/api/predict/prompt?q=…&k=10` | Mood/phrase → nearest tracks (`embedding`) |
| `GET` | `/api/stats/summary` | Listening totals |
| `GET` | `/api/stats/top-tracks` | Most-played tracks |
| `GET` | `/api/stats/top-artists` | Most-played artists |
| `GET` | `/api/stats/listening-by-hour?tz_offset_minutes=` | Plays by local hour |
| `GET` | `/api/stats/listening-by-day?days=30&tz_offset_minutes=` | Daily play counts |
| `POST` | `/api/tracks/enrich-images` | Backfill album art via Spotify |

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
