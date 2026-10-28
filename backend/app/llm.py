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


_recent: dict[str, list[float]] = {}


async def _paced(model: str) -> bool:
    """Sliding-window limiter: bursts are fine; only when `gemini_rpm` calls happened in the last 60 s do we wait,
    and never longer than `gemini_max_wait_s` (returns False = skip the LLM this time)."""
    lock = _pace_locks.setdefault(model, asyncio.Lock())
    s = get_settings()
    async with lock:
        now = time.time()
        window = [t for t in _recent.get(model, []) if now - t < 60.0]
        if len(window) >= max(s.gemini_rpm, 1):
            wait = 60.0 - (now - window[0])
            if wait > s.gemini_max_wait_s:
                _stats["quota_skips"] += 1
                return False
            await asyncio.sleep(wait)
            window = window[1:]
        window.append(time.time())
        _recent[model] = window
        _last_call[model] = time.time()
        return True


async def _gemini_with_quota(model: str, *args) -> str | None:
    for attempt in range(2):
        if not _usable(model):
            _stats["quota_skips"] += 1
            return None
        if not await _paced(model):
            return None
        s = get_settings()
        try:
            return await asyncio.wait_for(_gemini(model, *args), timeout=s.gemini_timeout_s)
        except asyncio.TimeoutError:
            # Gemini is slow right now: don't make people wait, use built-in answers for a short while
            _stats["timeouts"] = _stats.get("timeouts", 0) + 1
            for m in {model, *_models()}:
                _blocked_until[m] = max(_blocked_until.get(m, 0.0), time.time() + s.gemini_cooldown_s)
            _warn_once(model, "slow", f"Gemini {model} took over {s.gemini_timeout_s:.0f}s; using built-in answers for {s.gemini_cooldown_s:.0f}s")
            return None
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
            if "503" in msg or "UNAVAILABLE" in msg:  # overloaded ("high demand"): try the other model, then cool down
                _blocked_until[model] = time.time() + get_settings().gemini_cooldown_s
                _warn_once(model, "busy", f"Gemini {model} is overloaded; skipping it for {get_settings().gemini_cooldown_s:.0f}s")
                return None
            if kind == "minute":
                delay = _retry_seconds(msg)
                if attempt == 0 and delay <= get_settings().gemini_max_wait_s:
                    await asyncio.sleep(delay)
                    continue
                # don't make a person wait: park this model briefly and fall back to built-in answers
                _blocked_until[model] = time.time() + min(delay, 65.0)
                _warn_once(model, "minute", f"Gemini {model}: per-minute limit hit; using built-in answers for {delay:.0f}s")
                return None
            _warn_once(model, "error", f"Gemini {model} failed: {msg[:160]}")
            return None
    return None


def stats() -> dict:
    now = time.time()
    avg = round(_stats.get("ms_total", 0) / _stats["calls"]) if _stats["calls"] else None
    return {**_stats, "ms_avg_per_call": avg, "blocked_models": {m: round((t - now) / 60) for m, t in _blocked_until.items() if t > now}}


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


_clients: dict[int, object] = {}


def _client():
    """One Gemini client per event loop, reused across requests (a new client per call means a fresh TLS
    connection each time, which is very slow on small servers)."""
    from google import genai
    from google.genai import types

    loop = id(asyncio.get_running_loop())
    if loop not in _clients:
        s = get_settings()
        transport = httpx.AsyncHTTPTransport(local_address="0.0.0.0", retries=1) if s.gemini_force_ipv4 else None
        ac = httpx.AsyncClient(transport=transport, timeout=httpx.Timeout(60.0, connect=10.0))
        _clients.clear()  # old loops are gone (batch scripts call asyncio.run repeatedly)
        _clients[loop] = genai.Client(api_key=s.gemini_api_key, http_options=types.HttpOptions(httpx_async_client=ac))
    return _clients[loop]


async def _gemini(model: str, prompt: str, system: str | None, json_mode: bool, temperature: float,
                  audio: tuple[bytes, str] | None) -> str:
    from google.genai import types

    client = _client()
    t0 = time.perf_counter()
    contents: list = [prompt]
    if audio:
        contents = [types.Part.from_bytes(data=audio[0], mime_type=audio[1]), prompt]
    cfg = types.GenerateContentConfig(
        system_instruction=system, temperature=temperature,
        response_mime_type="application/json" if json_mode else None,
    )
    _stats["calls"] += 1
    resp = await client.aio.models.generate_content(model=model, contents=contents, config=cfg)
    _stats["ms_total"] = _stats.get("ms_total", 0) + (time.perf_counter() - t0) * 1000
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
