#!/usr/bin/env python3
"""Tiny local API for the Skills Index app. Loopback only.

    GET  /catalog  -> latest export (same JSON the exporter writes)
    POST /refresh  -> re-run the exporter with full MCP health checks
    GET  /status   -> {"running": bool, "lastRun": unix time, "lastExit": int}

Started automatically by the Claude Code SessionStart hook:
    python3 tools/s2pb_server.py &
"""
import json
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = 8765
HERE = Path(__file__).resolve().parent
EXPORTER = HERE / "export_catalog.py"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/storage/emulated/0/Public/skills-catalog-sync.json")

state = {"running": False, "lastRun": None, "lastExit": None}
lock = threading.Lock()


def refresh():
    with lock:
        if state["running"]:
            return
        state["running"] = True
    try:
        r = subprocess.run([sys.executable, str(EXPORTER), "--out", str(OUT)], capture_output=True)
        state["lastExit"] = r.returncode
    finally:
        state["lastRun"] = int(time.time())
        state["running"] = False


class Handler(BaseHTTPRequestHandler):
    def send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/catalog":
            try:
                self.send(200, OUT.read_bytes())
            except FileNotFoundError:
                self.send(404, {"error": "no export yet; POST /refresh"})
        elif self.path == "/status":
            self.send(200, state)
        else:
            self.send(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/refresh":
            threading.Thread(target=refresh, daemon=True).start()
            self.send(202, {"started": True})
        else:
            self.send(404, {"error": "not found"})

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    try:
        server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    except OSError:
        sys.exit(0)  # already running
    server.serve_forever()
