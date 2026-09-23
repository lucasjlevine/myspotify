# AGENTS.md

Monorepo: `backend/` (FastAPI) + `frontend/` (Next.js).

**Precedence:** nearest `AGENTS.md` to the edited file wins. See also `.cursor/rules/`.

## Commands

```bash
# Backend
cd backend && uv sync && uv run main.py
cd backend && uv run python -m app.import_history
cd backend && uv run python -m app.ml.train

# Frontend
cd frontend && npm install && npm run dev
```

## Git

After substantive work: branch (`feature|fix|chore/...`) → commit → PR → merge to `main`. Details in `.cursor/rules/git-workflow.mdc`.

## Do not

- Commit `.env`, `*.db`, `data/models/*.json`, or `data/Spotify Extended Streaming History/`
- Push secrets or force-push `main`
