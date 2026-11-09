"""Vercel serverless entry point for the DoubtSahayak paper list.

GET /api/papers  -> all GATE papers with subjects and KB entry counts.
Same notes as api/ask.py: written for Vercel's Python runtime, not yet
tested on a live Vercel deployment. The local FastAPI backend
(backend/app.py) is the verified path.
"""
import json
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.solver import papers_info  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def _send(self, status: int, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        try:
            self._send(200, {"papers": papers_info()})
        except Exception as exc:  # keep the function from crashing the deploy
            self._send(500, {"detail": f"Server error: {exc}"})

    def log_message(self, *args):  # keep Vercel logs quiet
        pass
