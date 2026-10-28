"""Shared evaluation harness: runs the LangGraph agent on SchemeQA items under a given configuration."""
from __future__ import annotations

import asyncio
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app import llm  # noqa: E402
from app.graph.build import build_graph  # noqa: E402

BENCH = ROOT / "eval" / "schemeqa" / "schemeqa_v0.jsonl"
REPORTS = ROOT / "eval" / "reports"
REPORTS.mkdir(exist_ok=True)


def load_items(path: Path = BENCH) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


async def run_item(item: dict, overrides: dict) -> dict:
    t0 = time.perf_counter()
    state = {"query": item["question"], "ui_lang": item["language"], "profile": {}, "asked": [],
             "skip_questions": item["type"] == "eligibility", "overrides": overrides}
    final = await build_graph().ainvoke(state)
    ans = final["answer"]
    hits = [h for h in (final.get("hits") or []) if h.sources != {"mention": 1}]
    return {
        "id": item["id"], "language": item["language"], "type": item["type"], "answerable": item["answerable"],
        "intent": final.get("intent"),
        "latency_ms": (time.perf_counter() - t0) * 1000,
        "text": ans["text"], "abstained": bool(ans.get("abstained")),
        # a passage counts if it belongs to the gold scheme (its seed summary or its official document)
        "retrieved": [(h.chunk.scheme_id or h.chunk.doc_id, h.chunk.page) for h in hits[:5]],
        "top_score": final.get("top_score", 0.0),
        "eligible": sorted(c["scheme_id"] for c in ans.get("cards", []) if c["status"] == "eligible"),
        "citations": [c["status"] for c in ans.get("citations", [])],
        "gold_sources": [(g["doc"].rsplit(".", 1)[0], g["page"]) for g in item["gold_sources"]],
        "must": item["gold_answer_must_include"], "gold_eligible": item.get("gold_eligible"),
    }


JUDGE = """Question: {q}
Reference facts that a correct answer must contain: {must}
Answer: {a}
Is the answer correct and does it contain the reference facts? Reply JSON {{"correct": true|false}}."""


async def judge(r: dict, question: str) -> bool | None:
    # LLM-as-judge costs one request per item; opt in with HAATHI_EVAL_JUDGE=1 (free tier is small)
    import os

    if os.environ.get("HAATHI_EVAL_JUDGE") != "1" or not llm.available() or not r["must"]:
        return None
    data = await llm.complete_json(JUDGE.format(q=question, must="; ".join(r["must"]), a=r["text"]))
    return bool(data.get("correct")) if isinstance(data, dict) else None


def score(results: list[dict]) -> dict:
    def mean(xs):
        xs = [x for x in xs if x is not None]
        return round(100 * sum(xs) / len(xs), 1) if xs else None

    ret = [r for r in results if r["answerable"] and r["gold_sources"]]
    recall, rr = [], []
    for r in ret:
        gold_docs = {d for d, _ in r["gold_sources"]}
        docs = [d for d, _ in r["retrieved"]]
        recall.append(any(d in gold_docs for d in docs[:5]))
        rank = next((i + 1 for i, d in enumerate(docs) if d in gold_docs), None)
        rr.append(1 / rank if rank else 0.0)
    factual = [r for r in results if r["answerable"] and r["must"]]
    correct = [all(m.lower() in r["text"].lower() for m in r["must"]) and not r["abstained"] for r in factual]
    elig = [r for r in results if r["gold_eligible"] is not None]
    f1s, exact = [], []
    for r in elig:
        g, p = set(r["gold_eligible"]), set(r["eligible"])
        tp = len(g & p)
        prec = tp / len(p) if p else (1.0 if not g else 0.0)
        rec = tp / len(g) if g else 1.0
        f1s.append(0 if prec + rec == 0 else 2 * prec * rec / (prec + rec))
        exact.append(g == p)
    unans = [r for r in results if not r["answerable"]]
    ans = [r for r in results if r["answerable"]]
    cites = [c for r in results for c in r["citations"]]
    lat = sorted(r["latency_ms"] for r in results)
    return {
        "n": len(results),
        "recall@5": mean(recall), "mrr": round(sum(rr) / len(rr), 3) if rr else None,
        "correctness": mean(correct),
        "eligibility_f1": mean(f1s), "eligibility_exact": mean(exact),
        "abstain_recall": mean([r["abstained"] for r in unans]),          # unanswerable correctly refused
        "false_abstain": mean([r["abstained"] for r in ans]),             # answerable wrongly refused
        "faithfulness": mean([c == "supported" for c in cites]),
        "p50_ms": round(statistics.median(lat), 1) if lat else None,
        "p95_ms": round(lat[min(len(lat) - 1, int(0.95 * len(lat)))], 1) if lat else None,
    }


def run(items: list[dict], overrides: dict) -> list[dict]:
    async def go():
        out = []
        for it in items:
            r = await run_item(it, overrides)
            j = await judge(r, it["question"])
            r["judge_correct"] = j
            out.append(r)
        return out

    return asyncio.run(go())


def md_table(rows: list[dict], cols: list[str]) -> str:
    head = "| " + " | ".join(cols) + " |\n|" + "|".join("---" for _ in cols) + "|\n"
    return head + "".join("| " + " | ".join("—" if r.get(c) is None else str(r.get(c)) for c in cols) + " |\n" for r in rows)
