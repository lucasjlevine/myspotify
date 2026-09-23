# AGENTS.md — Backend

Applies when editing `backend/`. Root [AGENTS.md](../AGENTS.md) + `.cursor/rules/` also apply.

## Purpose

FastAPI app: Spotify OAuth, play upsert/polling, Extended History import, Markov next-song baseline.

## Commands

```bash
cd backend
uv sync
uv run main.py
uv run python -m app.import_history
uv run python -m app.ml.train
```

## Layout

- `main.py` — thin entry only
- `app/routers/` — HTTP
- `app/spotify/` — OAuth, recently-played sync, export parse
- `app/ml/` — `NextSongPredictor` protocol + Markov; train CLI / predict service
- `app/models.py` + `app/repositories.py` — SQLAlchemy

## Rules

- Sessions via `session_scope()`; no raw `sqlite3`
- Never return tokens in API responses
- Deps: `uv add` / `uv sync`
- Upsert key `(played_at, track_id)`
- New models implement `app/ml/protocol.py`; artifact `data/models/markov.json`
- Redirect URI: loopback `127.0.0.1`, not `localhost`

## Do not commit

`.env`, `data/*.db`, `data/models/*.json`, `data/Spotify Extended Streaming History/`

## Out of scope unless asked

Frontend, neural models, force-push / rewriting git history
