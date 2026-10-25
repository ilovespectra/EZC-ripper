#!/usr/bin/env python3
"""Local playlist media saver with MP4 video and MP3 audio output."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import json
import os
import re
import shutil
import subprocess
import threading

HOST = "127.0.0.1"
PORT = 8765
ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT = Path.home() / "Downloads" / "Recovered YouTube Music"
PAGE = ROOT / "index.html"
LOCK = threading.Lock()
STATE = {
    "status": "idle", "message": "Ready", "percent": 0,
    "playlist_item": None, "playlist_total": None,
    "saved_count": 0, "saved_paths": [], "logs": [], "error": None, "format": "mp4",
}

def dependencies():
    local_ytdlp = ROOT / ".venv" / "bin" / "yt-dlp"
    local_ffmpeg = ROOT / "tools" / "bin" / "ffmpeg"
    return {
        "yt-dlp": str(local_ytdlp) if local_ytdlp.is_file() else shutil.which("yt-dlp"),
        "ffmpeg": str(local_ffmpeg) if local_ffmpeg.is_file() else shutil.which("ffmpeg"),
        "node": shutil.which("node"),
    }

def state_copy():
    with LOCK:
        result = dict(STATE)
        result["logs"] = list(STATE["logs"])
        result["saved_paths"] = list(STATE["saved_paths"])
    result["tools"] = dependencies()
    result["default_output"] = str(DEFAULT_OUTPUT)
    return result

def update(**values):
    with LOCK:
        STATE.update(values)

def allowed_youtube_playlist(url):
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    valid_host = host in {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"}
    playlist_id = parse_qs(parsed.query).get("list", [""])[0]
    return parsed.scheme == "https" and host in valid_host and bool(playlist_id)

class Handler(BaseHTTPRequestHandler):
    server_version = "LocalPlaylistSaver/1.0"

    def log_message(self, *_args):
        pass

    def send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def local_request_only(self):
        allowed_hosts = {f"127.0.0.1:{PORT}", f"localhost:{PORT}"}
        if self.headers.get("Host", "") not in allowed_hosts:
            self.send_json(403, {"error": "Local requests only"})
            return False
        origin = self.headers.get("Origin")
        if origin and origin not in {f"http://127.0.0.1:{PORT}", f"http://localhost:{PORT}"}:
            self.send_json(403, {"error": "Requests must come from this local page"})
            return False
        return True

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            try:
                body = PAGE.read_bytes()
            except OSError:
                self.send_json(500, {"error": "The local UI file is missing"})
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        elif path == "/api/status":
            if self.local_request_only():
                self.send_json(200, state_copy())
        else:
            self.send_json(404, {"error": "Not found"})

    def do_POST(self):
        if not self.local_request_only():
            return
        if urlparse(self.path).path != "/api/download":
            self.send_json(404, {"error": "Not found"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size <= 0 or size > 32768:
                self.send_json(400, {"error": "Invalid request size"})
                return
            data = json.loads(self.rfile.read(size).decode("utf-8"))
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            self.send_json(400, {"error": "Invalid JSON request"})
            return

        url = str(data.get("url", "")).strip()
        if not allowed_youtube_playlist(url):
            self.send_json(400, {"error": "Paste an HTTPS YouTube playlist URL containing a list= playlist ID."})
            return

        output_format = str(data.get("format", "mp4")).lower()
        if output_format not in {"mp3", "mp4"}:
            self.send_json(400, {"error": "Choose MP3 or MP4 as the output format."})
            return

        folder = str(data.get("folder", "")).strip()
        output_dir = Path(folder).expanduser() if folder else DEFAULT_OUTPUT
        try:
            output_dir = output_dir.resolve()
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self.send_json(400, {"error": f"Could not create the save folder: {exc}"})
            return

        tools = dependencies()
        missing = [name for name, path in tools.items() if not path]
        if missing:
            self.send_json(503, {
                "error": "Missing local tools: " + ", ".join(missing),
                "setup": "Run Setup.command once, then restart this page.",
            })
            return
        if not getattr(self.server, "job_lock", None).acquire(blocking=False):
            self.send_json(409, {"error": "A playlist download is already running."})
            return

        update(status="downloading", message="Starting playlist…", percent=0,
               playlist_item=None, playlist_total=None, saved_count=0,
               saved_paths=[], logs=[], error=None, format=output_format)
        thread = threading.Thread(target=download_playlist, args=(url, output_dir, output_format), daemon=True)
        thread.start()
        self.send_json(202, {"status": "downloading", "save_folder": str(output_dir), "format": output_format})

def download_playlist(url, output_dir, output_format):
    tools = dependencies()
    output_template = "%(playlist_title)s/%(playlist_index)03d - %(title)s [%(id)s].%(ext)s"
    command = [
        tools["yt-dlp"],
        "--yes-playlist", "--ignore-errors", "--newline", "--progress",
        "--js-runtimes", "node", "--remote-components", "ejs:github",
        # Prefer the Mac's system trust bundle. Framework Python may have no
        # populated OpenSSL CA file, which otherwise makes YouTube TLS fail.
        "--compat-options", "no-certifi",
        "--ffmpeg-location", tools["ffmpeg"],
    ]
    if output_format == "mp3":
        command += ["-f", "bestaudio/best", "--extract-audio", "--audio-format", "mp3", "--audio-quality", "0"]
    else:
        command += [
            "-f", "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bestvideo+bestaudio/best",
            "--merge-output-format", "mp4", "--remux-video", "mp4",
        ]
    command += [
        "--output", output_template,
        "--paths", str(output_dir),
        "--print", "after_move:filepath",
        url,
    ]
    recent = []
    saved = []
    item = None
    total = None
    pct = 0
    errors_seen = False
    try:
        child_env = os.environ.copy()
        system_ca = Path("/etc/ssl/cert.pem")
        if system_ca.is_file():
            child_env.setdefault("SSL_CERT_FILE", str(system_ca))
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, bufsize=1, env=child_env)
        item_pattern = re.compile(r"Downloading item (\d+) of (\d+)", re.I)
        percent_pattern = re.compile(r"(\d{1,3}(?:\.\d+)?)%")
        for raw in proc.stdout:
            line = raw.strip()
            if not line:
                continue
            recent.append(line)
            recent = recent[-35:]
            if "error" in line.lower() or "failed" in line.lower():
                errors_seen = True
            m = item_pattern.search(line)
            if m:
                item, total = int(m.group(1)), int(m.group(2))
            p = percent_pattern.search(line)
            if p:
                file_pct = max(0.0, min(float(p.group(1)), 100.0))
                if total:
                    pct = int(((max((item or 1) - 1, 0) + file_pct / 100) / total) * 100)
                else:
                    pct = int(file_pct)
            if line.lower().endswith((".mp4", ".mp3")) and ("/" in line or "\\" in line):
                saved.append(line)
            update(message=line[:240], percent=min(pct, 99), playlist_item=item,
                   playlist_total=total, saved_count=len(saved), saved_paths=saved[-20:],
                   logs=recent)
        return_code = proc.wait()
        if return_code == 0:
            status = "partial" if errors_seen else "complete"
            msg = "Finished with some item errors; see the log." if errors_seen else "Playlist download complete."
            update(status=status, message=msg, percent=100, saved_count=len(saved),
                   saved_paths=saved[-20:], logs=recent, error=None)
        else:
            detail = "\n".join(recent[-20:]) or f"yt-dlp exited with code {return_code}"
            update(status="error", message="Download stopped with an error.", error=detail,
                   percent=pct, saved_count=len(saved), saved_paths=saved[-20:], logs=recent)
    except FileNotFoundError as exc:
        update(status="error", message="A required tool could not be started.", error=str(exc), logs=recent)
    except Exception as exc:
        update(status="error", message="Download failed.", error=str(exc), logs=recent)
    finally:
        server_lock = getattr(_server, "job_lock", None)
        if server_lock:
            server_lock.release()

_server = None

def main():
    global _server
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    server.daemon_threads = True
    server.job_lock = threading.Lock()
    _server = server
    print(f"Playlist Media Saver is local at http://{HOST}:{PORT}")
    print("Keep this window open while downloading. Press Ctrl+C to stop.")
    server.serve_forever()

if __name__ == "__main__":
    main()
