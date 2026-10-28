"""LLM access: Gemini (free tier) with a fallback Gemini model, then local Ollama, then None.

Callers must handle `None` (no LLM configured or all providers rate-limited): every pipeline step has a
deterministic fallback, so Haathi still works offline and at ₹0 without any key.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
from pathlib import Path

import httpx

from .config import get_settings

log = logging.getLogger(__name__)
_sem = asyncio.Semaphore(4)  # simple queue: at most 4 concurrent LLM calls
_stats = {"calls": 0, "cache_hits": 0, "fallbacks": 0, "errors": 0, "tokens_in": 0, "tokens_out": 0, "quota_skips": 0}

# Free-tier quota handling: pace requests per model, and park a model whose daily quota is used up.
_blocked_until: dict[str, float] = {}
_last_call: dict[str, float] = {}
_pace_locks: dict[str, asyncio.Lock] = {}
_warned: set[tuple[str, str]] = set()


def _models() -> list[str]:
    s = get_settings()
    return [m for m in dict.fromkeys((s.gemini_model, s.gemini_fallback_model)) if m]


def _usable(model: str) -> bool:
    return _blocked_until.get(model, 0.0) <= time.time()


def available() -> bool:
    s = get_settings()
    return bool((s.gemini_api_key and any(_usable(m) for m in _models())) or s.ollama_url)


def _retry_seconds(msg: str) -> float:
    m = re.search(r"retryDelay'?\"?:\s*'?\"?(\d+(?:\.\d+)?)s", msg)
    if m:
        return float(m.group(1))
    m = re.search(r"retry in (?:(\d+)h)?(?:(\d+)m)?(\d+(?:\.\d+)?)s", msg)
    if m:
        h, mi, se = m.groups()
        return int(h or 0) * 3600 + int(mi or 0) * 60 + float(se)
    return 60.0


def quota_kind(msg: str) -> str | None:
    """'day' for a used-up daily quota, 'minute' for a per-minute limit, None for other errors."""
    if "RESOURCE_EXHAUSTED" not in msg and "429" not in msg:
        return None
    return "day" if "PerDay" in msg or "per day" in msg else "minute"


def _warn_once(model: str, kind: str, text: str) -> None:
    if (model, kind) not in _warned:
        _warned.add((model, kind))
        log.warning(text)


async def _paced(model: str):
    lock = _pace_locks.setdefault(model, asyncio.Lock())
    async with lock:
        gap = 60.0 / max(get_settings().gemini_rpm, 1)
        wait = _last_call.get(model, 0.0) + gap - time.time()
        if wait > 0:
            await asyncio.sleep(wait)
        _last_call[model] = time.time()


async def _gemini_with_quota(model: str, *args) -> str | None:
    for attempt in range(2):
        if not _usable(model):
            _stats["quota_skips"] += 1
            return None
        await _paced(model)
        try:
            return await _gemini(model, *args)
        except Exception as e:
            msg = str(e)
            kind = quota_kind(msg)
            _stats["errors"] += 1
            if kind == "day":
                delay = _retry_seconds(msg)
                _blocked_until[model] = time.time() + delay
                _warn_once(model, "day", f"Gemini {model}: free daily quota used up; skipping it for "
                                         f"{delay / 3600:.1f} h (Haathi keeps working with built-in answers)")
                return None
            if kind == "minute" and attempt == 0:
                delay = min(_retry_seconds(msg), 65.0)
                _warn_once(model, "minute", f"Gemini {model}: per-minute limit hit; waiting {delay:.0f}s and pacing requests")
                await asyncio.sleep(delay)
                continue
            _warn_once(model, "error", f"Gemini {model} failed: {msg[:160]}")
            return None
    return None


def stats() -> dict:
    now = time.time()
    return {**_stats, "blocked_models": {m: round((t - now) / 60) for m, t in _blocked_until.items() if t > now}}


def _cache_path(key: str) -> Path:
    d = get_settings().cache_dir / "llm"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{key}.json"


def _key(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()[:32]


async def complete(prompt: str, system: str | None = None, json_mode: bool = False, cache: bool = True,
                   temperature: float = 0.2, audio: tuple[bytes, str] | None = None) -> str | None:
    s = get_settings()
    key = _key(system or "", prompt, str(json_mode), str(temperature), hashlib.sha256(audio[0]).hexdigest() if audio else "")
    cp = _cache_path(key)
    if cache and cp.exists():
        _stats["cache_hits"] += 1
        return json.loads(cp.read_text())["text"]
    text = None
    async with _sem:
        if s.gemini_api_key:
            for i, model in enumerate(_models()):
                text = await _gemini_with_quota(model, prompt, system, json_mode, temperature, audio)
                if text is not None:
                    if i:
                        _stats["fallbacks"] += 1
                    break
        if text is None and s.ollama_url and audio is None:
            try:
                text = await _ollama(prompt, system, json_mode, temperature)
                _stats["fallbacks"] += 1
            except Exception as e:
                _stats["errors"] += 1
                _warn_once("ollama", "error", f"Ollama failed: {e}")
    if text is not None and cache:
        cp.write_text(json.dumps({"text": text, "t": time.time()}))
    return text


async def complete_json(prompt: str, system: str | None = None, **kw) -> dict | list | None:
    text = await complete(prompt, system, json_mode=True, **kw)
    if text is None:
        return None
    m = re.search(r"[\[{].*[\]}]", text, re.S)
    try:
        return json.loads(m.group(0) if m else text)
    except json.JSONDecodeError:
        log.warning("LLM returned invalid JSON: %s", text[:200])
        return None


async def _gemini(model: str, prompt: str, system: str | None, json_mode: bool, temperature: float,
                  audio: tuple[bytes, str] | None) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=get_settings().gemini_api_key)
    contents: list = [prompt]
    if audio:
        contents = [types.Part.from_bytes(data=audio[0], mime_type=audio[1]), prompt]
    cfg = types.GenerateContentConfig(
        system_instruction=system, temperature=temperature,
        response_mime_type="application/json" if json_mode else None,
    )
    _stats["calls"] += 1
    resp = await client.aio.models.generate_content(model=model, contents=contents, config=cfg)
    um = getattr(resp, "usage_metadata", None)
    if um:
        _stats["tokens_in"] += um.prompt_token_count or 0
        _stats["tokens_out"] += um.candidates_token_count or 0
    if not resp.text:
        raise RuntimeError("empty response")
    return resp.text


async def _ollama(prompt: str, system: str | None, json_mode: bool, temperature: float) -> str:
    s = get_settings()
    body = {"model": s.ollama_model, "prompt": prompt, "system": system or "", "stream": False,
            "options": {"temperature": temperature}}
    if json_mode:
        body["format"] = "json"
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(f"{s.ollama_url.rstrip('/')}/api/generate", json=body)
        r.raise_for_status()
        _stats["calls"] += 1
        return r.json()["response"]


def run_sync(coro):
    """Run an async LLM call from sync code (ingestion scripts)."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    coro.close()  # don't leave an un-awaited coroutine behind
    raise RuntimeError("run_sync called inside an event loop")
