# myspotify

Personal Spotify listening history + next-song prediction.

| Path | Role |
|------|------|
| [`backend/`](backend/) | FastAPI: OAuth, play collection, Extended History import, multi-model next-song prediction |
| [`frontend/`](frontend/) | Next.js dashboard (overview charts, predict playground, history) |
| [`deploy/`](deploy/) | Silk Unit build + [silk-sidecar](https://github.com/lucasjlevine/silk-sidecar) helpers |

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
- Health: http://127.0.0.1:8000/api/health  

Or run each side alone:

```bash
npm run dev:backend
npm run dev:frontend
```

Docs: [backend/README.md](backend/README.md) · Silk deploy: [deploy/README.md](deploy/README.md) · Agent notes: [AGENTS.md](AGENTS.md)

## Frontend notes

- Browser calls go to `/api/*`, rewritten by Next to `${API_UPSTREAM}/api/*` (default `http://127.0.0.1:8000`).
- Connect Spotify from the UI; OAuth redirect URI is `…/api/authorize/callback`, then the backend sends the user to `FRONTEND_URL/auth/callback`.

## Deploy on UVM Silk

Clone or sync this repo to `~/www-root/myspotify`, then see **[deploy/README.md](deploy/README.md)** (`silk-sidecar.json` + `deploy/build-web.sh`).
