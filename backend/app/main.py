"""FastAPI app: SSE chat streaming animation events, eligibility API, source viewer API, feedback, ASR."""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from collections import OrderedDict, deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncIterator

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse

from ingestion.parse import locate_quote, union_bbox

from . import llm
from .config import get_settings
from .eligibility.evaluator import evaluate, evaluate_all
from .eligibility.fields import FIELDS, FIXED_ORDER, spec_json
from .eligibility.questioner import rank_questions
from .graph.build import build_graph, langfuse_config
from .graph.serialize import Citations, scheme_card
from .graph.templates import DISCLAIMER
from .models import AskRequest, ChatRequest, EvaluateRequest, FeedbackRequest, NextRequest
from .services import services

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("haathi")


@asynccontextmanager
async def lifespan(app: FastAPI):
    t0 = time.perf_counter()
    sv = services()
    sv.retriever()  # build indexes at start-up, not on the first request
    build_graph()
    log.info("Haathi ready: %d schemes, %d chunks, embedder=%s, reranker=%s, llm=%s (%.1fs)", len(sv.corpus.schemes),
             len(sv.corpus.chunks), sv.retriever().embedder.name, getattr(sv.retriever().reranker, "name", "off"),
             llm.available(), time.perf_counter() - t0)
    yield


app = FastAPI(title="Haathi API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ----------------------------------------------------------------------------------- metrics + cache
_lat_first: deque[float] = deque(maxlen=500)
_lat_full: deque[float] = deque(maxlen=500)
_cache: OrderedDict[str, list[dict]] = OrderedDict()
_cache_stats = {"hits": 0, "misses": 0}
CACHE_MAX = 256


def _pct(xs, p: float) -> float | None:
    if not xs:
        return None
    s = sorted(xs)
    return round(s[min(len(s) - 1, int(p * len(s)))], 1)


def _norm_q(q: str) -> str:
    return re.sub(r"[^\wऀ-ॿఀ-౿₹.]+", " ", q.lower()).strip()


def sse(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False, default=str)}\n\n"


# ----------------------------------------------------------------------------------- chat
@app.post("/api/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    state = {
        "query": req.message[:2000], "ui_lang": req.lang, "profile": {k: v.model_dump() for k, v in req.profile.items()},
        "pending": req.pending, "asked": req.asked, "focus": req.focus, "skip_questions": req.skip_questions,
        "overrides": {},
    }
    cacheable = not req.profile and not req.pending and not req.focus
    key = f"{req.lang}|{_norm_q(req.message)}"

    async def stream() -> AsyncIterator[str]:
        t0 = time.perf_counter()
        first = None
        if cacheable and key in _cache:
            _cache_stats["hits"] += 1
            _cache.move_to_end(key)
            for ev in _cache[key]:
                yield sse(ev)
            return
        if cacheable:
            _cache_stats["misses"] += 1
        recorded: list[dict] = []
        final: dict | None = None
        try:
            async for mode, chunk in build_graph().astream(state, stream_mode=["custom", "values"], config=langfuse_config()):
                if mode == "custom":
                    if chunk.get("type") == "token" and first is None:
                        first = time.perf_counter() - t0
                    recorded.append(chunk)
                    yield sse(chunk)
                else:
                    final = chunk
        except Exception as e:  # pragma: no cover - surfaced to the UI as the sleepy-elephant error state
            log.exception("chat failed")
            yield sse({"type": "error", "message": str(e)[:200]})
            return
        assert final is not None
        ans = final["answer"]
        done = {
            "type": "done", "lang": final["lang"], "intent": final["intent"],
            "text": ans["text"], "cards": ans["cards"], "citations": ans["citations"], "questions": ans.get("questions", []),
            "abstained": ans.get("abstained", False), "official_links": ans.get("official_links", []),
            "kind": ans.get("kind"), "disclaimer": ans.get("disclaimer"),
            "profile_updates": final.get("new_facts", []), "focus": final.get("mentions", []),
            "trace": {"info": final.get("info"), "english": final.get("english"), "translate": final.get("translate_method"),
                      "queries": final.get("queries"), "top_score": round(final.get("top_score", 0.0), 3),
                      "retries": final.get("retries", 0), "timings": final.get("timings"),
                      "removed_claims": ans.get("removed_claims", 0),
                      "passages": [{"id": h.chunk.id, "score": round(h.score, 3), "sources": h.sources}
                                   for h in (final.get("hits") or [])[:8]]},
        }
        recorded.append(done)
        yield sse(done)
        _lat_full.append((time.perf_counter() - t0) * 1000)
        if first is not None:
            _lat_first.append(first * 1000)
        if cacheable and not done["abstained"]:
            _cache[key] = recorded
            if len(_cache) > CACHE_MAX:
                _cache.popitem(last=False)

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/ask")
async def ask_baseline(req: AskRequest) -> StreamingResponse:
    """Baseline RAG (Prompt 1): dense-only retrieval, top 5, answer with numbered citations, streamed."""
    from .graph.nodes import GEN_PROMPT

    sv = services()
    retr = sv.retriever({"retrieval": "dense", "use_rerank": False})
    hits = retr.search([req.question], k=5)

    async def stream() -> AsyncIterator[str]:
        cites = [{"id": i + 1, "doc": h.chunk.doc_id, "page": h.chunk.page, "text": h.chunk.text} for i, h in enumerate(hits)]
        yield sse({"type": "stage", "stage": "retrieve", "count": len(hits)})
        text = None
        if llm.available():
            text = await llm.complete(GEN_PROMPT.format(lang_name="the same language as the question",
                                                        passages="\n".join(f"[{c['id']}] {c['text']}" for c in cites),
                                                        q=req.question))
        if not text:
            text = " ".join(f"{c['text'][:220]}… [{c['id']}]" for c in cites[:2])
        for w in re.split(r"(\s+)", text):
            if w:
                yield sse({"type": "token", "text": w})
        yield sse({"type": "done", "text": text, "citations": cites})

    return StreamingResponse(stream(), media_type="text/event-stream")


# ----------------------------------------------------------------------------------- eligibility
def _values(profile: dict) -> dict:
    return {k: (v["value"] if isinstance(v, dict) and "value" in v else v) for k, v in profile.items()}


def _scope(categories: list[str] | None):
    schemes = list(services().corpus.schemes.values())
    if categories:
        schemes = [s for s in schemes if set(s.categories) & set(categories)]
    return schemes


@app.post("/api/eligibility/evaluate")
async def eligibility_evaluate(req: EvaluateRequest) -> dict:
    cites = Citations(services().corpus)
    schemes = [services().corpus.schemes[i] for i in req.scheme_ids if i in services().corpus.schemes] if req.scheme_ids else _scope(req.categories)
    outs = evaluate_all(schemes, _values(req.profile))
    cards = [scheme_card(o, req.lang, cites) for o in outs]
    return {"cards": cards, "citations": cites.verified(),
            "counts": {s: sum(o.status == s for o in outs) for s in ("eligible", "maybe", "not_eligible")}}


@app.post("/api/eligibility/next")
async def eligibility_next(req: NextRequest) -> dict:
    """Step-by-step checker: returns the best next question (information gain) plus the current results."""
    profile = _values(req.profile)
    schemes = _scope(req.categories)
    ranked = rank_questions(profile, schemes, exclude=set(req.skipped))
    best = next((c for c in ranked if c.gain > 1e-6), None)
    outs = evaluate_all(schemes, profile)
    cites = Citations(services().corpus)
    done = best is None or len(req.asked) >= req.max_questions
    return {
        "question": None if done else spec_json(best.field, req.lang),
        "gain": None if done else round(best.gain, 4),
        "ranking": [{"field": c.field, "gain": round(c.gain, 4)} for c in ranked[:6]],
        "done": done,
        "counts": {s: sum(o.status == s for o in outs) for s in ("eligible", "maybe", "not_eligible")},
        "cards": [scheme_card(o, req.lang, cites) for o in outs if o.status != "not_eligible" or o.what_if],
        "citations": cites.verified(),
    }


@app.get("/api/fields")
async def fields(lang: str = "en") -> dict:
    return {"fields": [spec_json(f, lang) for f in FIXED_ORDER]}


# ----------------------------------------------------------------------------------- schemes + sources
@app.get("/api/schemes")
async def list_schemes(lang: str = "en") -> dict:
    cites = Citations(services().corpus)
    outs = [evaluate(s, {}) for s in services().corpus.schemes.values()]
    cards = [scheme_card(o, lang, cites) for o in outs]
    order = {"Telangana": 0, None: 1, "Andhra Pradesh": 2}
    cards.sort(key=lambda c: (order.get(c["state"], 3), c["name_en"]))
    return {"schemes": cards}


@app.post("/api/schemes/{scheme_id}")
async def scheme_detail(scheme_id: str, req: EvaluateRequest) -> dict:
    sc = services().corpus.schemes.get(scheme_id)
    if not sc:
        raise HTTPException(404, "unknown scheme")
    cites = Citations(services().corpus)
    card = scheme_card(evaluate(sc, _values(req.profile)), req.lang, cites)
    return {"card": card, "citations": cites.verified(), "disclaimer": DISCLAIMER[req.lang]}


@app.get("/api/sources/{doc_id}/page/{page_no}")
async def source_page(doc_id: str, page_no: int, quote: str | None = None) -> dict:
    doc = services().corpus.docs.get(doc_id)
    if not doc:
        raise HTTPException(404, "unknown document")
    try:
        page = doc.page(page_no)
    except StopIteration:
        raise HTTPException(404, "no such page")
    spans = locate_quote(page, quote) if quote else []
    sc = services().corpus.scheme_for_doc(doc_id)
    return {
        "doc_id": doc_id, "title": doc.title, "source_url": doc.source_url, "kind": doc.kind,
        "pages": [p.page for p in doc.pages], "page": page_no, "width": page.width, "height": page.height,
        "blocks": [{"id": b.id, "type": b.type, "font_size": b.font_size, "bbox": b.bbox,
                    "lines": [{"text": ln.text, "bbox": ln.bbox} for ln in b.lines]} for b in page.blocks],
        "highlights": spans, "highlight_bbox": union_bbox(spans),
        "scheme_id": sc.scheme_id if sc else None, "last_verified": sc.last_verified if sc else None,
        "file_url": f"/api/files/{doc_id}" if doc.kind == "pdf" and (get_settings().data_dir / "raw" / doc_id).exists() else None,
    }


@app.get("/api/files/{doc_id}")
async def source_file(doc_id: str) -> FileResponse:
    path = (get_settings().data_dir / "raw" / doc_id).resolve()
    if not str(path).startswith(str((get_settings().data_dir / "raw").resolve())) or not path.exists():
        raise HTTPException(404)
    return FileResponse(path)


# ----------------------------------------------------------------------------------- feedback, voice, meta
@app.post("/api/feedback")
async def feedback(req: FeedbackRequest) -> dict:
    p = get_settings().data_dir / "feedback.jsonl"
    rec = req.model_dump() | {"ts": datetime.now(timezone.utc).isoformat()}
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return {"ok": True}


@app.post("/api/asr")
async def asr(audio: UploadFile = File(...), lang: str = Form("te")) -> dict:
    """Speech-to-text via Gemini audio input. Browsers with Web Speech API transcribe on-device instead."""
    from .speech.asr import transcribe

    data = await audio.read()
    if len(data) > 8 * 1024 * 1024:
        raise HTTPException(413, "audio too long")
    text = await transcribe(data, audio.content_type or "audio/webm", lang)
    if text is None:
        raise HTTPException(501, "server ASR unavailable (set GEMINI_API_KEY)")
    return {"text": text, "engine": "gemini"}


# ----------------------------------------------------------------------------------- speech-test recorder (dev only)
_CLIP_LANGS = {"te", "hi", "en"}


def _clip_dir(lang: str):
    if get_settings().env == "production":
        raise HTTPException(403, "clip recording is disabled in production")
    if lang not in _CLIP_LANGS:
        raise HTTPException(400, "lang must be te, hi or en")
    d = get_settings().data_dir.parent / "eval" / "asr_clips" / lang
    d.mkdir(parents=True, exist_ok=True)
    return d


@app.get("/api/asr-clips")
async def asr_clips_list() -> dict:
    return {lang: sorted(int(p.stem[4:]) for p in _clip_dir(lang).glob("clip*.wav")) for lang in sorted(_CLIP_LANGS)}


@app.post("/api/asr-clips")
async def asr_clip_save(lang: str = Form(...), index: int = Form(...), text: str = Form(...),
                        audio: UploadFile = File(...)) -> dict:
    """Save one read-aloud clip for eval/asr_compare.py as clipNN.wav + clipNN.txt (the sentence that was read)."""
    d = _clip_dir(lang)
    if not 1 <= index <= 99:
        raise HTTPException(400, "index out of range")
    data = await audio.read()
    if len(data) > 6 * 1024 * 1024 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise HTTPException(400, "expected a WAV file under 6 MB")
    (d / f"clip{index:02d}.wav").write_bytes(data)
    (d / f"clip{index:02d}.txt").write_text(text.strip() + "\n", encoding="utf-8")
    return {"ok": True, "saved": f"eval/asr_clips/{lang}/clip{index:02d}.wav", "bytes": len(data)}


@app.get("/api/asr-clips/{lang}/{index}.wav")
async def asr_clip_get(lang: str, index: int) -> FileResponse:
    p = _clip_dir(lang) / f"clip{index:02d}.wav"
    if not p.exists():
        raise HTTPException(404)
    return FileResponse(p, media_type="audio/wav")


@app.websocket("/api/asr/live")
async def asr_live(ws: WebSocket) -> None:
    """Word-by-word dictation (see app/speech/live.py)."""
    from .speech.live import live_dictation

    await live_dictation(ws)


@app.get("/api/meta")
async def meta() -> dict:
    sv = services()
    r = sv.retriever()
    schemes = list(sv.corpus.schemes.values())
    return {
        "schemes": len(schemes), "documents": len(sv.corpus.docs), "chunks": len(sv.corpus.chunks),
        "states": sorted({s.state for s in schemes if s.state}), "central": sum(s.level == "central" for s in schemes),
        "last_verified": max(s.last_verified for s in schemes),
        "changed": sorted([{"scheme_id": s.scheme_id, "name": s.name.model_dump(), "changed_on": s.changed_on,
                            "note": s.change_note.model_dump() if s.change_note else None}
                           for s in schemes if s.changed_on], key=lambda x: x["changed_on"], reverse=True),
        "review": {k: sum(s.review_status == k for s in schemes) for k in ("seed", "pending", "approved", "edited")},
        "engine": {"embedder": r.embedder.name, "reranker": getattr(r.reranker, "name", "off"), "llm": llm.available(),
                   "retrieval": get_settings().retrieval, "crosslingual": get_settings().crosslingual},
        "fields": len(FIELDS),
        "env": get_settings().env,
    }


@app.get("/api/metrics")
async def metrics() -> dict:
    total = _cache_stats["hits"] + _cache_stats["misses"]
    return {
        "latency_ms": {"first_token_p50": _pct(_lat_first, 0.5), "first_token_p95": _pct(_lat_first, 0.95),
                       "full_p50": _pct(_lat_full, 0.5), "full_p95": _pct(_lat_full, 0.95), "n": len(_lat_full)},
        "cache": {**_cache_stats, "hit_rate": round(_cache_stats["hits"] / total, 3) if total else None, "size": len(_cache)},
        "llm": llm.stats(),
    }


@app.get("/api/health")
async def health() -> dict:
    return {"ok": True}


from admin.review import router as admin_router  # noqa: E402

app.include_router(admin_router)
