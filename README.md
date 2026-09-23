# myspotify

Personal Spotify listening history + next-song prediction.

| Path | Role |
|------|------|
| [`backend/`](backend/) | FastAPI: OAuth, play collection, Extended History import, multi-model next-song prediction |
| [`frontend/`](frontend/) | Next.js dashboard (overview charts, predict playground, history) |

## Quick start (both apps)

From the repo root (requires Node + [`uv`](https://docs.astral.sh/uv/)):

```bash
npm run install:all
# create backend/.env — see backend/README.md
# optional: copy frontend/.env.example → frontend/.env.local
npm run dev
```

- Frontend: http://localhost:3000  
- Backend / API docs: http://127.0.0.1:8000/docs  

Or run each side alone:

```bash
npm run dev:backend
npm run dev:frontend
```

Docs: [backend/README.md](backend/README.md) · Agent notes: [AGENTS.md](AGENTS.md), [backend/AGENTS.md](backend/AGENTS.md)

## Frontend notes

- Browser calls go to `/api/*`, rewritten by Next to the FastAPI server (`BACKEND_URL`, default `http://127.0.0.1:8000`).
- Connect Spotify from the UI; OAuth still uses the backend redirect URI (`127.0.0.1:8000`), then redirects to the app.
