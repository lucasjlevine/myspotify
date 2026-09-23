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
```

From repo root: `npm run dev` (backend + frontend).

## Layout

- `main.py` — thin entry
- `app/routers/` — HTTP (`auth`, `plays`, `predict`, `stats`, `health`)
- `app/spotify/` — OAuth, sync, export parse
- `app/ml/` — `NextSongPredictor` + registry (`markov`, `popularity`, `artist`, `cooccurrence`, `item_knn`, `prompted`)
- `app/models.py` + `app/repositories.py` — SQLAlchemy

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
- Album art: `album_image_url` on plays; `POST /tracks/enrich-images` backfills via Spotify

## Do not commit

`.env`, `data/*.db`, `data/models/*` artifacts, privacy-export JSON

## Out of scope unless asked

Frontend UI polish, force-push / history rewrite
(Local prompted LLM / Ollama backends are OK when expanding `prompted`)
