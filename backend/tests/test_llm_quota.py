import asyncio

from app import llm

DAY = ("429 RESOURCE_EXHAUSTED. {'quotaId': 'GenerateRequestsPerDayPerProjectPerModel-FreeTier'}, "
       "{'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '7990s'}")
MINUTE = "429 RESOURCE_EXHAUSTED. quotaId GenerateRequestsPerMinutePerProjectPerModel-FreeTier. Please retry in 9.79s."


def test_quota_kind_and_delay():
    assert llm.quota_kind(DAY) == "day" and llm._retry_seconds(DAY) == 7990
    assert llm.quota_kind(MINUTE) == "minute" and abs(llm._retry_seconds(MINUTE) - 9.79) < 0.01
    assert llm.quota_kind("500 internal") is None
    assert llm._retry_seconds("Please retry in 2h13m8.5s.") == 2 * 3600 + 13 * 60 + 8.5


def test_daily_quota_parks_model(monkeypatch):
    calls = []

    async def fake(model, *a):
        calls.append(model)
        raise RuntimeError(DAY)

    monkeypatch.setattr(llm, "_gemini", fake)
    monkeypatch.setattr(llm, "_blocked_until", {})
    monkeypatch.setattr(llm, "_last_call", {})
    assert asyncio.run(llm._gemini_with_quota("m-test", "p", None, False, 0.2, None)) is None
    assert asyncio.run(llm._gemini_with_quota("m-test", "p", None, False, 0.2, None)) is None
    assert calls == ["m-test"]  # second call skipped without hitting the API


def test_minute_limit_does_not_make_chat_wait(monkeypatch):
    """A per-minute 429 with a long retry delay must fall back immediately, not sleep for a minute."""
    import time as _t

    async def fake(model, *a):
        raise RuntimeError("429 RESOURCE_EXHAUSTED quotaId GenerateRequestsPerMinutePerProjectPerModel-FreeTier. Please retry in 40s.")

    monkeypatch.setattr(llm, "_gemini", fake)
    monkeypatch.setattr(llm, "_blocked_until", {})
    monkeypatch.setattr(llm, "_recent", {})
    t0 = _t.time()
    assert asyncio.run(llm._gemini_with_quota("m-minute", "p", None, False, 0.2, None)) is None
    assert _t.time() - t0 < 1.0
    assert not llm._usable("m-minute")  # parked until the minute passes


def test_bursts_are_not_spaced_out(monkeypatch):
    async def ok(model, *a):
        return "x"

    monkeypatch.setattr(llm, "_gemini", ok)
    monkeypatch.setattr(llm, "_recent", {})
    monkeypatch.setattr(llm, "_blocked_until", {})
    import time as _t
    t0 = _t.time()
    for _ in range(5):
        assert asyncio.run(llm._gemini_with_quota("m-burst", "p", None, False, 0.2, None)) == "x"
    assert _t.time() - t0 < 1.0


def test_slow_gemini_times_out_and_cools_down(monkeypatch):
    """Live chat must not wait on a slow Gemini: time out, then skip Gemini for the cool-down."""
    from app.config import get_settings

    calls = []

    async def slow(model, *a):
        calls.append(model)
        await asyncio.sleep(5)
        return "late"

    monkeypatch.setattr(llm, "_gemini", slow)
    monkeypatch.setattr(llm, "_blocked_until", {})
    monkeypatch.setattr(llm, "_recent", {})
    monkeypatch.setattr(get_settings(), "gemini_timeout_s", 0.2)
    import time as _t
    t0 = _t.time()
    assert asyncio.run(llm._gemini_with_quota("m-slow", "p", None, False, 0.2, None)) is None
    assert _t.time() - t0 < 1.0
    assert asyncio.run(llm._gemini_with_quota("m-slow", "p", None, False, 0.2, None)) is None
    assert calls == ["m-slow"]  # second call skipped during the cool-down
