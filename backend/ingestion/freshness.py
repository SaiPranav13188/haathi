"""Freshness tracking (haathi.md §5 step 8, Prompt 9): weekly re-download; on hash change, diff the text,
keep the old version, re-extract rules for review, and mark the scheme "changed" (🦎 in the UI)."""
from __future__ import annotations

import difflib
import json
import logging
from datetime import date
from pathlib import Path

from app.config import get_settings

from .download import download_all, read_manifest
from .extract_rules import extract
from .parse import parse_any, save

log = logging.getLogger(__name__)


def run(only: set[str] | None = None) -> list[dict]:
    s = get_settings()
    parsed_dir = s.index_dir / "parsed"
    versions = s.data_dir / "versions"
    meta = {r["scheme_id"]: r for r in read_manifest()}
    state = download_all(only)
    changes = []
    for sid, st in state.items():
        if not st.get("changed"):
            continue
        new_path = s.data_dir / "raw" / st["file"]
        old_parsed = parsed_dir / f"{st['file']}.json"
        old_text = ""
        if old_parsed.exists():
            old = json.loads(old_parsed.read_text())
            old_text = "\n".join(b["text"] for p in old["pages"] for b in p["blocks"])
            vdir = versions / st["file"]
            vdir.mkdir(parents=True, exist_ok=True)
            (vdir / f"{date.today()}.json").write_text(old_parsed.read_text())
        doc = parse_any(new_path, st["url"])
        save(doc, parsed_dir)
        new_text = "\n".join(b.text for p in doc.pages for b in p.blocks)
        diff = list(difflib.unified_diff(old_text.splitlines(), new_text.splitlines(), lineterm="", n=0))
        changes.append({"scheme_id": sid, "date": str(date.today()), "diff_lines": len(diff), "diff": diff[:80]})
        extract(doc, sid, {**meta.get(sid, {}), **st})
        live = s.data_dir / "schemes" / f"{sid}.json"
        if live.exists():
            sc = json.loads(live.read_text())
            sc["changed_on"] = str(date.today())
            sc["change_note"] = {"en": "The official document changed; rules are being re-checked.",
                                 "hi": "आधिकारिक दस्तावेज़ बदला है; नियम दोबारा जाँचे जा रहे हैं।",
                                 "te": "అధికారిక పత్రం మారింది; నియమాలను మళ్లీ తనిఖీ చేస్తున్నాం."}
            live.write_text(json.dumps(sc, ensure_ascii=False, indent=2) + "\n")
    report = Path(s.data_dir).parent / "eval" / "reports" / "freshness.md"
    lines = [f"# Freshness run {date.today()}", "", f"Checked {len(state)} sources; {len(changes)} changed.", ""]
    for c in changes:
        lines += [f"## {c['scheme_id']} ({c['diff_lines']} changed lines)", "```diff", *c["diff"], "```", ""]
    report.write_text("\n".join(lines))
    return changes


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
