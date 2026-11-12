"""DoubtSahayak FastAPI backend — local dev server.

Run:  uvicorn app:app --reload --port 8000   (from the backend/ folder,
with the venv active; see ../README.md)
"""
import os
import sys

# Works whether uvicorn runs from backend/ (uvicorn app:app) or from the
# project root (uvicorn backend.app:app --app-dir .).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    from solver import (
        EXAMPLES,
        SUBJECTS,
        generate_quiz,
        kb_grouped,
        kb_summary,
        papers_info,
        solve,
    )
except ImportError:  # imported as part of the backend package
    from backend.solver import (
        EXAMPLES,
        SUBJECTS,
        generate_quiz,
        kb_grouped,
        kb_summary,
        papers_info,
        solve,
    )

app = FastAPI(title="DoubtSahayak API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # MVP: same-origin in prod, localhost in dev
    allow_methods=["*"],
    allow_headers=["*"],
)


class SolveRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    language: str = "English"
    subject: str = "Probability & Stats"
    paper: str = "DA"
    # "bharatcode" (default) or "adaption" (Adaption-tuned model; falls
    # back to BharatCode when the tuned model is not deployed yet).
    engine: str = "bharatcode"


@app.get("/health")
def health():
    return {"status": "ok", "service": "doubtsahayak"}


@app.get("/api/subjects")
def subjects():
    return {"subjects": SUBJECTS, "languages": ["English", "Telugu", "Hindi"]}


@app.get("/api/examples")
def examples():
    return {"examples": EXAMPLES}


@app.get("/api/papers")
def papers():
    """All GATE papers with their subjects and KB entry counts."""
    return {"papers": papers_info()}


@app.get("/api/kb")
def kb():
    """Full knowledge base grouped by paper, then subject — powers the
    formula sheet."""
    return {"papers": kb_grouped(), "summary": kb_summary()}


@app.get("/api/kb/summary")
def kb_summary_endpoint():
    return kb_summary()


@app.get("/api/quiz")
def quiz(paper: str = "DA", subject: str | None = None, n: int = 5,
         seed: int | None = None):
    """MCQ quiz built from KB entries for one paper (and optional subject).
    `seed` makes a run reproducible."""
    try:
        return generate_quiz(paper, subject or None, n, seed)
    except ValueError as exc:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/ask")
def ask(req: SolveRequest):
    return solve(req.question, req.language, req.subject, req.paper, req.engine)


# Backwards-compatible alias (same handler, same path the old dev flow used).
@app.post("/api/solve")
def ask_alias(req: SolveRequest):
    return solve(req.question, req.language, req.subject, req.paper, req.engine)
