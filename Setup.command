#!/bin/bash
set -euo pipefail
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

pause_on_exit() {
  read -r -p "Press Return to close this window." || true
}
trap pause_on_exit EXIT

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is required, but it was not found on PATH."
  exit 1
fi
if ! command -v node >/dev/null 2>&1; then
  echo "Node.js 22 or newer is required, but it was not found on PATH."
  echo "Install Node.js, then run Setup.command again."
  exit 1
fi
NODE_VERSION="$(node -p 'process.versions.node')"
NODE_MAJOR="${NODE_VERSION%%.*}"
if (( NODE_MAJOR < 22 )); then
  echo "Node.js 22 or newer is required. Found Node.js ${NODE_VERSION}."
  echo "Update Node.js, then run Setup.command again."
  exit 1
fi

export PIP_NO_CACHE_DIR=1

echo "Installing the downloader and FFmpeg inside this app folder..."
python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/python" -m pip install --upgrade pip
"$APP_DIR/.venv/bin/python" -m pip install --upgrade yt-dlp imageio-ffmpeg
mkdir -p "$APP_DIR/tools/bin"
FFMPEG_PATH="$("$APP_DIR/.venv/bin/python" -c 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())')"
ln -sf "$FFMPEG_PATH" "$APP_DIR/tools/bin/ffmpeg"

printf '\nSetup complete. Double-click Start.command, then open http://127.0.0.1:8765 in your browser.\n'
