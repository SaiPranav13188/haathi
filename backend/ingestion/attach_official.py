"""Point seed rules at the official documents that back them (review step after `make ingest-download`).

Each mapping says: this seed rule (or benefit) is supported by this sentence of this official document. A quote is
used only if it is found on that page of the parsed document (exactly, or as the whole block that fuzzily matches),
so a citation can never point at text that isn't there. Rules without official support keep their seed source.

    uv run python -m ingestion.attach_official
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from rapidfuzz import fuzz

from app.config import get_settings

from .parse import ParsedDoc

# scheme -> {rule id | "benefit": (official doc, page, quote fragment)}
# ("@ext:<rule>" reuses the quote Gemini extracted for that rule in data/schemes_pending/<doc stem>_extracted.json)
MAP: dict[str, dict[str, tuple[str, int, str]]] = {
    "apy": {"r1": ("apy.pdf", 2, "@ext:r1"), "r2": ("apy.pdf", 2, "@ext:r3"), "r3": ("apy.pdf", 2, "@ext:r2"),
            "benefit": ("apy.pdf", 3, "Lifelong pension between ₹1,000 to ₹5,000 from age 60 until death")},
    "pm_sym": {"r1": ("pm_sym.pdf", 2, "@ext:r3"), "r2": ("pm_sym.pdf", 2, "@ext:r1"), "r3": ("pm_sym.pdf", 2, "@ext:r2"),
               "r4": ("pm_sym.pdf", 3, "@ext:r4"), "r5": ("pm_sym.pdf", 3, "@ext:r5"),
               "benefit": ("pm_sym.pdf", 2, "Minimum Assured Pension: ₹3,000 per month after 60 years of age.")},
    "pmjjby": {"r1": ("pmjjby.pdf", 2, "@ext:r1"), "r2": ("pmjjby.pdf", 2, "@ext:r2")},
    "pmsby": {"r1": ("pmsby.pdf", 4, "@ext:r1"), "r2": ("pmsby.pdf", 4, "@ext:r2")},
    "pmay_u": {"r1": ("pmay_u.pdf", 17, "@ext:r1"), "r2": ("pmay_u.pdf", 17, "@ext:r2"), "r3": ("pmay_u.pdf", 17, "@ext:r3")},
    "pmfby": {"r1": ("pmfby.pdf", 13, "@ext:r1")},
    "post_matric_sc": {"r1": ("post_matric_sc.pdf", 2, "SC students in higher education"),
                       "r2": ("post_matric_sc.pdf", 4, "Scholarships will be given for the study of all recognized post-matriculation or postsecondary courses"),
                       "r3": ("post_matric_sc.pdf", 5, "@ext:r2")},
    "ts_mahalakshmi_bus": {"r1": ("ts_mahalakshmi_bus.pdf", 1, "@ext:r2"), "r2": ("ts_mahalakshmi_bus.pdf", 1, "@ext:r1"),
                           "benefit": ("ts_mahalakshmi_bus.pdf", 1, "They can travel anywhere within the borders of Telangana State in Palle velugu and Express buses")},
    "ts_mahalakshmi_lpg": {"r1": ("ts_mahalakshmi_lpg.pdf", 1, "They should be White Ration Card (FSC) holders in Telangana."),
                           "r2": ("ts_mahalakshmi_lpg.pdf", 1, "They should be White Ration Card (FSC) holders in Telangana."),
                           "r3": ("ts_mahalakshmi_lpg.pdf", 1, "They should have active domestic LPG connection in their name."),
                           "benefit": ("ts_mahalakshmi_lpg.pdf", 1, "Supply of LPG Domestic Cylinder at a subsidized rate of Rs.500/- per refill")},
    "ts_kalyana_lakshmi": {"r1": ("ts_kalyana_lakshmi.pdf", 1, "@ext:r2"), "r7": ("ts_kalyana_lakshmi.pdf", 1, "@ext:r1"),
                           "benefit": ("ts_kalyana_lakshmi_amount.pdf", 1, "hereby enhance the financial assistance from Rs.75,116/- to Rs.1,00,116/-")},
    "ts_shaadi_mubarak": {"r1": ("ts_kalyana_lakshmi.pdf", 1, "@ext:r2"), "r7": ("ts_kalyana_lakshmi.pdf", 1, "@ext:r1"),
                          "benefit": ("ts_kalyana_lakshmi_amount.pdf", 1, "hereby enhance the financial assistance from Rs.75,116/- to Rs.1,00,116/-")},
    "ts_epass_post_matric": {"r3": ("ts_epass_post_matric.pdf", 1, "@ext:r2"), "r4": ("ts_epass_post_matric.pdf", 1, "@ext:r2")},
    "ts_aasara_pension": {"benefit": ("ts_aasara_pension.pdf", 1, "Enhanced monthly Pension under Aasara Scheme w.e.f. June, 2019 payable in July, 2019 (Rs.): 2016/-")},
    "kcc": {},
    "pm_vishwakarma": {},
}
# official documents to list on each scheme even where no single rule could be re-pointed
REFERENCES = {"kcc": ["kcc.html"], "pm_vishwakarma": ["pm_vishwakarma.pdf"], "ts_aasara_pension": ["ts_aasara_pension.pdf"]}


def _norm(s: str) -> str:
    return " ".join(s.split())


def resolve(doc: ParsedDoc, page: int, quote: str) -> str | None:
    p = doc.page(page)
    text = _norm(p.text)
    q = _norm(quote)
    if q in text:
        return q
    best = max(p.blocks, key=lambda b: fuzz.partial_ratio(q, _norm(b.text)), default=None)
    if best is not None and fuzz.partial_ratio(q, _norm(best.text)) >= 90:
        return _norm(best.text)[:400] if len(_norm(best.text)) <= 400 else None
    return None


def main() -> None:
    s = get_settings()
    parsed = s.index_dir / "parsed"
    pending = s.data_dir / "schemes_pending"
    state = {}
    for name in ("manifest_state.json", "goir_state.json"):
        p = s.data_dir / "raw" / name
        if p.exists():
            state.update(json.loads(p.read_text()))
    log_rows = []
    for sid, mapping in MAP.items():
        path = s.data_dir / "schemes" / f"{sid}.json"
        sc = json.loads(path.read_text(encoding="utf-8"))
        changed, refs = 0, set(REFERENCES.get(sid, []))
        for key, (doc_id, page, quote) in mapping.items():
            doc = ParsedDoc.from_json(json.loads((parsed / f"{doc_id}.json").read_text()))
            if quote.startswith("@ext:"):
                ext = json.loads((pending / f"{Path(doc_id).stem}_extracted.json").read_text())
                quote = next(r["source"]["quote"] for r in ext["rules"] if r["id"] == quote[5:])
            exact = resolve(doc, page, quote)
            if not exact:
                print(f"  ✗ {sid}.{key}: quote not found on {doc_id} p{page}; keeping seed source")
                continue
            target = sc["benefit"] if key == "benefit" else next(r for r in sc["rules"] if r["id"] == key)
            target["source"] = {"doc": doc_id, "page": page, "quote": exact}
            refs.add(doc_id)
            changed += 1
        if not refs:
            continue
        sc["official_sources"] = []
        for doc_id in sorted(refs):
            stem = Path(doc_id).stem
            st = state.get(stem, {})
            sc["official_sources"].append({
                "doc": doc_id, "url": st.get("url") or "https://goir.telangana.gov.in",
                "label": f"{st['go']} ({st['dept']}), {st['date']}" if st.get("go") else (ParsedDoc.from_json(json.loads((parsed / f'{doc_id}.json').read_text())).title[:90]),
                "downloaded": (st.get("downloaded_at") or "")[:10], "sha256": st.get("sha256"),
            })
        sc["review_status"] = "edited" if changed else sc.get("review_status", "seed")
        sc["last_verified"] = str(date.today())
        path.write_text(json.dumps(sc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        log_rows.append({"scheme_id": sid, "action": "edit" if changed else "approve", "rules": len(sc["rules"]),
                         "rules_changed": changed, "ts": str(date.today()), "note": "re-pointed to official documents"})
        print(f"  ✓ {sid}: {changed} citation(s) now point to {', '.join(sorted(refs))}")
    with (s.data_dir / "review_log.jsonl").open("a") as f:
        for r in log_rows:
            f.write(json.dumps(r) + "\n")
    # extracted drafts have been reviewed; move them out of the pending queue
    done = pending / "reviewed"
    done.mkdir(exist_ok=True)
    for p in pending.glob("*_extracted.json"):
        p.rename(done / p.name)


if __name__ == "__main__":
    main()
