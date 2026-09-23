# AGENTS.md — Frontend

Applies when editing `frontend/`. Root [AGENTS.md](../AGENTS.md) + `.cursor/rules/` also apply.

<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->

## Purpose

Next.js dashboard for listening stats, next-song prediction, and play history. Proxies `/api/*` to the FastAPI backend.

## Conventions

- API client: `src/lib/api/` (one module per backend router area)
- UI: shadcn under `src/components/ui/`; shell in `src/components/app-shell.tsx`
- Theme: dark Spotify-inspired tokens in `src/app/globals.css` (Outfit + Syne)
- New backend endpoints → add a typed function in `src/lib/api/`, then wire a page

## Commands

```bash
cd frontend && npm install && npm run dev
# or from repo root: npm run dev
```
