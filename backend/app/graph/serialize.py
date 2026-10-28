"""Turn rule-engine outcomes into UI payloads (scheme cards, citations)."""
from __future__ import annotations

from ..eligibility.dsl import Scheme, Source
from ..eligibility.evaluator import SchemeOutcome
from ..eligibility.explain import doc_label, rule_label, value_label, what_if_text
from .templates import STATUS


class Citations:
    def __init__(self, corpus) -> None:
        self.corpus = corpus
        self.items: list[dict] = []

    def add(self, src: Source | dict, scheme_id: str | None = None, structured: bool = True, text: str | None = None) -> int:
        s = src if isinstance(src, dict) else src.model_dump()
        for c in self.items:
            if c["doc"] == s["doc"] and c["page"] == s["page"] and c.get("quote") == s.get("quote"):
                return c["id"]
        doc = self.corpus.docs.get(s["doc"])
        scheme = self.corpus.schemes.get(scheme_id) if scheme_id else self.corpus.scheme_for_doc(s["doc"])
        cid = len(self.items) + 1
        self.items.append({
            "id": cid, "doc": s["doc"], "page": s["page"], "quote": s.get("quote") or (text or "")[:300],
            "bbox": s.get("bbox"), "scheme_id": scheme.scheme_id if scheme else None,
            "title": doc.title if doc else s["doc"], "source_url": doc.source_url if doc else None,
            "kind": doc.kind if doc else "seed", "structured": structured, "status": "pending",
            "passage": text,
        })
        return cid

    def verified(self) -> list[dict]:
        """Structured citations quote the rule DB; check each quote really is on its cited page."""
        for c in self.items:
            if c["status"] != "pending":
                continue
            doc = self.corpus.docs.get(c["doc"])
            try:
                page = " ".join(doc.page(c["page"]).text.split()) if doc else ""
            except StopIteration:
                page = ""
            c["status"] = "supported" if c.get("quote") and " ".join(c["quote"].split()) in page else "unclear"
            c.pop("passage", None)
        return self.items


def scheme_card(o: SchemeOutcome, lang: str, cites: Citations) -> dict:
    s: Scheme = o.scheme
    rules = []
    for ro in o.rules:
        cid = cites.add(ro.rule.source, s.scheme_id)
        rules.append({
            "id": ro.rule.id, "field": ro.rule.field, "label": rule_label(ro.rule, lang), "result": ro.result,
            "user_value": value_label(ro.rule.field, ro.user_value, lang) if ro.user_value is not None else None,
            "citation": cid, "quote": ro.rule.source.quote,
        })
    benefit_cid = cites.add(s.benefit.source, s.scheme_id)
    apply_cid = cites.add(s.how_to_apply.source, s.scheme_id)
    card = {
        "scheme_id": s.scheme_id, "status": o.status, "status_label": STATUS[o.status][lang],
        "name": s.name.get(lang), "name_en": s.name.en, "tagline": s.tagline.get(lang),
        "level": s.level, "state": s.state, "categories": s.categories,
        "benefit": s.benefit.summary.get(lang), "amount": s.benefit.amount,
        "unit": s.benefit.unit.get(lang) if s.benefit.unit else None, "per_acre": s.benefit.per_acre,
        "benefit_citation": benefit_cid,
        "rules": rules, "logic": s.logic, "missing_fields": o.missing_fields,
        "documents": [{"key": d, "label": doc_label(d, lang)} for d in s.documents_required],
        "how_to_apply": s.how_to_apply.summary.get(lang), "apply_citation": apply_cid,
        "official_url": s.official_url, "last_verified": s.last_verified, "review_status": s.review_status,
        "changed_on": s.changed_on, "change_note": s.change_note.get(lang) if s.change_note else None,
        "official_sources": [{k: o.get(k) for k in ("doc", "url", "label", "downloaded")} for o in s.official_sources],
        "what_if": None,
    }
    if o.what_if:
        w = o.what_if
        card["what_if"] = {**{k: w[k] for k in ("rule_id", "field", "threshold", "current", "direction", "would_be")},
                           "text": what_if_text(w, s.name.get(lang), lang),
                           "citation": cites.add(w["source"], s.scheme_id)}
    return card
