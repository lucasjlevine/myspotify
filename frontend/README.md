# Frontend

Next.js UI for myspotify: overview charts, predict playground, listening history.

## Setup

```bash
# From repo root (preferred)
npm run install:all
npm run dev
```

Or frontend only:

```bash
cd frontend
cp .env.example .env.local   # optional; defaults to http://127.0.0.1:8000
npm install
npm run dev
```

Open http://localhost:3000. Backend must be running (or use root `npm run dev`).

## Routes

| Path | Purpose |
|------|---------|
| `/` | Listening overview + charts |
| `/predict` | Model playground |
| `/history` | Recent plays + sync |
| `/auth/callback` | OAuth return from backend |

API calls use `/api/...` (Next rewrite → FastAPI).
