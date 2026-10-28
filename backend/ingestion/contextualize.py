"""Contextual Retrieval: prepend a 1–2 sentence note to every chunk before indexing (cached on disk).

With GEMINI_API_KEY the note is written by Gemini from the whole document; without it a deterministic
template note is used (scheme, level, state, section) so the technique can still be ablated.
"""
from __future__ import annotations

import hashlib
import json
import logging

from app import llm
from app.config import get_settings

from .chunk import Chunk
from .parse import ParsedDoc

log = logging.getLogger(__name__)

PROMPT = """<document>
{doc}
</document>
Here is a chunk from the document above:
<chunk>
{chunk}
</chunk>
Write one or two short sentences that situate this chunk within the document (which scheme, which section,
which government, what it is about) to improve search retrieval. Answer with only the sentences."""


def _template(c: Chunk, scheme: dict | None) -> str:
    if not scheme:
        return f"This passage is from the {c.section or 'main'} section of {c.doc_id}."
    gov = "Government of India (central scheme)" if scheme["level"] == "central" else f"Government of {scheme['state']}"
    return (f"This passage is from the {c.section or 'main'} section of the {scheme['name']['en']} guidelines, "
            f"a scheme of the {gov} for {', '.join(scheme['categories'])}.")


def contextualize(chunks: list[Chunk], docs: dict[str, ParsedDoc], schemes_by_id: dict[str, dict]) -> None:
    s = get_settings()
    path = s.cache_dir / "context_notes.json"
    s.cache_dir.mkdir(parents=True, exist_ok=True)
    cache: dict[str, str] = json.loads(path.read_text()) if path.exists() else {}
    use_llm = s.contextual_llm and llm.available()
    dirty = False
    for c in chunks:
        key = f"{'llm' if use_llm else 'tpl'}:{c.id}:{hashlib.sha1(c.text.encode()).hexdigest()[:10]}"
        if key in cache:
            c.context = cache[key]
            continue
        note = None
        if use_llm:
            try:
                doc_text = "\n".join(p.text for p in docs[c.doc_id].pages)
                note = llm.run_sync(llm.complete(PROMPT.format(doc=doc_text[:12000], chunk=c.text)))
            except RuntimeError:
                note = None  # inside an event loop (server start-up): fall back to template
        c.context = (note or _template(c, schemes_by_id.get(c.scheme_id or ""))).strip()
        if use_llm and not note:
            continue  # LLM unavailable / rate-limited: don't cache the template under the LLM key; retry next run
        cache[key] = c.context
        dirty = True
    if dirty:
        path.write_text(json.dumps(cache, ensure_ascii=False, indent=0))
