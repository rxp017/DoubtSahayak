#!/usr/bin/env python3
"""Build the Adaption training dataset for DoubtSahayak from backend/kb.json.

Honest construction rules (see adaption/README.md):
- Every example is derived STRICTLY from one real KB entry's verified
  fact / formula / example. Nothing is invented.
- Four distinct question angles per entry (concept, worked example, formula,
  application). Each angle is a different training signal, not a duplicate:
  different question, different focus. This is the same kind of expansion
  Adaption's own "adapt" step performs on a dataset.
- Per-paper target: ~100 examples. Variant rounds are emitted in order
  (concept -> worked -> formula -> application) until the paper hits the
  target. Papers with >100 entries (DA) keep one example per entry.
- Output: adaption/training-data.jsonl (with metadata) and
  adaption/training-data.csv (instruction,response) for Adaption's raw upload.
"""
import csv
import json
import os
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KB_PATH = os.path.join(ROOT, "backend", "kb.json")
OUT_DIR = os.path.join(ROOT, "adaption")
TARGET_PER_PAPER = 100

# (variant, instruction template, response builder)
def q_concept(e):
    return (
        f"What is {e['topic']}? Explain it briefly. "
        f"[GATE {e['paper']} - {e['subject']}]",
        f"{e['fact']}\n\nFormula: {e['formula']}\n\nWorked example: {e['example']}",
    )

def q_worked(e):
    return (
        f"Give a worked example for {e['topic']} "
        f"[GATE {e['paper']} - {e['subject']}]",
        f"Worked example: {e['example']}\n\nFormula: {e['formula']}\n\n{e['fact']}",
    )

def q_formula(e):
    return (
        f"What is the formula for {e['topic']}? When is it used? "
        f"[GATE {e['paper']} - {e['subject']}]",
        f"Formula: {e['formula']}\n\n{e['fact']}",
    )

def q_application(e):
    return (
        f"Why does {e['topic']} matter in {e['subject']}? Where is it used? "
        f"[GATE {e['paper']}]",
        f"{e['fact']}\n\nFormula: {e['formula']}",
    )

VARIANTS = [
    ("concept", q_concept),
    ("worked", q_worked),
    ("formula", q_formula),
    ("application", q_application),
]

# Telugu / Hindi question variants (final top-up only). The question is asked
# in Telugu/Hindi (code-mixed, as students actually ask), the response is the
# same verified worked solution from the KB entry — formulas and worked
# numbers are language-independent. The app's inference-time language
# instruction renders answers in the user's language; these variants teach
# the model to understand Telugu/Hindi questions about the topic.
def q_worked_te(e):
    return (
        f"{e['topic']} gurinchi oka worked example ivvu. "
        f"[GATE {e['paper']} - {e['subject']}]",
        f"Worked example: {e['example']}\n\nFormula: {e['formula']}\n\n{e['fact']}",
    )

def q_worked_hi(e):
    return (
        f"{e['topic']} par ek worked example dijiye. "
        f"[GATE {e['paper']} - {e['subject']}]",
        f"Worked example: {e['example']}\n\nFormula: {e['formula']}\n\n{e['fact']}",
    )

def q_concept_te(e):
    return (
        f"{e['topic']} ante enti? Vivarinchu. "
        f"[GATE {e['paper']} - {e['subject']}]",
        f"{e['fact']}\n\nFormula: {e['formula']}\n\nWorked example: {e['example']}",
    )

def q_concept_hi(e):
    return (
        f"{e['topic']} kya hai? Samjhaiye. "
        f"[GATE {e['paper']} - {e['subject']}]",
        f"{e['fact']}\n\nFormula: {e['formula']}\n\nWorked example: {e['example']}",
    )

LANG_VARIANTS = [
    ("worked-te", "Telugu", q_worked_te),
    ("worked-hi", "Hindi", q_worked_hi),
    ("concept-te", "Telugu", q_concept_te),
    ("concept-hi", "Hindi", q_concept_hi),
]


def load_web_examples():
    path = os.path.join(OUT_DIR, "web_examples.json")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    with open(KB_PATH, encoding="utf-8") as f:
        kb = json.load(f)
    entries = kb["entries"]

    by_paper = defaultdict(list)
    for e in entries:
        by_paper[e["paper"]].append(e)

    examples = []
    counts = Counter()

    # 1. Web-sourced PYQs first (verified, real exam questions).
    for ex in load_web_examples():
        examples.append(ex)
        counts[ex["paper"]] += 1

    # 2. KB-derived English variants, in order, until the per-paper target.
    for paper in sorted(by_paper):
        paper_entries = by_paper[paper]
        for variant, builder in VARIANTS:
            for e in paper_entries:
                # Oversized papers (DA, 112 entries): emit the concept variant
                # for ALL entries (full topic coverage) instead of cutting at 100.
                if counts[paper] >= TARGET_PER_PAPER and len(paper_entries) <= TARGET_PER_PAPER:
                    break
                if len(paper_entries) > TARGET_PER_PAPER and variant != "concept":
                    break
                instruction, response = builder(e)
                examples.append({
                    "instruction": instruction,
                    "response": response,
                    "paper": paper,
                    "subject": e["subject"],
                    "topic": e["topic"],
                    "kb_id": e["id"],
                    "source": e["source"],
                    "language": "English",
                    "variant": variant,
                    "origin": "kb-entry",
                })
                counts[paper] += 1
            if counts[paper] >= TARGET_PER_PAPER:
                break

    # 3. Telugu/Hindi question variants to top up papers still below target.
    for paper in sorted(by_paper):
        paper_entries = by_paper[paper]
        for variant, language, builder in LANG_VARIANTS:
            for e in paper_entries:
                if counts[paper] >= TARGET_PER_PAPER:
                    break
                instruction, response = builder(e)
                examples.append({
                    "instruction": instruction,
                    "response": response,
                    "paper": paper,
                    "subject": e["subject"],
                    "topic": e["topic"],
                    "kb_id": e["id"],
                    "source": e["source"],
                    "language": language,
                    "variant": variant,
                    "origin": "kb-entry-lang-variant",
                })
                counts[paper] += 1
            if counts[paper] >= TARGET_PER_PAPER:
                break

    os.makedirs(OUT_DIR, exist_ok=True)
    jsonl_path = os.path.join(OUT_DIR, "training-data.jsonl")
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    csv_path = os.path.join(OUT_DIR, "training-data.csv")
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["instruction", "response"])
        for ex in examples:
            w.writerow([ex["instruction"], ex["response"]])

    var_counts = Counter(ex["variant"] for ex in examples)
    origin_counts = Counter(ex["origin"] for ex in examples)
    lang_counts = Counter(ex["language"] for ex in examples)
    print(f"total examples: {len(examples)}")
    print("per paper:", dict(sorted(counts.items())))
    print("per variant:", dict(var_counts))
    print("per origin:", dict(origin_counts))
    print("per language:", dict(lang_counts))
    print("papers at >=100:", sum(1 for c in counts.values() if c >= 100), "/", len(counts))
    print("wrote:", jsonl_path)
    print("wrote:", csv_path)


if __name__ == "__main__":
    main()
