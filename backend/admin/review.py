"""Human review of extracted rules (haathi.md §5 step 7): rule list beside the highlighted source.

Approve / edit / reject each scheme's rules; every decision is logged so the share of rules that needed
fixing can be reported as a metric.
"""
from __future__ import annotations

import html
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from app.config import get_settings
from app.eligibility.dsl import Scheme
from ingestion.parse import locate_quote

router = APIRouter(prefix="/admin", tags=["admin"])

CSS = """<style>
body{font:15px/1.5 system-ui,'Noto Sans',sans-serif;margin:0;background:#f6efe3;color:#1d2a30}
header{background:#0b5f73;color:#fff;padding:14px 24px;display:flex;gap:16px;align-items:center}
header a{color:#ffd27a} main{padding:20px 24px;max-width:1300px;margin:auto}
table{border-collapse:collapse;width:100%;background:#fff;border-radius:12px;overflow:hidden}
td,th{padding:8px 10px;border-bottom:1px solid #eadfcd;text-align:left;vertical-align:top}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px} .card{background:#fff;border-radius:14px;padding:16px;box-shadow:0 1px 3px #0002}
mark{background:#ffd27a;padding:0 2px;border-radius:3px} .pill{padding:2px 8px;border-radius:99px;font-size:12px;background:#e6f0f2}
.seed{background:#eee}.pending{background:#ffe7b3}.approved{background:#d7efd9}.edited{background:#d9e8ff}.rejected{background:#f8d4d0}
textarea{width:100%;font:13px ui-monospace,monospace;min-height:340px} button{padding:8px 14px;border-radius:10px;border:0;margin-right:6px;cursor:pointer}
.ok{background:#3a8f4b;color:#fff}.ed{background:#0b5f73;color:#fff}.no{background:#c65a50;color:#fff} pre{white-space:pre-wrap}
</style>"""


def _dirs():
    s = get_settings()
    return s.data_dir / "schemes", s.data_dir / "schemes_pending"


def _load(scheme_id: str) -> tuple[dict, str]:
    for d in _dirs():
        p = d / f"{scheme_id}.json"
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8")), str(p)
    raise HTTPException(404)


def _log(scheme_id: str, action: str, n_rules: int, n_changed: int) -> None:
    p = get_settings().data_dir / "review_log.jsonl"
    with p.open("a") as f:
        f.write(json.dumps({"scheme_id": scheme_id, "action": action, "rules": n_rules, "rules_changed": n_changed,
                            "ts": datetime.now(timezone.utc).isoformat()}) + "\n")


def review_stats() -> dict:
    p = get_settings().data_dir / "review_log.jsonl"
    rows = [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []
    total = sum(r["rules"] for r in rows if r["action"] in {"approve", "edit"})
    changed = sum(r["rules_changed"] for r in rows if r["action"] == "edit")
    return {"reviews": len(rows), "rules_reviewed": total, "rules_needing_edit": changed,
            "pct_rules_edited": round(100 * changed / total, 1) if total else None}


@router.get("", response_class=HTMLResponse)
async def index() -> str:
    rows = []
    for d in _dirs():
        if not d.exists():
            continue
        for p in sorted(d.glob("*.json")):
            s = json.loads(p.read_text(encoding="utf-8"))
            st = s.get("review_status", "seed")
            rows.append(f"<tr><td><a href='/admin/{s['scheme_id']}'>{html.escape(s['name']['en'])}</a></td><td>{s.get('state') or 'Central'}</td>"
                        f"<td>{len(s['rules'])}</td><td><span class='pill {st}'>{st}</span></td><td>{s.get('last_verified','')}</td></tr>")
    st = review_stats()
    return (f"<html><head><title>Haathi rule review</title>{CSS}</head><body><header><b>🐘 Haathi · Rule review</b>"
            f"<span>Rules reviewed: {st['rules_reviewed']} · needing edits: {st['rules_needing_edit']} ({st['pct_rules_edited'] or 0}%)</span></header>"
            f"<main><table><tr><th>Scheme</th><th>State</th><th>Rules</th><th>Status</th><th>Verified</th></tr>{''.join(rows)}</table></main></body></html>")


@router.get("/{scheme_id}", response_class=HTMLResponse)
async def detail(scheme_id: str) -> str:
    from app.services import services

    raw, _ = _load(scheme_id)
    doc = services().corpus.docs.get(raw["doc"])
    rule_rows, pages_html = [], {}
    for r in raw["rules"]:
        rule_rows.append(f"<tr><td>{r['id']}</td><td><code>{r['field']} {r['op']} {html.escape(json.dumps(r['value'], ensure_ascii=False))}</code></td>"
                         f"<td>p{r['source']['page']}: “{html.escape(r['source'].get('quote') or '')}”</td></tr>")
    if doc:
        for p in doc.pages:
            quotes = [r["source"]["quote"] for r in raw["rules"] if r["source"]["page"] == p.page and r["source"].get("quote")]
            hl = {(s["block"], s["line"]): s for q in quotes for s in locate_quote(p, q)}
            out = []
            for b in p.blocks:
                lines = []
                for li, ln in enumerate(b.lines):
                    t = html.escape(ln.text)
                    if (b.id, li) in hl:
                        sp = hl[(b.id, li)]
                        t = html.escape(ln.text[:sp["start"]]) + "<mark>" + html.escape(ln.text[sp["start"]:sp["end"]]) + "</mark>" + html.escape(ln.text[sp["end"]:])
                    lines.append(t)
                tag = "h3" if b.type in {"heading", "title"} else "p"
                out.append(f"<{tag}>{' '.join(lines)}</{tag}>")
            pages_html[p.page] = "".join(out)
    src = "".join(f"<div class='card'><b>Page {n}</b>{h}</div><br>" for n, h in pages_html.items())
    st = raw.get("review_status", "seed")
    return (f"<html><head><title>Review {html.escape(raw['name']['en'])}</title>{CSS}</head><body><header><a href='/admin'>← all</a>"
            f"<b>{html.escape(raw['name']['en'])}</b><span class='pill {st}'>{st}</span></header><main><div class='grid'>"
            f"<div><div class='card'><table><tr><th>id</th><th>rule</th><th>source</th></tr>{''.join(rule_rows)}</table>"
            f"<p><b>logic:</b> <code>{html.escape(raw['logic'])}</code></p></div><br>"
            f"<form class='card' method='post' action='/admin/{scheme_id}'><textarea name='body'>{html.escape(json.dumps(raw, ensure_ascii=False, indent=2))}</textarea><br>"
            f"<button class='ok' name='action' value='approve'>Approve</button><button class='ed' name='action' value='edit'>Save edits</button>"
            f"<button class='no' name='action' value='reject'>Reject</button></form></div><div>{src}</div></div></main></body></html>")


@router.post("/{scheme_id}")
async def decide(scheme_id: str, action: str = Form(...), body: str = Form(...)):
    raw, path = _load(scheme_id)
    if action == "reject":
        raw["review_status"] = "rejected"
        new = raw
        changed = 0
    else:
        try:
            new = json.loads(body)
            Scheme.model_validate(new)
        except Exception as e:
            raise HTTPException(400, f"invalid scheme JSON: {e}")
        old_rules = {r["id"]: json.dumps(r, sort_keys=True) for r in raw["rules"]}
        changed = sum(old_rules.get(r["id"]) != json.dumps(r, sort_keys=True) for r in new["rules"])
        new["review_status"] = "edited" if (action == "edit" and changed) else "approved"
    _log(scheme_id, action, len(raw["rules"]), changed)
    # approved/edited rules move into the live rule DB
    live = _dirs()[0] / f"{scheme_id}.json"
    live.write_text(json.dumps(new, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if path != str(live):
        from pathlib import Path

        Path(path).unlink(missing_ok=True)
    return RedirectResponse(f"/admin/{scheme_id}", status_code=303)
