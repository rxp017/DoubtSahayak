# DoubtSahayak — BharatCode Build League

A multilingual GATE doubt solver for all 30 GATE papers + General
Aptitude. Paste a doubt in **Telugu, Hindi or English**, pick a paper and
subject, and get a short explanation + one worked example — **grounded in
a knowledge base of 875 entries**, not a bare chat wrapper.

- **Frontend:** React (Vite), single-page UI with a GATE paper selector,
  language + subject selectors, formula sheet, quiz mode and doubt history.
- **Backend:** FastAPI (`backend/app.py`), core logic in `backend/solver.py`.
- **Grounding KB:** `backend/kb.json` — **875 entries** (631 full notes with
  worked examples, 244 concise notes):
  - **24 entries from the author's own GATE DA drill packs** (8 packs, Nov
    2026), labelled "Your GATE DA notes" in the UI. These are the only
    entries that are the author's own notes. The MGF/LLN/CLT drill pack was
    deliberately excluded — its topic was never verified.
  - **851 standard reference entries**, researched from public sources
    against the **official GATE 2026 syllabi** (IIT Guwahati,
    gate2026.iitr.ac.in — note: GATE 2026 is run by IIT Guwahati, and the
    official 30th paper is TF Textile, not RA; see "Coverage honesty"
    below). Labelled "Standard reference" in the UI.
- **LLM:** BharatCode API, OpenAI-compatible chat completions
  (`https://bharatcode.ai/api/model/v1`), default model `qwen-3.8-27b`,
  fallback `deepseek-v4.1-flash`. Key comes from the `BHARATCODE_API_KEY`
  env var only — never hardcoded, never committed.

## Coverage honesty (read this before trusting a number)

- The KB covers the **full official GATE 2026 syllabus topic list** for
  all 30 papers in the app (AE, AG, AR, BM, BT, CE, CH, CS, CY, DA, EC,
  EE, ES, EY, GE, GG, IN, MA, ME, MN, MT, NM, PE, PH, PI, RA, ST, XE, XH,
  XL) plus General Aptitude (GA, the common 15-mark section).
- **Depth varies honestly:** core/high-weightage topics have full notes
  with worked examples; narrower topics have concise notes. Each entry
  carries a `depth` field ("full" / "concise") and the formula sheet shows
  it. This is **not** the full GATE syllabus in depth and **not**
  exam-complete.
- **Known gaps (deliberately left out rather than padded):** a small number
  of fine-grained syllabus sub-items have no entry — e.g. ME turbomachinery
  velocity diagrams, cams/gyroscopes, machine-design elements detail; MA
  abstract algebra / functional analysis / topology; PH solid-state and
  nuclear physics; ST calculus/matrix-theory background sections; XH
  international/public economics detail; XE polymer processing and ocean
  sciences detail. The full list of leftovers is in each gap batch's notes;
  they are real syllabus items and the natural next batch.
- **RA is not an official GATE 2026 paper** — the official 30th paper is
  TF (Textile Engineering & Fibre Science), which has no entries here
  because it was not in the requested list. RA entries follow a standard
  robotics & automation syllabus instead.
- DA is the deepest paper (112 entries, incl. the 24 drill-notes entries);
  other papers have 18–56 entries each. Per-paper counts:
  AE 23, AG 18, AR 18, BM 33, BT 18, CE 28, CH 30, CS 56, CY 19, DA 112,
  EC 33, EE 34, ES 18, EY 18, GA 9, GE 21, GG 23, IN 33, MA 35, ME 36,
  MN 20, MT 22, NM 20, PE 22, PH 38, PI 29, RA 20, ST 31, XE 22, XH 18,
  XL 18. Total 875.

## Features

1. **Ask a doubt** — pick a GATE paper, subject and language (Telugu /
   Hindi / English); get a short explanation + one worked example. Answers
   are labelled by grounding: "From your GATE DA notes", "Standard
   reference — verify against your notes", or "No grounding note — verify
   this answer".
2. **Formula sheet** — every KB formula for the selected paper, grouped by
   subject, with source ("Your notes" / "Reference") and depth ("In depth"
   / "Concise") badges.
3. **Quiz mode** — 5 multiple-choice questions per paper/subject, built
   from KB entries (match a formula to its topic, or a topic to its
   formula), instant feedback, score at the end. If a subject has fewer
   than 4 notes, the quiz draws from the whole paper and says so.
4. **Doubt history** — the last 20 doubts, saved in the browser's
   localStorage; click one to ask it again.

## How it answers

1. Keyword retrieval pulls the top 3 KB entries for the chosen paper +
   subject.
2. If a key is set, the LLM is called with those notes as grounding and
   instructed to answer in the chosen language, under 250 words. Notes
   from the author's drill packs are tagged as such in the prompt; reference
   notes are tagged as standard reference material.
3. If no key is set, the app answers **offline from the KB only** and says
   so — it never pretends a live LLM call happened. If the API call fails,
   it falls back to the KB answer with a visible warning.
4. Answers grounded only in reference entries carry a "verify against your
   notes" warning; answers with no grounding note carry an "LLM-only"
   warning.

## Run locally

```bash
# 1. Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env   # then put your key in ../.env (optional — offline KB works without it)
uvicorn app:app --reload --port 8000

# 2. Frontend (new terminal, from the project root)
npm install
npm run dev        # http://localhost:5173 — /api is proxied to localhost:8000
```

Try the example doubts (English Binomial, Telugu Normal, Hindi
mean/median/mode, Linear Algebra eigenvalues, 3NF vs BCNF, bias–variance,
A*, Carnot, quicksort) — they all have KB coverage, so even the offline
mode gives a real answer.

## API

- `GET /api/papers` — all papers with subjects and entry counts.
- `GET /api/kb` — full KB grouped by paper, then subject (+ summary).
- `GET /api/quiz?paper=ME&subject=Thermodynamics&n=5&seed=42` — MCQ quiz.
- `POST /api/ask` — `{question, language, subject, paper}` → answer.
- `GET /api/subjects`, `GET /api/examples`, `GET /health`.

## Deploy free (Vercel)

1. Push this folder as a **public** GitHub repo (see "Submit" below).
2. In Vercel: **Add New Project → import the repo**. Framework: Vite.
   Build command `npm run build`, output directory `dist`.
3. Set the environment variable **`BHARATCODE_API_KEY`** in the Vercel
   project settings (never in code). The frontend calls `/api/ask`, served
   by the serverless function `api/ask.py`; `/api/kb`, `/api/quiz` and
   `/api/papers` have matching serverless functions.
4. Deploy. No payment needed — Vercel Hobby is free.

> `api/*.py` are written for Vercel's Python runtime but have **not** been
> tested on a live Vercel deployment yet (no Vercel account was used during
> the build). If the serverless path gives trouble, the fallback is:
> frontend on Vercel + backend on a free Render web service
> (`uvicorn app:app --host 0.0.0.0 --port $PORT` from `backend/`), then
> set `VITE_API_URL` to the Render URL and redeploy the frontend.

## Demo script (2 minutes)

See [DEMO.md](DEMO.md).

## Submit (BharatCode Build League — deadline Tue 10 Nov 2026, 11:59 PM IST)

1. Register at https://bharatcode.ai/hackathon (your step — sign-in).
2. Create a **public** GitHub repo, push this folder, and make sure
   `BharatCode.txt` is in the repo root (it is — required for submission).
3. Get your free student API key from BharatCode (`.ac.in` email; if it asks
   for payment, stop — do not pay).
4. Deploy on Vercel (above) and add the live URL to the repo README.
5. Submit the repo link on the hackathon page before **Tue 10 Nov 2026,
   11:59 PM IST**.

Prize: ₹10,000 first prize; the winner also gets an interview for a paid
SDE internship at ₹60,000/month × 3 months. That ₹60k is the winner's
prize, not a guaranteed stipend. Judging: GitHub stars + website votes +
judges.

## Project structure

```
doubtsahayak/
├── BharatCode.txt          # required for submission — keep in repo root
├── README.md  DEMO.md  .env.example  vercel.json
├── package.json  vite.config.js  index.html
├── src/                    # React frontend (App.jsx, App.css, main.jsx)
├── backend/
│   ├── app.py              # FastAPI server (local dev)
│   ├── solver.py           # retrieval + BharatCode call + offline fallback + quiz
│   ├── kb.json             # 875 grounded KB entries (24 drill-notes + 851 reference)
│   └── requirements.txt
└── api/
    ├── ask.py              # Vercel serverless function (same solver)
    ├── kb.py               # Vercel serverless: formula sheet data
    ├── quiz.py             # Vercel serverless: quiz generation
    └── papers.py           # Vercel serverless: paper list
```

## What is NOT done / not verified

- **No live BharatCode call has been made** — the API key exists but the
  free student access was not active at last check (API returned 402
  subscription_required; a community-request form / email to
  contact@bharatcode.ai was pending the user's choice). The live path is
  code-complete but untested until the key works.
- **Not deployed** — no Vercel project, no live URL yet.
- **Not on GitHub** — no repo created, nothing pushed (user's step).
- **Not registered** — the hackathon registration is the user's step
  (account created 9 Nov 2026; Build League spot saved).
- **KB coverage is broad, not exam-complete** — see "Coverage honesty"
  above for the known gaps.
- **Vercel serverless functions untested on live Vercel** — local FastAPI
  backend is the verified path.
