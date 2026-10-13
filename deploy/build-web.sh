#!/usr/bin/env bash
# Assemble Next.js standalone output for Silk Unit → deploy/dist/web/server.js
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FRONTEND="$ROOT/frontend"
DIST="$ROOT/deploy/dist/web"

cd "$FRONTEND"

if [[ ! -d node_modules ]]; then
  npm ci
fi

npm run build

rm -rf "$DIST"
mkdir -p "$DIST"

STANDALONE="$FRONTEND/.next/standalone"
if [[ -f "$STANDALONE/server.js" ]]; then
  cp -a "$STANDALONE"/. "$DIST"/
elif [[ -f "$STANDALONE/frontend/server.js" ]]; then
  cp -a "$STANDALONE/frontend"/. "$DIST"/
else
  echo "error: Next standalone server.js not found under .next/standalone" >&2
  find "$STANDALONE" -name 'server.js' 2>/dev/null || true
  exit 1
fi

mkdir -p "$DIST/.next"
rm -rf "$DIST/.next/static"
cp -a "$FRONTEND/.next/static" "$DIST/.next/static"

# Silk Unit requires document-root (public/) on disk even if empty.
mkdir -p "$DIST/public"
if [[ -d "$FRONTEND/public" ]]; then
  cp -a "$FRONTEND/public"/. "$DIST/public"/
fi

echo "Built Unit app → $DIST (server.js + public/)"
