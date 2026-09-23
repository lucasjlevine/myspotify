# AGENTS.md — Backend

Applies when editing `backend/`. Root [AGENTS.md](../AGENTS.md) + `.cursor/rules/` also apply.

## Purpose

FastAPI: Spotify OAuth, play upsert/polling, Extended History import, multi-model next-song prediction, listening stats for the dashboard.

## Commands

```bash
cd backend
uv sync
uv run main.py
uv run python -m app.import_history
uv run python -m app.ml.train            # all
uv run python -m app.ml.train --model markov
uv run python -m app.enrich_features --batches 20   # genres + audio features
uv run python -m app.enrich_images --batches 20
```

From repo root: `npm run dev` (backend + frontend).

## Layout

- `main.py` — thin entry
- `app/routers/` — HTTP (`auth`, `plays`, `predict`, `stats`, `health`)
- `app/spotify/` — OAuth, sync, export parse
- `app/ml/` — `NextSongPredictor` + registry (`markov`, `popularity`, `artist`, `cooccurrence`, `item_knn`, `prompted`, `embedding`)
- `app/models.py` + `app/repositories.py` — SQLAlchemy
- `app/listening.py` — daily-capped affinity + short/medium/long windows
- `app/spotify/catalog.py` — genres (Spotify) + audio features (ReccoBeats)

## Rules

- Sessions via `session_scope()`; no raw `sqlite3`
- Never return tokens in API responses
- Deps: `uv add` / `uv sync`
- Upsert key `(played_at, track_id)`
- New models: implement protocol, register in `app/ml/registry.py`
- Artifacts: `data/models/{id}.json` or `{id}.joblib` (+ `.meta.json` for binary)
- Redirect URI: `127.0.0.1`, not `localhost`
- OAuth success redirects to `FRONTEND_URL/auth/callback`
- Predict windows: `latest` | `hours_4` | `today` | `plays_N` (blend classical; prompted uses full window)
- `prompted` is local TF-IDF today — keep the prompt builder so an Ollama backend can plug in later
- `embedding` is local fastembed+audio: genres/mood phrases + 9-d features; `GET /predict/prompt?q=…`
- Tops: `time_range=short_term|medium_term|long_term` with 3-plays/day cap (anti sleep-loop)
- Album art: `album_image_url` on plays; `POST /tracks/enrich-images` backfills via Spotify
- Features: `TrackMeta` + `POST /tracks/enrich-features` (Spotify genres, ReccoBeats audio)

## Do not commit

`.env`, `data/*.db`, `data/models/*` artifacts, privacy-export JSON

## Out of scope unless asked

Frontend UI polish, force-push / history rewrite
(Local prompted LLM / Ollama backends are OK when expanding `prompted`)
