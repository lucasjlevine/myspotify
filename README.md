# myspotify

Personal Spotify listening history + next-song prediction.

| Path | Role |
|------|------|
| [`backend/`](backend/) | FastAPI: OAuth, play collection, Extended History import, Markov next-song baseline |
| [`frontend/`](frontend/) | Next.js UI |

## Quick start (backend)

```bash
cd backend
uv sync
# create .env — see backend/README.md
uv run main.py
```

Docs: [backend/README.md](backend/README.md) · Agent notes: [AGENTS.md](AGENTS.md), [backend/AGENTS.md](backend/AGENTS.md)
