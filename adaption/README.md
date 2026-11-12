# Adaption — model training for DoubtSahayak

DoubtSahayak's second answer engine: a model fine-tuned on the GATE
knowledge base via [Adaption Labs](https://adaptionlabs.ai) (AutoScientist).
Added 12 Nov 2026, **after** the BharatCode Build League submission
deadline (10 Nov 2026, 11:59 PM IST) — this integration is an
after-submission improvement, not part of the submitted entry.

## Status (honest, as of 12 Nov 2026, ~09:00 IST)

- **Training dataset: DONE** — 3,112 examples, ready to upload
  (`training-data.csv` for Adaption's raw upload, `training-data.jsonl`
  with full metadata).
- **Training run: NOT STARTED — blocked.** There is no Adaption account
  or API key for the owner yet. Claiming the 1,000 free Build League
  credits needs the owner to create an Adaption account (sign-up on
  adaptionlabs.ai with his email/Google) and create an API key. No
  BharatCode-specific claim link or code was found anywhere — plain
  sign-up. No model has been trained, no job ID exists, no credits used.
  Nothing here is faked: the app code below is real and tested, but the
  tuned model itself does not exist yet.
- **App integration: DONE (code), UNVERIFIED live.** The Adaption engine
  is wired into `backend/solver.py`, `api/ask.py`, `backend/app.py` and
  the frontend toggle. It has been tested for its fallback behaviour
  (no key → falls back to BharatCode and says so). A live call to the
  tuned model can only be tested after the owner trains and deploys it.

## What to do next (owner only — needs his sign-in)

1. Create an account at https://adaptionlabs.ai (sign up with
   24e51a6645@hitam.org or Google). The Build League gives every
   participant 1,000 free Adaption credits — check the account/credits
   page to confirm they are there before training.
2. In Settings → API keys, create an API key (shown once only — copy it).
3. Install the SDK and run the training script from the repo root:
   ```
   pip install "adaption>=0.7.0"
   ADAPTION_API_KEY=<key> python3 adaption/train.py
   ```
   It uploads `training-data.csv`, starts an AutoScientist run, waits for
   completion, prints the job ID / base model / best win rate, and
   downloads the best checkpoint to `adaption/best-checkpoint.tgz`.
   It records everything in `adaption/training-run.json`.
4. Deploy the checkpoint for inference. Adaption trains on Together AI
   infrastructure; a fine-tuned model is served from Together's
   OpenAI-compatible inference endpoint
   (`https://api-inference.together.ai/v1`) as a dedicated endpoint.
   **Cost warning:** training is covered by the free credits, but a
   Together dedicated endpoint bills per GPU-hour. Check the
   Adaption/Together dashboard for the cost before deploying, and do
   not pay anything without the owner's word.
5. Set these Vercel environment variables (never in code):
   - `ADAPTION_API_KEY` — the Together/Adaption inference key
   - `ADAPTION_MODEL` — the deployed model/endpoint string, e.g.
     `your-project-slug/doubtsahayak-gate-tuned`
   - `ADAPTION_BASE_URL` — optional, defaults to
     `https://api-inference.together.ai/v1`
6. Redeploy. Pick "Adaption-tuned" in the app's Answer engine toggle
   and ask a GATE question — the badge will read
   "Live · Adaption-tuned model" with the model name.

## How the app uses it

- `backend/solver.py`: `solve(..., engine="adaption")` calls
  `_call_adaption()` (Together-compatible `/chat/completions` with the
  fine-tuned model). If the key/model is not set, or the call fails, it
  falls back to the BharatCode Qwen path and then to the offline KB —
  and the `warning` field says exactly what happened. The `mode` field
  in the response always reports what actually answered:
  `adaption` | `bharatcode` | `offline-kb` | `error-fallback-kb`.
- `api/ask.py` and `backend/app.py` accept an `engine` field
  (`bharatcode` default, `adaption`).
- `src/App.jsx`: an "Answer engine" toggle (BharatCode Qwen /
  Adaption-tuned) next to the language selector, and a violet
  "Live · Adaption-tuned model" badge showing the model name.
  Existing features are untouched: 31-paper selector, 4 tabs,
  language/subject selectors, badges, quiz, history.

## The training dataset

Built by `adaption/build_dataset.py` from `backend/kb.json` (933 entries)
plus verified web-sourced previous-year questions. Rebuild any time with:

```
python3 adaption/build_dataset.py
```

| Origin | Count | What it is |
|---|---|---|
| `kb-entry` | 2,732 | Q&A variants derived strictly from real KB entries (concept / worked example / formula / application angles — different questions, not duplicates) |
| `web-pyq` | 32 | Real GATE previous-year questions with worked solutions, from EduRev (`edurev.in/t/373110/...`), GetMyUni and the official GATE 2026 AR paper with solutions (Zollege). Each carries its `source_url`. One (paper-folding, GATE 2024 Set 1) was corrected against the source's own answer key during verification — the long edge changes after each fold, so the answer is 18 cm, not 21. |
| `kb-entry-lang-variant` | 348 | Telugu/Hindi question variants of real KB entries (code-mixed, as students actually ask). The response is the same verified worked solution — formulas and worked numbers are language-independent. The app's inference-time language instruction renders answers in the user's language. |
| **Total** | **3,112** | |

### Per-paper counts (training examples, NOT KB entries)

The knowledge base itself is still 933 entries. The 100-per-paper target
is met in the **training dataset**: every paper has ≥100 examples.

AE 100, AG 100, AR 100, BM 100, BT 100, CE 100, CH 100, CS 100, CY 100,
DA 112, EC 100, EE 100, ES 100, EY 100, GA 100, GE 100, GG 100, IN 100,
MA 100, ME 100, MN 100, MT 100, NM 100, PE 100, PH 100, PI 100, RA 100,
ST 100, XE 100, XH 100, XL 100. Total 3,112.

Language split: English 2,764 · Telugu 259 · Hindi 89.
Variant split: concept 933 · worked 807 · formula 654 · application 338 ·
PYQ 32 · Telugu worked 250 · Hindi worked 80 · Telugu concept 9 ·
Hindi concept 9. Zero duplicate instructions.

### Honesty rules the dataset was built under

- Every example comes from a real KB entry or a real sourced note.
  Nothing was invented — no formulas, facts or worked examples were
  made up. If a source could not be verified, it was left out.
- Web PYQs are labelled `source: "reference"` (standard public material,
  NOT the author's own drill notes), each with its source URL.
- DA has 112 examples (concept variant for all 112 KB entries — full
  topic coverage); every other paper is capped at 100.
- The dataset is English-first (the KB is English); Telugu/Hindi
  coverage is question-side only, as documented above.

## Files

- `build_dataset.py` — builds `training-data.jsonl` + `training-data.csv`
  from `backend/kb.json` + `web_examples.json`
- `web_examples.json` — the 32 verified web-sourced PYQs with source URLs
- `training-data.jsonl` — full dataset with metadata (paper, subject,
  topic, kb_id, source, language, variant, origin, source_url)
- `training-data.csv` — `instruction,response` only, for Adaption's raw upload
- `train.py` — uploads the CSV and runs AutoScientist (needs
  `ADAPTION_API_KEY`; exits with a clear message without it)
- `training-run.json` — written by `train.py` when a run completes
  (does not exist yet — no run has happened)
