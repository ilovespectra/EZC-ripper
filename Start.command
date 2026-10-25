#!/bin/bash
set -u
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
export PATH="$APP_DIR/.venv/bin:$APP_DIR/tools/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
cd "$APP_DIR"

if /usr/bin/curl -fsS --max-time 2 http://127.0.0.1:8765/api/status >/dev/null 2>&1; then
  echo "Playlist Media Saver is already running at http://127.0.0.1:8765"
  read -r -p "Press Return to close this window." || true
  exit 0
fi

python3 server.py
