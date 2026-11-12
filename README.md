# DoubtSahayak — BharatCode Build League

A multilingual GATE doubt solver for all 30 GATE papers + General
Aptitude. Paste a doubt in **Telugu, Hindi or English**, pick a paper and
subject, and get a short explanation + one worked example — **grounded in
a knowledge base of 933 entries**, not a bare chat wrapper.

- **Frontend:** React (Vite), single-page UI with a GATE paper selector,
  language + subject selectors, formula sheet, quiz mode and doubt history.
- **Backend:** FastAPI (`backend/app.py`), core logic in `backend/solver.py`.
- **Grounding KB:** `backend/kb.json` — **933 entries** (659 full notes with
  worked examples, 274 concise notes):
  - **24 entries from the author's own GATE DA drill packs** (8 packs, Nov
    2026), labelled "Your GATE DA notes" in the UI. These are the only
    entries that are the author's own notes. The MGF/LLN/CLT drill pack was
    deliberately excluded — its topic was never verified.
  - **909 standard reference entries**, researched from public sources
    against the **official GATE 2027 syllabi** (IIT Madras,
    gate2027.iitm.ac.in). RA (Robotics & Automation) is a new GATE 2027
    paper; TF (Textile Engineering & Fibre Science) is no longer a
    standalone paper in 2027 — its topics live under XE section 9. Labelled
    "Standard reference" in the UI.
- **LLM:** BharatCode API, OpenAI-compatible chat completions
  (`https://bharatcode.ai/api/model/v1`), default model `qwen-3.8-27b`,
  fallback `deepseek-v4.1-flash`. Key comes from the `BHARATCODE_API_KEY`
  env var only — never hardcoded, never committed.

## Coverage honesty (read this before trusting a number)

- The KB covers the **full official GATE 2027 syllabus topic list** for
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
- **RA is a new GATE 2027 paper** (Robotics & Automation) — its entries
  follow the official GATE 2027 RA syllabus (Part A + optional Part B1
  Electrical / B2 Mechanical). **TF is not a standalone
  GATE 2027 paper** — from 2027, Textile Engineering & Fibre Science
  topics are XE section 9, and the KB covers them under XE ("XE9 Textile
  Engineering & Fibre Science", 14 entries across XE9.1–XE9.5).
- **GATE 2027 reconciliation (9 Nov 2026):** the KB was reconciled entry
  by entry against the official GATE 2027 syllabus PDFs (IIT Madras).
  DA and EE are **unchanged** vs 2026 (DA verified by reading the official
  DA PDF). CS, ME, EC and CE were **revised**: CS gained Karnaugh-map /
  Quine-McCluskey minimisation and dropped ARP, DHCP, ICMP, SMTP, FTP and
  secondary-storage/magnetic-disk entries (NAT/CIDR/fragmentation and
  DNS/HTTP/socket-API kept); ME gained 14 entries (2-DOF vibration,
  damping estimation, transmissibility, PID/transfer function, compressible
  flow and nozzles, velocity potential, boiling/condensation, pump
  characteristics, additive manufacturing, non-traditional machining,
  solid-state welding, NDT, powder metallurgy, ASA/ORS tool geometry,
  Six Sigma/Lean, air-fuel ratio) and dropped Heisler charts; EC gained
  correlation/regression, FIR/IIR filter design, MOSFET scaling, Miller
  compensation/phase margin, PID control and source coding; CE gained a
  standalone Section 8 (Construction Materials and Management), virtual
  work/Castigliano, sheet piles, ground improvement, streamflow
  measurement, weirs/river training, earthen dams, tertiary wastewater
  treatment, GNSS/geodetic/digital photogrammetry and well irrigation; the
  KB's plate-girder, flexibility-method and sampling-theorem content was
  removed, and prestressed concrete (listed as removed in 2027) was never
  in the KB. RA gained 13 entries for the official Part A.2/B1/B2
  topics (network theorems, op-amps, transforms, transfer functions/Bode,
  PID, Mohr's circle, torsion/bending, Euler buckling, gear trains, SDOF
  vibration, fatigue/S-N, homogeneous transforms, Python data structures).
- DA is the deepest paper (112 entries, incl. the 24 drill-notes entries);
  other papers have 18–57 entries each. Per-paper counts:
  AE 23, AG 18, AR 18, BM 33, BT 18, CE 38, CH 30, CS 57, CY 19, DA 112,
  EC 39, EE 34, ES 18, EY 18, GA 9, GE 21, GG 23, IN 33, MA 35, ME 50,
  MN 20, MT 22, NM 20, PE 22, PH 38, PI 29, RA 33, ST 31, XE 36, XH 18,
  XL 18. Total 933.

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

## Model training with Adaption

Added 12 Nov 2026 — **after** the Build League submission deadline
(10 Nov 2026, 11:59 PM IST), so this is an after-submission improvement,
not part of the submitted entry. Full detail: [`adaption/README.md`](adaption/README.md).

- **What was trained:** a model **was trained on 12 Nov 2026** with
  Adaption AutoScientist on the 3,112-example dataset (free credits
  only — no money spent). Training run
  `206fe3ca-f5ae-448e-8d9e-e15ca80b0290`, dataset
  `a0ec07b9-fc0d-4e08-8f2c-064c20a854f9`, base model
  `google/gemma-3-4b-pt`, best win rate **0.545**, status **succeeded**.
  Best checkpoint downloaded to `adaption/best-checkpoint.tgz`
  (local only, not in the repo). Full record:
  `adaption/training-run.json`. The model is trained but **not yet
  deployed for inference** — the app's Adaption mode still falls back
  to BharatCode Qwen until the checkpoint is deployed (Together
  dedicated endpoint, billed per GPU-hour — deployment needs the
  owner's word first).
- **Dataset:** 3,112 examples in `adaption/training-data.csv` (+ JSONL
  with metadata), built by `adaption/build_dataset.py` from the 933 KB
  entries plus 32 verified web-sourced GATE previous-year questions
  (EduRev, GetMyUni, official GATE 2026 AR paper) and 348 Telugu/Hindi
  question variants of real KB entries. **Every paper has ≥100 training
  examples** (DA 112, all others 100; GA reached 100 only with the web
  PYQs). The KB itself is still 933 entries — the 100-per-paper target
  is met in the training dataset, not in the KB. Nothing was invented:
  every example comes from a real KB entry or a real sourced note.
- **How the app calls it:** the "Answer engine" toggle in the UI
  (BharatCode Qwen / Adaption-tuned). `POST /api/ask` accepts
  `engine: "adaption"`; `backend/solver.py` calls the tuned model via
  Together AI's OpenAI-compatible inference endpoint
  (`ADAPTION_API_KEY` + `ADAPTION_MODEL` env vars only). If the tuned
  model is not deployed, or its call fails, the app falls back to the
  BharatCode Qwen path and then to the offline KB — and the warning
  says so. The mode badge always reports what actually answered:
  `adaption` | `bharatcode` | `offline-kb` | `error-fallback-kb`.
- **Serving cost warning:** training is covered by the free credits,
  but serving a fine-tuned model on Together needs a dedicated endpoint
  billed per GPU-hour — check the dashboard before deploying and do not
  pay without the owner's word.

### Sample answers (observed 12 Nov 2026)

Question: "A Carnot engine works between 600 K and 300 K. What is its
maximum efficiency?" (ME, Thermodynamics, English)

| Engine | Answer (as observed) |
|---|---|
| BharatCode Qwen (`qwen-3.8-27b`, live) | "For a Carnot engine, the **maximum efficiency** depends only on the reservoir temperatures: η = 1 − Tc/Th … **Worked example:** Given Th = 600 K, Tc = 300 K, η = 1 − 300/600 = 0.5, i.e. 50%." (mode `bharatcode`, grounded, reference warning shown) |
| Adaption-tuned | **Trained, not deployed yet** — the model exists (run `206fe3ca`, `google/gemma-3-4b-pt`, win rate 0.545) but is not serving, so no live Adaption answer can be shown yet. The integration code was verified against a mock Together endpoint (mode `adaption`, model name shown in the badge) and its fallback was verified live: with no Adaption key set, `engine=adaption` fell back to BharatCode Qwen and the warning said so. |

Same fallback verified for quicksort worst-case (CS, Algorithms):
`engine=adaption` → mode `bharatcode`, model `qwen-3.8-27b`,
"Adaption-tuned model is not deployed yet … so this answer came from
the BharatCode model instead."

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
- `POST /api/ask` — `{question, language, subject, paper, engine}` → answer.
  `engine` is `"bharatcode"` (default) or `"adaption"` (Adaption-tuned
  model; falls back to BharatCode when not deployed).
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
├── README.md  DEMO.md  .env.example  vercel.json  requirements.txt  # root requirements.txt: httpx only, for Vercel serverless
├── package.json  vite.config.js  index.html
├── src/                    # React frontend (App.jsx, App.css, main.jsx)
├── adaption/               # Adaption fine-tuning: build_dataset.py, train.py,
│                           # training-data.csv/.jsonl (3,112 examples), README.md
├── backend/
│   ├── app.py              # FastAPI server (local dev)
│   ├── solver.py           # retrieval + BharatCode call + Adaption engine + offline fallback + quiz
│   ├── kb.json             # 933 grounded KB entries (24 drill-notes + 909 reference)
│   └── requirements.txt
└── api/
    ├── ask.py              # Vercel serverless function (same solver)
    ├── kb.py               # Vercel serverless: formula sheet data
    ├── quiz.py             # Vercel serverless: quiz generation
    └── papers.py           # Vercel serverless: paper list
```

## What is NOT done / not verified

- **Live BharatCode call verified** — student access active since
  10 Nov 2026; `/api/ask` answers live in mode `bharatcode`
  (model `qwen-3.8-27b`). Re-verified locally 12 Nov 2026 (Carnot and
  quicksort questions, both grounded, correct answers). The Adaption
  engine is code-complete and fallback-verified, and the model **has
  been trained** (run `206fe3ca`, `google/gemma-3-4b-pt`, win rate
  0.545, 12 Nov 2026) — see "Model training with Adaption" above. It
  is not yet deployed for inference, so the Adaption mode still falls
  back to BharatCode Qwen.
- **On GitHub** — public repo https://github.com/rxp017/DoubtSahayak
  (pushed 9 Nov 2026, main branch). Live at
  https://doubt-sahayak.vercel.app/ (Vercel project created from the repo).
- **Live deploy was broken at last check (9 Nov 2026)** — `/api/ask`
  returned FUNCTION_INVOCATION_FAILED (500) on every call, including GET.
  Diagnosis: `api/ask.py` imports `backend.solver`, which imports `httpx`,
  but Vercel's Python runtime only installs from a `requirements.txt` in
  the project root, and the project had only `backend/requirements.txt` —
  so `httpx` was missing in the serverless environment. Fixed locally the
  same day: project-root `requirements.txt` with `httpx==0.28.1`, plus
  `api/ask.py` now forwards the `paper` field to `solve()` (it was silently
  defaulting every ask to DA). Fix verified locally in a fresh venv with
  only the root requirements installed — **not yet verified on live Vercel;
  needs a redeploy + live check** (parent's step, not done here).
- **Not registered** — the hackathon registration is the user's step
  (account created 9 Nov 2026; Build League spot saved).
- **KB coverage is broad, not exam-complete** — see "Coverage honesty"
  above for the known gaps.
- **Vercel serverless functions tested locally only** — all four handlers
  import and answer correctly in a fresh venv with only the project-root
  `requirements.txt` installed (GET + POST checks pass, see above); live
  Vercel verification still pending after redeploy. Local FastAPI backend
  is the verified path.
