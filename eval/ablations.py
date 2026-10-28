"""Ablation table (haathi.md §10.3 exp. 1 + 3): each technique added in order, plus cross-lingual A/B/C."""
from __future__ import annotations

from datetime import date

from harness import REPORTS, load_items, md_table, run, score

from app import llm
from app.services import services

NAIVE = {"retrieval": "dense", "use_rerank": False, "contextual": False, "chunking": "fixed", "corrective": False,
         "verify": False, "crosslingual": "A"}
STEPS = [
    ("naive RAG (dense, fixed chunks)", {}),
    ("+ hybrid (BM25 + dense + sparse, RRF)", {"retrieval": "hybrid"}),
    ("+ reranker", {"use_rerank": True}),
    ("+ Contextual Retrieval", {"contextual": True}),
    ("+ structure-aware chunking", {"chunking": "structure"}),
    ("+ cross-lingual C (orig + English)", {"crosslingual": "C"}),
    ("+ corrective loop", {"corrective": True}),
    ("+ citation verifier", {"verify": True}),
]
COLS = ["config", "recall@5", "mrr", "correctness", "eligibility_f1", "abstain_recall", "false_abstain", "faithfulness", "p50_ms"]


def main() -> None:
    items = load_items()
    rows, cfg = [], dict(NAIVE)
    for name, delta in STEPS:
        cfg.update(delta)
        s = score(run(items, dict(cfg)))
        rows.append({"config": name, **s})
        print(name, s)
    full = dict(cfg)
    xl = []
    for strat in ("A", "B", "C"):
        res = run(items, {**full, "crosslingual": strat})
        for lang in ("en", "hi", "te"):
            s = score([r for r in res if r["language"] == lang])
            xl.append({"config": f"{strat} · {lang}", **s})
    r = services().retriever()
    engine = f"embedder `{r.embedder.name}`, reranker `{getattr(r.reranker, 'name', 'off')}`, LLM {'on' if llm.available() else 'off'}"
    text = (f"# Ablations ({date.today()})\n\n{engine}. SchemeQA-Indic v0 ({len(items)} items, author-draft).\n\n"
            "Each row adds one technique to the row above.\n\n" + md_table(rows, COLS)
            + "\n\n## Cross-lingual strategies\n\nA = embed the original query, B = translate to English first, C = both fused.\n\n"
            + md_table(xl, ["config", "recall@5", "mrr", "correctness", "abstain_recall"])
            + ("\n\nNote: with the light hashing embedder and lexical reranker, B/C depend on the offline glossary; rerun with "
               "`uv sync --extra ml` (BGE-M3 + bge-reranker-v2-m3) and `GEMINI_API_KEY` for the full-model numbers.\n"
               if r.embedder.name == "hash" else "\n\nWith LLM off, strategy B translates with the offline glossary only.\n"))
    (REPORTS / "ablations.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
