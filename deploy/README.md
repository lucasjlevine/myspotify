# Deploy on UVM Silk ([silk-sidecar](https://github.com/lucasjlevine/silk-sidecar))

```
Browser → https://{NETID}.w3.uvm.edu/...
                → Silk Unit [Next.js standalone]
Browser → https://{NETID}.w3.uvm.edu/api/...
                → Next rewrite → 127.0.0.1:8000/api/...
                                        ↑
                              systemd --user + linger
```

## Prerequisites on Silk

1. Install [silk-sidecar](https://github.com/lucasjlevine/silk-sidecar) (`~/bin` on `PATH`).
2. `loginctl enable-linger "$USER"` (confirm `Linger=yes`).
3. Put this repo at **`~/www-root/myspotify`** (paths in `silk-sidecar.json` assume that).

## First-time setup

```bash
cd ~/www-root/myspotify
./deploy/setup-silk.sh          # venv + fill YOUR_NETID
# edit backend/.env (see below)
silk-sidecar linger enable
silk-sidecar deploy --config ./silk-sidecar.json
silk-sidecar doctor --config ./silk-sidecar.json
```

Open `https://{NETID}.w3.uvm.edu/`.

### `backend/.env` (Silk)

```env
FRONTEND_URL=https://YOUR_NETID.w3.uvm.edu
SPOTIFY_REDIRECT_URI=https://YOUR_NETID.w3.uvm.edu/api/authorize/callback
CORS_ORIGINS=https://YOUR_NETID.w3.uvm.edu
# …same Spotify secrets as local
```

Add the redirect URI in the Spotify Developer Dashboard. Backend routes are under `/api/…` (health: `/api/health`).

## Day-to-day

| Change | Command |
|--------|---------|
| Backend | `silk-sidecar restart --config ./silk-sidecar.json` |
| Frontend | `./deploy/build-web.sh` then `silk-sidecar frontend load --config ./silk-sidecar.json` |
| Full | `silk-sidecar deploy --config ./silk-sidecar.json` |
| Stale UI | `silk-sidecar frontend kill-stale --broad --config ./silk-sidecar.json` then `frontend load` |
| Logs | `silk-sidecar logs -f --config ./silk-sidecar.json` |

## Logout test (required)

```bash
curl -fsS http://127.0.0.1:8000/api/health
# exit SSH, wait ~30s, reconnect
curl -fsS http://127.0.0.1:8000/api/health
systemctl --user status myspotify-api
```

## Local laptop

Unchanged flow from repo root: `npm run install:all` && `npm run dev`.

- Next proxies `/api/*` → `API_UPSTREAM` (default `http://127.0.0.1:8000`) `/api/*`
- Local redirect URI: `http://127.0.0.1:8000/api/authorize/callback`
