"""Run SchemeQA-Indic with the current configuration and print/save scores (overall and per language)."""
from __future__ import annotations

import json
import sys
from datetime import date

from harness import REPORTS, load_items, md_table, run, score

from app import llm
from app.services import services


def main(overrides: dict | None = None) -> dict:
    items = load_items()
    results = run(items, overrides or {})
    overall = score(results)
    per_lang = {lang: score([r for r in results if r["language"] == lang]) for lang in ("en", "hi", "te")}
    judged = [r["judge_correct"] for r in results if r.get("judge_correct") is not None]
    if judged:
        overall["llm_judge_correct"] = round(100 * sum(judged) / len(judged), 1)
    r = services().retriever()
    engine = {"embedder": r.embedder.name, "reranker": getattr(r.reranker, "name", "off"), "llm": llm.available()}
    cols = ["config", "n", "recall@5", "mrr", "correctness", "eligibility_f1", "abstain_recall", "false_abstain", "faithfulness", "p50_ms", "p95_ms"]
    rows = [{"config": "all", **overall}] + [{"config": k, **v} for k, v in per_lang.items()]
    report = (f"# SchemeQA-Indic results ({date.today()})\n\nEngine: `{json.dumps(engine)}` · items: {len(items)} "
              f"(benchmark v0, author-draft — needs human verification)\n\n" + md_table(rows, cols)
              + "\n\nFailures:\n\n" + "".join(
                  f"- `{x['id']}` ({x['type']}): {x['text'][:140].replace(chr(10), ' ')!r}\n"
                  for x in results if (x['must'] and not all(m.lower() in x['text'].lower() for m in x['must']))
                  or (x['gold_eligible'] is not None and set(x['gold_eligible']) != set(x['eligible']))
                  or (not x['answerable'] and not x['abstained'])))
    (REPORTS / "baseline.md").write_text(report, encoding="utf-8")
    (REPORTS / "baseline_results.jsonl").write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in results), encoding="utf-8")
    print(report)
    return overall


if __name__ == "__main__":
    ov = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
    main(ov)
