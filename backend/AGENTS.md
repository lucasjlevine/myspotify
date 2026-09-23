# AGENTS.md — Backend

Applies when editing `backend/`. Root [AGENTS.md](../AGENTS.md) + `.cursor/rules/` also apply.

## Purpose

FastAPI: Spotify OAuth, play upsert/polling, Extended History import, multi-model next-song prediction.

## Commands

```bash
cd backend
uv sync
uv run main.py
uv run python -m app.import_history
uv run python -m app.ml.train            # all
uv run python -m app.ml.train --model markov
```

## Layout

- `main.py` — thin entry
- `app/routers/` — HTTP
- `app/spotify/` — OAuth, sync, export parse
- `app/ml/` — `NextSongPredictor` + registry (`markov`, `popularity`, `artist`, `cooccurrence`, `item_knn`)
- `app/models.py` + `app/repositories.py` — SQLAlchemy

## Rules

- Sessions via `session_scope()`; no raw `sqlite3`
- Never return tokens in API responses
- Deps: `uv add` / `uv sync`
- Upsert key `(played_at, track_id)`
- New models: implement protocol, register in `app/ml/registry.py`
- Artifacts: `data/models/{id}.json` or `item_knn.joblib` (+ `.meta.json`)
- Redirect URI: `127.0.0.1`, not `localhost`

## Do not commit

`.env`, `data/*.db`, `data/models/*` artifacts, privacy-export JSON

## Out of scope unless asked

Frontend, neural nets, force-push / history rewrite
