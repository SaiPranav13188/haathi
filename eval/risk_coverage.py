"""Risk–coverage curve for the abstention threshold (haathi.md §10.3 exp. 6).

Runs every free-form ("general") question with abstention disabled, records the top rerank score, and for each
threshold t computes coverage = share of questions answered and risk = share of answered ones that are wrong
(unanswerable answered, or answerable answered without the gold facts). Writes the curve and the chosen t.
"""
from __future__ import annotations

import json

from harness import REPORTS, load_items, run


def main() -> None:
    items = load_items()
    results = run(items, {"abstain_threshold": 0.0, "corrective": False})
    # only items that reach the threshold gate (no scheme named, not a profile question)
    gated = [r for r in results if r["intent"] == "general"]
    pts = []
    for t in [i / 100 for i in range(0, 61, 2)]:
        answered = [r for r in gated if r["top_score"] >= t and not r["abstained"]]
        wrong = [r for r in answered if not r["answerable"] or not all(m.lower() in r["text"].lower() for m in r["must"])]
        refused_ok = [r for r in gated if (r["top_score"] < t or r["abstained"]) and r["answerable"]]
        refused_bad = [r for r in gated if (r["top_score"] < t or r["abstained"]) and not r["answerable"]]
        acc = (len(answered) - len(wrong) + len(refused_bad)) / len(gated)
        pts.append({"t": t, "coverage": round(len(answered) / len(gated), 3), "risk": round(len(wrong) / len(answered), 3) if answered else 0.0,
                    "lost_answerable": len(refused_ok), "accuracy": round(acc, 3)})
    # choose: highest accuracy (correct answers + correct refusals); tie-break lower risk, then lower threshold
    best = max(pts, key=lambda p: (p["accuracy"], -p["risk"], -p["t"]))
    lines = ["# Abstention threshold: risk–coverage", "", f"Free-form questions reaching the gate: {len(gated)}", "", "| threshold | coverage | risk | accuracy | answerable refused |", "|---|---|---|---|---|"]
    lines += [f"| {p['t']:.2f} | {p['coverage']:.3f} | {p['risk']:.3f} | {p['accuracy']:.3f} | {p['lost_answerable']} |" for p in pts]
    lines += ["", f"**Chosen threshold: {best['t']:.2f}** (risk {best['risk']:.3f} at coverage {best['coverage']:.3f}). "
              "Set `HAATHI_ABSTAIN_THRESHOLD` to override.", "",
              "Scores of unanswerable items: " + ", ".join(f"{r['id']}={r['top_score']:.2f}" for r in gated if not r["answerable"]),
              "", "Lowest scores of answerable free-form items: " + ", ".join(
                  f"{r['id']}={r['top_score']:.2f}" for r in sorted([r for r in gated if r["answerable"]], key=lambda r: r["top_score"])[:6])]
    (REPORTS / "risk_coverage.md").write_text("\n".join(lines) + "\n")
    (REPORTS / "risk_coverage.json").write_text(json.dumps({"points": pts, "chosen": best}, indent=1))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
