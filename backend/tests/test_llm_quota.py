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
