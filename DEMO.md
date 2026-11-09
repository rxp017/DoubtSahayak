# DoubtSahayak — 2-minute demo script

For the hackathon demo video / live pitch. Total: ~2 minutes.

## 0:00–0:15 — The problem (show the landing page)
> "GATE aspirants get stuck on doubts late at night — in Telugu, Hindi
> or English — and a generic chatbot just makes up formulas. DoubtSahayak
> answers from a knowledge base of 875 notes covering all 30 GATE papers
> plus General Aptitude, built against the official GATE 2026 syllabus —
> so the formulas are the ones actually in the syllabus."

## 0:15–0:45 — Ask in English (click the English example)
Click **"English · Binomial"**, then **Solve my doubt**.
> "X ~ Binomial(12, 1/3). The answer comes back with E[X] = 4,
> Var = 8/3, mode 4 — and see the badge: *From your GATE DA notes*.
> Expand 'Grounding notes used' to show the exact note it retrieved."

## 0:45–1:05 — Ask in Telugu (click the Telugu example)
Click **"తెలుగు · Normal distribution"**, then **Solve my doubt**.
> "Same app, same grounding — the answer comes back in Telugu, because the
> doubt was asked in Telugu. The formula stays in standard maths notation."

## 1:05–1:25 — Switch papers (the upgrade)
Change the paper selector to **ME — Mechanical Engineering**, pick the
Carnot example, and ask it.
> "Same app, every GATE paper. ME, CE, CS, EC — 30 papers plus General
> Aptitude, each with its own formula sheet and quiz."

## 1:25–1:45 — Show the honesty (the differentiator)
Open the **Formula sheet** tab for ME, then the **Quiz me** tab and answer
one question.
> "Every formula is labelled: *Your notes* means it came from my own GATE
> DA drill packs; *Reference* means standard textbook material — and
> *In depth* vs *Concise* tells you how deep the note goes. The quiz is
> built from the same notes, with instant feedback. And with no API key at
> all, it still answers from the notes offline — it tells you that too."

## 1:45–2:00 — Stack + close
> "React frontend, FastAPI backend, 875-entry knowledge base from the
> official GATE 2026 syllabus, BharatCode's free student API —
> qwen-3.8-27b, zero cost. DoubtSahayak: ask in your language, get an
> answer you can trust."

## If the live API key is not set on demo day
The offline-KB mode still demos perfectly: the English, Telugu and Carnot
examples above all have KB coverage, so the answers are real even without
a key. Say so on camera — it is a feature, not a failure.

## Honesty note for the pitch
Do not claim the KB is the full GATE syllabus in depth. Say: "full
syllabus topic list; core topics in depth, narrower topics concise."
A small number of fine-grained syllabus sub-items are not covered yet —
see README "Coverage honesty".
