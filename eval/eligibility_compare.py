"""Eligibility accuracy: rule engine vs LLM-only (haathi.md §10.3 exp. 2). LLM-only reads the same scheme
guideline text and the user's message and lists the schemes it thinks apply."""
from __future__ import annotations

import asyncio
import json

from harness import REPORTS, load_items, run, score

from app import llm
from app.corpus import get_corpus

PROMPT = """You are checking eligibility for Indian government schemes. Using only these scheme guidelines:
{docs}

User says: "{q}"
List the scheme_ids the user is clearly eligible for based ONLY on what they said (do not assume unstated facts).
Reply JSON {{"eligible": ["scheme_id", ...]}}."""


async def llm_only(items):
    c = get_corpus()
    docs = "\n\n".join(f"[{s.scheme_id}] " + " ".join(p.text for p in c.docs[s.doc].pages) for s in c.schemes.values())
    out = []
    for it in items:
        data = await llm.complete_json(PROMPT.format(docs=docs[:60000], q=it["question"]))
        out.append(sorted((data or {}).get("eligible", [])) if isinstance(data, dict) else [])
    return out


def f1(g, p):
    g, p = set(g), set(p)
    tp = len(g & p)
    pr = tp / len(p) if p else (1.0 if not g else 0.0)
    rc = tp / len(g) if g else 1.0
    return 0 if pr + rc == 0 else 2 * pr * rc / (pr + rc)


def main() -> None:
    items = [i for i in load_items() if i["gold_eligible"] is not None]
    engine = run(items, {})
    rows = [("Rule engine (Haathi)", score(engine)["eligibility_f1"],
             round(100 * sum(set(r["eligible"]) == set(r["gold_eligible"]) for r in engine) / len(items), 1))]
    if llm.available():
        preds = asyncio.run(llm_only(items))
        rows.append(("LLM-only", round(100 * sum(f1(i["gold_eligible"], p) for i, p in zip(items, preds)) / len(items), 1),
                     round(100 * sum(set(i["gold_eligible"]) == set(p) for i, p in zip(items, preds)) / len(items), 1)))
    else:
        rows.append(("LLM-only", None, None))
    text = ["# Eligibility: rule engine vs LLM-only", "", f"{len(items)} profile questions from SchemeQA-Indic v0.", "",
            "| method | F1 | exact set match |", "|---|---|---|"]
    text += [f"| {n} | {'—' if a is None else a} | {'—' if b is None else b} |" for n, a, b in rows]
    if not llm.available():
        text += ["", "LLM-only row skipped: set `GEMINI_API_KEY` and rerun `make eval`."]
    (REPORTS / "eligibility_compare.md").write_text("\n".join(text) + "\n")
    print("\n".join(text))


if __name__ == "__main__":
    main()
