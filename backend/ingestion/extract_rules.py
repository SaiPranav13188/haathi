"""LLM rule extraction (haathi.md §5 step 6, Prompt 4): eligibility sections → Rule DSL with source quotes.

Every extracted rule must quote the parsed document (exact or fuzzy ≥ 90); otherwise it is rejected. Results
go to data/schemes_pending/ with review_status "pending" for the human review page (/admin).
"""
from __future__ import annotations

import json
import logging

from rapidfuzz import fuzz

from app import llm
from app.config import get_settings
from app.eligibility.dsl import Scheme
from app.eligibility.fields import FIELDS

from .parse import ParsedDoc

log = logging.getLogger(__name__)

PROMPT = """You convert Indian government scheme guidelines into a JSON rule DSL.
Allowed fields (use ONLY these; skip criteria that don't map):
{fields}
Ops: eq, neq, in, not_in, lt, lte, gt, gte, between, exists. Money = ₹ per year (convert monthly × 12).
Return JSON:
{{"rules":[{{"id":"r1","field":"...","op":"...","value":...,"page":<page>,"quote":"<exact sentence copied from the text>"}}],
  "logic":"r1 AND r2 ...", "benefit":{{"summary":"...","amount":<number or null>,"page":<page>,"quote":"..."}},
  "documents_required":["aadhaar", ...], "how_to_apply":{{"summary":"...","page":<page>,"quote":"..."}}}}
Quotes MUST be copied verbatim from the document. Use OR with parentheses when criteria have alternatives.

Document (pages marked):
{doc}"""


def _fields_spec() -> str:
    return "\n".join(f"- {f.name} ({f.kind})" + (f": {[o.value for o in f.options]}" if f.kind == "choice" else "") for f in FIELDS.values())


def _quote_ok(doc: ParsedDoc, page: int, quote: str) -> bool:
    try:
        text = " ".join(doc.page(page).text.split())
    except StopIteration:
        return False
    q = " ".join(quote.split())
    return q in text or fuzz.partial_ratio(q, text) >= 90


def extract(doc: ParsedDoc, scheme_id: str, meta: dict) -> dict | None:
    if not llm.available():
        log.info("no LLM configured; skipping rule extraction for %s", scheme_id)
        return None
    text = "\n".join(f"<!-- page {p.page} -->\n{p.text}" for p in doc.pages)[:40000]
    data = llm.run_sync(llm.complete_json(PROMPT.format(fields=_fields_spec(), doc=text)))
    if not isinstance(data, dict):
        return None
    kept, rejected = [], 0
    for r in data.get("rules", []):
        if r.get("field") in FIELDS and r.get("quote") and _quote_ok(doc, int(r.get("page", 1)), r["quote"]):
            kept.append({"id": r["id"], "field": r["field"], "op": r["op"], "value": r.get("value"),
                         "source": {"doc": doc.doc_id, "page": int(r.get("page", 1)), "quote": r["quote"]}})
        else:
            rejected += 1
    if not kept:
        return None
    name = meta.get("name", scheme_id)
    out = {
        "scheme_id": scheme_id, "version": "extracted", "doc": doc.doc_id,
        "name": {"en": name}, "tagline": {"en": data.get("benefit", {}).get("summary", name)},
        "level": "state" if meta.get("state") else "central", "state": meta.get("state") or None,
        "categories": [meta.get("category") or "other"], "official_url": meta.get("url", ""),
        "last_verified": meta.get("downloaded_at", "")[:10] or "unknown", "review_status": "pending",
        "rules": kept, "logic": data.get("logic") or " AND ".join(r["id"] for r in kept),
        "benefit": {"summary": {"en": data.get("benefit", {}).get("summary", "")}, "amount": data.get("benefit", {}).get("amount"),
                    "source": {"doc": doc.doc_id, "page": int(data.get("benefit", {}).get("page", 1)), "quote": data.get("benefit", {}).get("quote")}},
        "documents_required": data.get("documents_required", []),
        "how_to_apply": {"summary": {"en": data.get("how_to_apply", {}).get("summary", "")},
                         "source": {"doc": doc.doc_id, "page": int(data.get("how_to_apply", {}).get("page", 1)), "quote": data.get("how_to_apply", {}).get("quote")}},
        "extraction": {"rules_kept": len(kept), "rules_rejected_no_quote": rejected},
    }
    try:
        Scheme.model_validate(out)
    except Exception as e:  # logic referencing a rejected rule, bad ops, ...
        log.warning("extracted scheme %s failed validation: %s", scheme_id, e)
        out["logic"] = " AND ".join(r["id"] for r in kept)
    pending = get_settings().data_dir / "schemes_pending"
    pending.mkdir(parents=True, exist_ok=True)
    (pending / f"{scheme_id}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2))
    return out
