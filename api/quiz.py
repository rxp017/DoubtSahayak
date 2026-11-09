"""Vercel serverless entry point for the DoubtSahayak quiz mode.

GET /api/quiz?subject=<subject>&n=5&seed=<int>  -> MCQ quiz from KB entries.
Same notes as api/ask.py: written for Vercel's Python runtime, not yet
tested on a live Vercel deployment. The local FastAPI backend
(backend/app.py) is the verified path.
"""
import json
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.solver import generate_quiz  # noqa: E402


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
            qs = parse_qs(urlparse(self.path).query)
            paper = (qs.get("paper") or ["DA"])[0]
            subject = (qs.get("subject") or [None])[0] or None
            n = int((qs.get("n") or ["5"])[0])
            seed_raw = (qs.get("seed") or [None])[0]
            seed = int(seed_raw) if seed_raw is not None else None
            self._send(200, generate_quiz(paper, subject, n, seed))
        except ValueError as exc:
            self._send(400, {"detail": str(exc)})
        except Exception as exc:  # keep the function from crashing the deploy
            self._send(500, {"detail": f"Server error: {exc}"})

    def log_message(self, *args):  # keep Vercel logs quiet
        pass
