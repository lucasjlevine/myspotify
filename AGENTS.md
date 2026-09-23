# AGENTS.md

Monorepo: `backend/` (FastAPI) + `frontend/` (Next.js).

**Precedence:** nearest `AGENTS.md` to the edited file wins. See also `.cursor/rules/`.

## Commands

```bash
# Both (from repo root)
npm run install:all
npm run dev

# Backend only
cd backend && uv sync && uv run main.py
cd backend && uv run python -m app.import_history
cd backend && uv run python -m app.ml.train
uv run python -m app.ml.train --model item_knn
uv run python -m app.enrich_features --batches 20
uv run python -m app.enrich_images --batches 20

# Tops use short_term / medium_term / long_term with a 3-plays/day cap
# (sleep-loop / binge resistant). Embedding uses genres + audio features.

# Frontend only
cd frontend && npm install && npm run dev
```

## Git

After substantive work: branch (`feature|fix|chore/...`) → commit → PR → merge to `main`. Details in `.cursor/rules/git-workflow.mdc`.

## Do not

- Commit `.env`, `*.db`, `data/models/*.json`, or `data/Spotify Extended Streaming History/`
- Push secrets or force-push `main`
