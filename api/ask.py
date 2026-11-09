"""Vercel serverless entry point for DoubtSahayak.

POST /api/ask  {question, language, subject}  -> solver.solve(...)
The BharatCode API key must be set as a Vercel environment variable
BHARATCODE_API_KEY (never in code). Without it, the solver answers from
the offline KB and says so — same behaviour as the local FastAPI backend.

NOTE: this file is written for Vercel's Python runtime and has NOT been
tested on a live Vercel deployment yet (no Vercel account used during the
build). The local FastAPI backend (backend/app.py) is the verified path.
"""
import json
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.solver import solve  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def _send(self, status: int, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._send(200, {"status": "ok", "service": "doubtsahayak"})

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length) or b"{}")
            result = solve(
                data.get("question", ""),
                data.get("language", "English"),
                data.get("subject", "Probability & Stats"),
            )
            self._send(200, result)
        except ValueError as exc:
            self._send(400, {"detail": str(exc)})
        except Exception as exc:  # keep the function from crashing the deploy
            self._send(500, {"detail": f"Server error: {exc}"})

    def log_message(self, *args):  # keep Vercel logs quiet
        pass
