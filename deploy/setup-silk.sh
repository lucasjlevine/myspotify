#!/usr/bin/env bash
# One-time Silk host prep: Python venv + fill YOUR_NETID in silk-sidecar.json
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP_NAME="${APP_NAME:-myspotify}"
NETID="${NETID:-$(whoami)}"
HOST="${NETID}.w3.uvm.edu"
VENV="${VENV:-$HOME/venvs/$APP_NAME}"

cd "$ROOT"

mkdir -p "$(dirname "$VENV")"

if command -v uv >/dev/null 2>&1; then
  # Sync backend deps into ~/venvs/myspotify (uv may fetch the required Python).
  (cd backend && UV_PROJECT_ENVIRONMENT="$VENV" uv sync)
else
  python3 -m venv "$VENV"
  # shellcheck disable=SC1091
  source "$VENV/bin/activate"
  pip install -U pip
  pip install -e "./backend"
fi

CONFIG="$ROOT/silk-sidecar.json"
if [[ ! -f "$CONFIG" ]]; then
  echo "error: missing $CONFIG" >&2
  exit 1
fi

tmp="$(mktemp)"
sed "s/YOUR_NETID/${NETID}/g" "$CONFIG" >"$tmp"
mv "$tmp" "$CONFIG"

chmod +x "$ROOT/deploy/build-web.sh" "$ROOT/deploy/setup-silk.sh"

echo "Silk prep done."
echo "  netid:   $NETID"
echo "  host:    https://${HOST}/"
echo "  venv:    $VENV"
echo "  config:  $CONFIG"
echo
echo "Next:"
echo "  1. Edit backend/.env — at minimum:"
echo "       FRONTEND_URL=https://${HOST}"
echo "       SPOTIFY_REDIRECT_URI=https://${HOST}/api/authorize/callback"
echo "       (+ Spotify client id/secret/state)"
echo "  2. Spotify Dashboard → add that redirect URI"
echo "  3. loginctl enable-linger \"\$USER\"   # or: silk-sidecar linger enable"
echo "  4. silk-sidecar deploy --config ./silk-sidecar.json"
echo "  5. silk-sidecar doctor --config ./silk-sidecar.json"
