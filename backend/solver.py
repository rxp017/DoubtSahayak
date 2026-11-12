"""DoubtSahayak core logic: KB retrieval + BharatCode API call + offline fallback.

No API key is hardcoded anywhere. The key comes from the BHARATCODE_API_KEY
environment variable only. Without a key, the solver answers from the curated
KB (backend/kb.json) and says so plainly — it never pretends a live LLM call
happened.

KB entries carry two provenance fields:
- "paper": the GATE paper code (DA, ME, CE, ...). DA is the deepest paper:
  its entries come from the author's own drill packs plus standard
  reference material for all DA subjects. The other 29 papers carry
  introductory CORE notes only (5-8 entries each) — standard reference
  material, NOT the full GATE syllabus and NOT the author's own notes.
- "source": "drill-notes" (the author's own GATE DA drill packs — the most
  trustworthy) or "reference" (standard textbook-level material researched
  from public sources).
"""
import json
import os
import random
import re
from pathlib import Path

import httpx

KB_PATH = Path(__file__).with_name("kb.json")
BHARATCODE_BASE = "https://bharatcode.ai/api/model/v1"
DEFAULT_MODEL = os.environ.get("BHARATCODE_MODEL", "qwen-3.8-27b")
FALLBACK_MODEL = "deepseek-v4.1-flash"

# Adaption (12 Nov 2026): a second answer engine — a model fine-tuned on
# the GATE knowledge base (adaption/training-data.jsonl, 3,112 examples)
# via Adaption Labs. Adaption trains on Together AI infrastructure and its
# checkpoints are served through Together's OpenAI-compatible inference
# endpoint, so the app calls the tuned model there. Both values come from
# environment variables only (ADAPTION_API_KEY, ADAPTION_MODEL); the key
# is never in code. If either is missing, the Adaption engine is
# unavailable and solve() falls back to BharatCode, saying so in the
# warning — it never pretends the tuned model answered.
# NOTE: training is covered by the 1,000 free Adaption credits, but
# SERVING a fine-tuned model on Together needs a dedicated endpoint,
# billed per GPU-hour — check the Adaption/Together dashboard before
# deploying, and do not pay anything without the owner's word.
ADAPTION_BASE_URL = os.environ.get(
    "ADAPTION_BASE_URL", "https://api-inference.together.ai/v1"
)

STOPWORDS = {
    "what", "is", "the", "a", "an", "and", "or", "of", "in", "on", "for",
    "to", "how", "do", "does", "find", "calculate", "solve", "explain",
    "ante", "enti", "ela", "cheppu", "meaning", "kya", "hai", "ka", "ki",
    "ke", "aur", "mein", "please", "pls", "bro", "give", "example",
}

LANGUAGE_INSTRUCTIONS = {
    "English": "Answer in English.",
    "Telugu": "Answer in Telugu (Telugu script). Keep formulas and symbols in standard maths notation.",
    "Hindi": "Answer in Hindi (Devanagari script). Keep formulas and symbols in standard maths notation.",
}

# All 30 GATE papers + General Aptitude (common 15-mark section): code ->
# full name + subject areas covered in the KB. Subjects are the areas
# the KB actually has entries for, not the full official syllabus — the
# KB is introductory core notes per paper (DA deepest), except DA.
PAPERS = {
    "AE": {"name": "Aerospace Engineering", "subjects": ["Aerodynamics", "Flight Mechanics", "Aerospace Structures", "Propulsion", "Engineering Mathematics"]},
    "AG": {"name": "Agricultural Engineering", "subjects": ["Agricultural Engineering", "Soil & Water", "Farm Machinery", "Food Processing", "Engineering Mathematics"]},
    "AR": {"name": "Architecture and Planning", "subjects": ["Architecture", "Planning", "Building Materials", "Urban Design", "History of Architecture"]},
    "BM": {"name": "Biomedical Engineering", "subjects": ["Biomedical Signals", "Biomechanics", "Medical Imaging", "Biomaterials", "Physiology", "Engineering Mathematics"]},
    "BT": {"name": "Biotechnology", "subjects": ["Biochemistry", "Molecular Biology", "Bioprocess Engineering", "Genetics", "Engineering Mathematics"]},
    "CE": {"name": "Civil Engineering", "subjects": ["Structural Analysis", "Geotechnical Engineering", "Fluid Mechanics & Hydraulics", "Transportation", "Environmental Engineering", "Surveying", "Engineering Mathematics", "Construction Materials and Management"]},
    "CH": {"name": "Chemical Engineering", "subjects": ["Chemical Process Calculations", "Thermodynamics", "Fluid Mechanics", "Heat Transfer", "Mass Transfer", "Chemical Reaction Engineering", "Engineering Mathematics"]},
    "CS": {"name": "Computer Science & Information Technology", "subjects": ["Algorithms", "Data Structures", "Theory of Computation", "Operating Systems", "DBMS", "Computer Networks", "Compiler Design", "Discrete Mathematics", "Engineering Mathematics", "Digital Logic", "Computer Organization and Architecture"]},
    "CY": {"name": "Chemistry", "subjects": ["Physical Chemistry", "Organic Chemistry", "Inorganic Chemistry", "Spectroscopy"]},
    "DA": {"name": "Data Science & Artificial Intelligence", "subjects": ["Probability & Stats", "Linear Algebra", "Calculus & Optimization", "Programming/DSA", "Database Management & Warehousing", "Machine Learning", "Artificial Intelligence"]},
    "EC": {"name": "Electronics & Communication Engineering", "subjects": ["Networks", "Electronic Devices", "Analog Circuits", "Digital Circuits", "Signals & Systems", "Communication", "Control Systems", "Engineering Mathematics"]},
    "EE": {"name": "Electrical Engineering", "subjects": ["Electric Circuits", "Electromagnetic Fields", "Power Systems", "Control Systems", "Electrical Machines", "Signals & Systems", "Engineering Mathematics"]},
    "ES": {"name": "Environmental Science & Engineering", "subjects": ["Environmental Chemistry", "Water Treatment", "Air Pollution", "Waste Management", "Engineering Mathematics"]},
    "EY": {"name": "Ecology and Evolution", "subjects": ["Ecology", "Evolution", "Biodiversity", "Conservation Biology"]},
    "GA": {"name": "General Aptitude", "subjects": ["Verbal Aptitude", "Quantitative Aptitude", "Logical Reasoning", "Data Interpretation"]},
    "GE": {"name": "Geomatics Engineering", "subjects": ["Surveying", "Geomatics", "Remote Sensing", "GIS", "Photogrammetry", "Engineering Mathematics"]},
    "GG": {"name": "Geology & Geophysics", "subjects": ["Geology", "Geophysics", "Seismology", "Mineralogy"]},
    "IN": {"name": "Instrumentation Engineering", "subjects": ["Instrumentation", "Control Systems", "Signals & Systems", "Electrical Circuits", "Measurements", "Engineering Mathematics"]},
    "MA": {"name": "Mathematics", "subjects": ["Linear Algebra", "Calculus", "Probability & Statistics", "Differential Equations", "Numerical Methods", "Real Analysis", "Complex Analysis"]},
    "ME": {"name": "Mechanical Engineering", "subjects": ["Thermodynamics", "Fluid Mechanics", "Strength of Materials", "Theory of Machines", "Heat Transfer", "Manufacturing Science", "Engineering Mathematics", "Applied Mechanics and Design", "Materials, Manufacturing and Industrial Engineering"]},
    "MN": {"name": "Mining Engineering", "subjects": ["Mining Methods", "Rock Mechanics", "Mine Ventilation", "Mineral Processing", "Engineering Mathematics"]},
    "MT": {"name": "Metallurgical Engineering", "subjects": ["Physical Metallurgy", "Mechanical Metallurgy", "Thermodynamics", "Extractive Metallurgy", "Engineering Mathematics"]},
    "NM": {"name": "Naval Architecture & Marine Engineering", "subjects": ["Naval Architecture", "Marine Engineering", "Hydrodynamics", "Ship Structures", "Engineering Mathematics"]},
    "PE": {"name": "Petroleum Engineering", "subjects": ["Reservoir Engineering", "Drilling", "Production Engineering", "Petroleum Geology", "Engineering Mathematics"]},
    "PH": {"name": "Physics", "subjects": ["Mechanics", "Electromagnetism", "Quantum Mechanics", "Thermodynamics & Statistical Physics", "Electronics", "Mathematical Physics"]},
    "PI": {"name": "Production & Industrial Engineering", "subjects": ["Manufacturing", "Industrial Engineering", "Operations Research", "Quality Control", "Metrology", "Engineering Mathematics"]},
    "RA": {"name": "Robotics & Automation", "subjects": ["Kinematics", "Dynamics & Control", "Sensors & Actuators", "Automation & PLC", "Trajectory Planning", "Motion Planning", "Mechatronics Basics", "Analog Circuits & Embedded Systems", "Signals & Systems", "Mechanics of Materials", "Machine Design"]},
    "ST": {"name": "Statistics", "subjects": ["Probability", "Statistical Inference", "Regression", "Sampling", "Hypothesis Testing", "Stochastic Processes", "Multivariate Analysis"]},
    "XE": {"name": "Engineering Sciences", "subjects": ["Engineering Mathematics", "Fluid Mechanics", "Solid Mechanics", "Materials Science", "Thermodynamics", "Energy Science", "Polymer Science and Engineering", "Atmospheric and Oceanic Sciences", "Food Technology", "XE9 Textile Engineering & Fibre Science"]},
    "XH": {"name": "Humanities & Social Sciences", "subjects": ["Economics", "Sociology", "Psychology", "English Comprehension", "Reasoning & Aptitude", "Linguistics", "Philosophy"]},
    "XL": {"name": "Life Sciences", "subjects": ["Life Sciences", "Biochemistry", "Microbiology", "Genetics", "Plant & Animal Physiology", "Botany", "Zoology", "Food Technology"]},
}

# Backwards-compatible: the DA subject list.
SUBJECTS = PAPERS["DA"]["subjects"]

with KB_PATH.open(encoding="utf-8") as _f:
    _KB = json.load(_f)
ENTRIES = _KB["entries"]
for _e in ENTRIES:
    # Entries written before the "source"/"paper" fields existed are the
    # author's own DA drill notes.
    _e.setdefault("source", "drill-notes")
    _e.setdefault("paper", "DA")


def _source_label(source: str) -> str:
    return "Your GATE DA notes" if source == "drill-notes" else "Standard reference"


def grounding_source(notes: list[dict]) -> str:
    """Provenance of the retrieved notes: drill-notes | reference | mixed | none."""
    if not notes:
        return "none"
    sources = {n.get("source", "drill-notes") for n in notes}
    if sources == {"drill-notes"}:
        return "drill-notes"
    if sources == {"reference"}:
        return "reference"
    return "mixed"


def papers_info() -> list[dict]:
    """All 30 papers with their subjects and KB entry counts."""
    out = []
    for code in sorted(PAPERS):
        entries = [e for e in ENTRIES if e.get("paper") == code]
        out.append({
            "code": code,
            "name": PAPERS[code]["name"],
            "subjects": PAPERS[code]["subjects"],
            "total": len(entries),
            "drill_notes": sum(1 for e in entries if e.get("source") == "drill-notes"),
            "reference": sum(1 for e in entries if e.get("source") == "reference"),
        })
    return out


def kb_summary() -> dict:
    """Per-paper entry counts, split by source, for the formula sheet."""
    out = {}
    for code in sorted(PAPERS):
        entries = [e for e in ENTRIES if e.get("paper") == code]
        out[code] = {
            "total": len(entries),
            "drill_notes": sum(1 for e in entries if e.get("source") == "drill-notes"),
            "reference": sum(1 for e in entries if e.get("source") == "reference"),
            "subjects": {
                s: sum(1 for e in entries if e["subject"] == s)
                for s in PAPERS[code]["subjects"]
            },
        }
    out["_total"] = len(ENTRIES)
    return out


def kb_grouped() -> dict:
    """All KB entries grouped by paper, then subject, for the formula sheet."""
    grouped = {code: {s: [] for s in PAPERS[code]["subjects"]} for code in PAPERS}
    for e in ENTRIES:
        grouped.setdefault(e.get("paper", "DA"), {}).setdefault(e["subject"], []).append(e)
    return grouped


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {w for w in words if w not in STOPWORDS and len(w) > 1}


def retrieve(question: str, subject: str, paper: str = "DA", top_n: int = 3) -> list[dict]:
    """Keyword-overlap retrieval over the curated KB, paper- and
    subject-filtered first."""
    q = _tokens(question)
    scored = []
    for entry in ENTRIES:
        if entry.get("paper", "DA") != paper:
            continue
        if subject and entry["subject"] != subject:
            continue
        hay = _tokens(" ".join([
            entry["topic"], entry["fact"], entry["formula"],
            " ".join(entry["keywords"]),
        ]))
        score = len(q & hay)
        # Exact keyword hits count double — cheap relevance boost.
        score += sum(2 for kw in entry["keywords"] if kw.lower() in question.lower())
        if score > 0:
            scored.append((score, entry))
    scored.sort(key=lambda s: -s[0])
    return [e for _, e in scored[:top_n]]


def _notes_text(notes: list[dict]) -> str:
    parts = []
    for n in notes:
        tag = "AUTHOR'S DRILL NOTES" if n.get("source") == "drill-notes" else "STANDARD REFERENCE"
        parts.append(
            f"- [{tag} | {n['topic']}] {n['fact']} Formula: {n['formula']} "
            f"Worked example: {n['example']}"
        )
    return "\n".join(parts)


def _offline_answer(question: str, notes: list[dict], language: str) -> str:
    """Answer built ONLY from KB entries. Used when no API key is configured."""
    if not notes:
        return (
            "No grounding notes cover this doubt yet, and no BharatCode API key "
            "is configured, so I cannot answer it right now. Add a "
            "BHARATCODE_API_KEY (free student tier) and ask again — or add this "
            "topic to backend/kb.json from your own notes."
        )
    lines = [
        "Offline answer — built only from the knowledge base "
        "(no BharatCode API key configured, so no LLM was called):",
        "",
    ]
    for n in notes:
        lines.append(f"**{n['topic']}** [{_source_label(n.get('source', 'drill-notes'))}]")
        lines.append(n["fact"])
        lines.append(f"Formula: {n['formula']}")
        lines.append(f"Worked example: {n['example']}")
        lines.append("")
    if language in ("Telugu", "Hindi"):
        lines.append(
            "Note: the knowledge base is stored in English, so this answer is "
            f"in English. Set an API key to get the same answer in {language}."
        )
    return "\n".join(lines).strip()


def generate_quiz(paper: str = "DA", subject: str | None = None, n: int = 5,
                  seed: int | None = None) -> dict:
    """Build a multiple-choice quiz from KB entries.

    Two question types, both drawn from real KB content:
    - "topic": show a formula, pick the topic it belongs to.
    - "formula": show a topic + fact, pick the matching formula.
    The correct answer is included in the response (self-quiz, no grading
    server-side); the frontend gives instant feedback per question.
    """
    rng = random.Random(seed)
    if paper not in PAPERS:
        raise ValueError(f"Unknown paper: {paper}")
    if subject and subject not in PAPERS[paper]["subjects"]:
        raise ValueError(f"Unknown subject for {paper}: {subject}")
    pool = [e for e in ENTRIES
            if e.get("paper") == paper and (not subject or e["subject"] == subject)]
    pool_note = None
    if len(pool) < 4:
        # Small subject (e.g. a paper with only a few notes per subject):
        # quiz across the whole paper instead of failing.
        pool = [e for e in ENTRIES if e.get("paper") == paper]
        pool_note = (
            f"Only {len([e for e in ENTRIES if e.get('paper') == paper and e['subject'] == subject])} "
            f"notes in {subject}, so this quiz draws from all of {paper}."
            if subject else None
        )
    if len(pool) < 4:
        raise ValueError("Not enough entries to build a quiz for this paper/subject.")
    n = max(1, min(int(n), 10, len(pool)))
    chosen = rng.sample(pool, n)

    def _distractors(field: str, correct: str, entry_id: str) -> list[str]:
        seen = {correct}
        cands = [e[field] for e in pool if e["id"] != entry_id and e[field] not in seen]
        rng.shuffle(cands)
        picked = []
        for c in cands:
            if c not in seen:
                seen.add(c)
                picked.append(c)
            if len(picked) == 3:
                break
        # Fall back to the whole paper's KB if the subject pool is too small.
        if len(picked) < 3:
            rest = [e[field] for e in ENTRIES
                    if e.get("paper") == paper and e[field] not in seen]
            rng.shuffle(rest)
            for c in rest:
                if c not in seen:
                    seen.add(c)
                    picked.append(c)
                if len(picked) == 3:
                    break
        return picked

    questions = []
    for e in chosen:
        qtype = rng.choice(["topic", "formula"])
        if qtype == "topic":
            prompt = f"Which topic does this formula belong to?\n{e['formula']}"
            correct = e["topic"]
            options = _distractors("topic", correct, e["id"]) + [correct]
        else:
            prompt = f"Which formula matches this topic?\n{e['topic']} — {e['fact']}"
            correct = e["formula"]
            options = _distractors("formula", correct, e["id"]) + [correct]
        rng.shuffle(options)
        questions.append({
            "id": e["id"],
            "paper": e.get("paper", "DA"),
            "subject": e["subject"],
            "source": e.get("source", "drill-notes"),
            "type": qtype,
            "prompt": prompt,
            "options": options,
            "answer": correct,
            "correct_index": options.index(correct),
        })
    return {
        "paper": paper,
        "subject": subject or "All subjects",
        "pool_note": pool_note,
        "count": len(questions),
        "questions": questions,
    }


def _clean_no_proxy():
    """Context manager: httpx rejects this sandbox runtime's bracketed
    IPv6 entries in NO_PROXY ([::1], [fd8b:...]) at Client() construction
    (InvalidURL: Invalid port), which broke BOTH the BharatCode and the
    Adaption calls locally — they fell back to offline-kb silently.
    Temporarily drop just the bracketed entries; localhost, 127.0.0.1
    and unbracketed ::1 still bypass the proxy. No-op on Vercel, where
    no such entries exist. Restores the original values afterwards."""
    import contextlib

    keys = [k for k in ("no_proxy", "NO_PROXY") if k in os.environ]
    saved = {k: os.environ[k] for k in keys}

    @contextlib.contextmanager
    def _cm():
        try:
            for k in keys:
                os.environ[k] = ",".join(
                    h for h in saved[k].split(",") if not h.startswith("[")
                )
            yield
        finally:
            for k, v in saved.items():
                os.environ[k] = v

    return _cm()


def _call_bharatcode(prompt: str, api_key: str) -> tuple[str, str]:
    """One chat-completions call; retries once with the fallback model on a
    model error. Returns (answer_text, model_used). Raises on failure."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": DEFAULT_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are DoubtSahayak, a study-doubt solver for students "
                    "preparing for GATE. Give a SHORT explanation plus ONE "
                    "worked example. Use the grounding notes given when they "
                    "are relevant. Notes tagged AUTHOR'S DRILL NOTES come "
                    "from the student's own verified study notes — trust "
                    "them over general knowledge. Notes tagged STANDARD "
                    "REFERENCE are textbook material, not the student's own "
                    "notes. If no grounding note covers the doubt, say so in "
                    "one line and answer carefully — never invent a formula. "
                    "Keep the whole answer under 250 words."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 800,
    }
    with _clean_no_proxy(), httpx.Client(timeout=60.0) as client:
        resp = client.post(
            f"{BHARATCODE_BASE}/chat/completions", json=payload, headers=headers
        )
        if resp.status_code in (400, 404) and DEFAULT_MODEL != FALLBACK_MODEL:
            payload["model"] = FALLBACK_MODEL
            resp = client.post(
                f"{BHARATCODE_BASE}/chat/completions", json=payload, headers=headers
            )
        resp.raise_for_status()
        data = resp.json()
        model_used = data.get("model") or payload["model"]
        return data["choices"][0]["message"]["content"].strip(), model_used


def _call_adaption(prompt: str, api_key: str, model: str) -> tuple[str, str]:
    """One chat-completions call to the Adaption-tuned model, served via
    Together AI's OpenAI-compatible inference endpoint (Adaption trains on
    Together infrastructure). Returns (answer_text, model_used). Raises on
    failure — the caller falls back to BharatCode."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are DoubtSahayak, a study-doubt solver for students "
                    "preparing for GATE. You were fine-tuned on a curated "
                    "GATE knowledge base (3,100+ notes across all 30 GATE "
                    "papers + General Aptitude, plus real previous-year "
                    "questions). Give a SHORT explanation plus ONE worked "
                    "example. Use the grounding notes given when they are "
                    "relevant. Notes tagged AUTHOR'S DRILL NOTES come from "
                    "the student's own verified study notes — trust them "
                    "over general knowledge. Notes tagged STANDARD REFERENCE "
                    "are textbook material, not the student's own notes. If "
                    "no grounding note covers the doubt, say so in one line "
                    "and answer carefully — never invent a formula. Keep the "
                    "whole answer under 250 words."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 800,
    }
    with _clean_no_proxy(), httpx.Client(timeout=60.0) as client:
        resp = client.post(
            f"{ADAPTION_BASE_URL}/chat/completions", json=payload, headers=headers
        )
        resp.raise_for_status()
        data = resp.json()
        model_used = data.get("model") or model
        return data["choices"][0]["message"]["content"].strip(), model_used


def _grounding_warning(gsource: str) -> str | None:
    if gsource == "drill-notes":
        return None
    if gsource == "reference":
        return ("Grounded in standard reference material — not your own "
                "drill notes. Verify this answer against your notes.")
    if gsource == "mixed":
        return ("Grounded in your drill notes and standard reference "
                "material — the reference parts need verification.")
    return ("No grounding note covered this doubt — "
            "this answer is LLM-only, please verify it against your notes.")


def solve(question: str, language: str = "English", subject: str = "Probability & Stats",
          paper: str = "DA", engine: str = "bharatcode") -> dict:
    question = (question or "").strip()
    if not question:
        raise ValueError("Question is empty.")
    if len(question) > 2000:
        raise ValueError("Question is too long (max 2000 characters).")
    if paper not in PAPERS:
        paper = "DA"
    if subject not in PAPERS[paper]["subjects"]:
        subject = PAPERS[paper]["subjects"][0]
    if language not in LANGUAGE_INSTRUCTIONS:
        language = "English"

    notes = retrieve(question, subject, paper)
    grounded = bool(notes)
    gsource = grounding_source(notes)
    lang_note = LANGUAGE_INSTRUCTIONS[language]
    if engine not in ("bharatcode", "adaption"):
        engine = "bharatcode"

    if notes:
        prompt = (
            f"GATE paper {paper}, subject: {subject}. {lang_note}\n\n"
            f"Student doubt: {question}\n\n"
            f"Grounding notes (trust the ones tagged AUTHOR'S DRILL NOTES "
            f"over general knowledge):\n{_notes_text(notes)}\n\n"
            f"Answer the doubt with a short explanation and one worked example."
        )
    else:
        prompt = (
            f"GATE paper {paper}, subject: {subject}. {lang_note}\n\n"
            f"Student doubt: {question}\n\n"
            f"No grounding note covers this doubt. "
            f"Say that in one line, then answer carefully with a short "
            f"explanation and one worked example."
        )

    # Adaption engine (only when requested): try the tuned model first.
    # Any problem — not configured, or the call fails — falls through to
    # the BharatCode path below, and the warning says so. The returned
    # mode always reports what actually answered.
    adaption_note = None
    if engine == "adaption":
        adaption_key = os.environ.get("ADAPTION_API_KEY", "").strip()
        adaption_model = os.environ.get("ADAPTION_MODEL", "").strip()
        if not adaption_key or not adaption_model:
            adaption_note = (
                "Adaption-tuned model is not deployed yet (ADAPTION_API_KEY "
                "/ ADAPTION_MODEL are not set), so this answer came from the "
                "BharatCode model instead."
            )
        else:
            try:
                answer, model_used = _call_adaption(
                    prompt, adaption_key, adaption_model
                )
                return {
                    "answer": answer,
                    "mode": "adaption",
                    "model": model_used,
                    "grounded": grounded,
                    "grounding_source": gsource,
                    "paper": paper,
                    "notes": notes,
                    "warning": _grounding_warning(gsource),
                }
            except Exception as exc:  # noqa: BLE001 — fall back, don't crash
                adaption_note = (
                    f"Adaption model call failed ({exc}); fell back to the "
                    "BharatCode model."
                )

    api_key = os.environ.get("BHARATCODE_API_KEY", "").strip()
    if not api_key:
        warning = (
            "No BHARATCODE_API_KEY is set, so this answer came only from "
            "the knowledge base — no LLM was called."
            if grounded else
            "No BHARATCODE_API_KEY is set and no grounding note covers "
            "this doubt. Set the free student API key to get a full answer."
        )
        if adaption_note:
            warning = f"{adaption_note} {warning}"
        if grounded and gsource in ("reference", "mixed"):
            warning += (" These notes are standard reference material, not "
                        "your own drill notes — verify them against your notes.")
        return {
            "answer": _offline_answer(question, notes, language),
            "mode": "offline-kb",
            "model": None,
            "grounded": grounded,
            "grounding_source": gsource,
            "paper": paper,
            "notes": notes,
            "warning": warning,
        }

    try:
        answer, model_used = _call_bharatcode(prompt, api_key)
    except httpx.HTTPStatusError as exc:
        warning = (
            f"BharatCode API call failed (HTTP {exc.response.status_code}). "
            "Showing the offline KB answer instead — check the API key and "
            "try again."
        )
        if adaption_note:
            warning = f"{adaption_note} {warning}"
        return {
            "answer": _offline_answer(question, notes, language),
            "mode": "error-fallback-kb",
            "model": None,
            "grounded": grounded,
            "grounding_source": gsource,
            "paper": paper,
            "notes": notes,
            "warning": warning,
        }
    except Exception as exc:  # network down, timeout, bad JSON, ...
        warning = (f"BharatCode API call failed ({exc}). Showing the "
                   "offline KB answer instead.")
        if adaption_note:
            warning = f"{adaption_note} {warning}"
        return {
            "answer": _offline_answer(question, notes, language),
            "mode": "error-fallback-kb",
            "model": None,
            "grounded": grounded,
            "grounding_source": gsource,
            "paper": paper,
            "notes": notes,
            "warning": warning,
        }

    warning = _grounding_warning(gsource)
    if adaption_note:
        warning = f"{adaption_note} {warning or ''}".strip()
    return {
        "answer": answer,
        "mode": "bharatcode",
        "model": model_used,
        "grounded": grounded,
        "grounding_source": gsource,
        "paper": paper,
        "notes": notes,
        "warning": warning,
    }


EXAMPLES = [
    {
        "language": "English",
        "paper": "DA",
        "subject": "Probability & Stats",
        "question": "X ~ Binomial(12, 1/3). Find E[X], Var(X), and the most probable value of X.",
    },
    {
        "language": "Telugu",
        "paper": "DA",
        "subject": "Probability & Stats",
        "question": "Normal distribution lo Z-score ante enti? X ~ N(10, 4) aithe P(X > 12) ela find chestaru?",
    },
    {
        "language": "Hindi",
        "paper": "DA",
        "subject": "Probability & Stats",
        "question": "Mean, median aur mode mein kya antar hai? Data 7, 3, 9, 3, 12, 5 ka mean, median aur mode nikalo.",
    },
    {
        "language": "English",
        "paper": "DA",
        "subject": "Linear Algebra",
        "question": "Find the eigenvalues of the matrix [[2, 1], [1, 2]].",
    },
    {
        "language": "English",
        "paper": "DA",
        "subject": "Database Management & Warehousing",
        "question": "What is 3NF, and how is it different from BCNF?",
    },
    {
        "language": "English",
        "paper": "DA",
        "subject": "Machine Learning",
        "question": "What is the bias-variance tradeoff? Why can't we minimise both at once?",
    },
    {
        "language": "English",
        "paper": "DA",
        "subject": "Artificial Intelligence",
        "question": "How does A* search work, and when is it guaranteed to find the optimal path?",
    },
    {
        "language": "English",
        "paper": "ME",
        "subject": "Thermodynamics",
        "question": "A Carnot engine works between 600 K and 300 K. What is its maximum efficiency?",
    },
    {
        "language": "English",
        "paper": "CS",
        "subject": "Algorithms",
        "question": "What is the worst-case time complexity of quicksort, and when does it happen?",
    },
]
