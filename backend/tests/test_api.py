import json

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def events(resp):
    return [json.loads(line[6:]) for line in resp.text.splitlines() if line.startswith("data: ")]


def test_chat_streams_stage_events_then_done(client):
    r = client.post("/api/chat", json={"message": "నేను తెలంగాణలో రైతుని, 2 ఎకరాల భూమి ఉంది", "lang": "te"})
    ev = events(r)
    stages = [e["stage"] for e in ev if e["type"] == "stage"]
    assert stages[:4] == ["understand", "decompose", "retrieve", "rerank"]
    assert any(e["type"] == "token" for e in ev)
    done = ev[-1]
    assert done["type"] == "done" and done["lang"] == "te"
    assert {f["field"] for f in done["profile_updates"]} >= {"state", "occupation", "land_acres"}
    assert done["questions"], "should ask the best next question"
    assert done["disclaimer"]


def test_followup_reaches_results(client):
    profile = {"state": {"value": "Telangana"}, "occupation": {"value": "farmer"}, "land_acres": {"value": 2}}
    r = client.post("/api/chat", json={"message": "45, yes", "lang": "en", "profile": profile,
                                       "pending": ["age", "has_bank_account"], "asked": ["age", "has_bank_account"],
                                       "skip_questions": True})
    done = events(r)[-1]
    assert done["kind"] == "eligible"
    ids = {c["scheme_id"] for c in done["cards"] if c["status"] == "eligible"}
    assert "ts_rythu_bharosa" in ids
    assert all(c["status"] in {"supported", "unclear"} for c in done["citations"])


def test_offtopic_abstains(client):
    done = events(client.post("/api/chat", json={"message": "Who won the football world cup in 2018?", "lang": "en"}))[-1]
    assert done["abstained"] and done["official_links"]


def test_renamed_scheme_freshness(client):
    done = events(client.post("/api/chat", json={"message": "how much does rythu bandhu give", "lang": "en"}))[-1]
    assert "Rythu Bharosa" in done["text"] and "2025-01-26" in done["text"]


def test_next_question_endpoint(client):
    r = client.post("/api/eligibility/next", json={"profile": {"state": "Telangana"}, "lang": "hi"}).json()
    assert r["question"]["field"] != "state" and r["question"]["question"]
    assert r["ranking"][0]["gain"] >= r["ranking"][-1]["gain"]


def test_source_page_highlight(client):
    q = "Investment support of ₹12,000 per acre per year"
    r = client.get("/api/sources/ts_rythu_bharosa.md/page/2", params={"quote": q}).json()
    assert r["highlights"] and r["highlight_bbox"]


def test_privacy_masks_ids(client):
    r = client.post("/api/chat", json={"message": "my aadhaar is 1234 5678 9012", "lang": "en"})
    assert "1234 5678 9012" not in r.text


def test_meta_and_metrics(client):
    m = client.get("/api/meta").json()
    assert m["schemes"] >= 30 and "Telangana" in m["states"]
    assert "cache" in client.get("/api/metrics").json()


def test_admin_pages(client):
    assert client.get("/admin").status_code == 200
    assert "Rythu Bharosa" in client.get("/admin/ts_rythu_bharosa").text


def test_show_results_now_uses_profile(client):
    profile = {"state": {"value": "Telangana"}, "gender": {"value": "female"}, "has_ration_card": {"value": True}}
    done = events(client.post("/api/chat", json={"message": "Show results now", "lang": "en", "profile": profile,
                                                 "skip_questions": True}))[-1]
    assert not done["abstained"] and done["kind"] == "eligible"
    assert "ts_mahalakshmi_bus" in {c["scheme_id"] for c in done["cards"] if c["status"] == "eligible"}


def test_asr_clip_recorder_roundtrip(client, tmp_path, monkeypatch):
    import struct

    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "data_dir", tmp_path / "data")
    pcm = b"\x00\x00" * 1600
    wav = (b"RIFF" + struct.pack("<I", 36 + len(pcm)) + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 1, 1, 16000, 32000, 2, 16)
           + b"data" + struct.pack("<I", len(pcm)) + pcm)
    r = client.post("/api/asr-clips", data={"lang": "te", "index": "3", "text": "నేను రైతుని"},
                    files={"audio": ("c.wav", wav, "audio/wav")})
    assert r.status_code == 200
    assert (tmp_path / "eval" / "asr_clips" / "te" / "clip03.txt").read_text(encoding="utf-8").strip() == "నేను రైతుని"
    assert client.get("/api/asr-clips").json()["te"] == [3]
    assert client.post("/api/asr-clips", data={"lang": "te", "index": "4", "text": "x"},
                       files={"audio": ("c.webm", b"not a wav", "audio/webm")}).status_code == 400


def test_what_if_only_when_change_makes_eligible(client):
    msg = "I am a BC family in a village in Telangana, income 1.8 lakh, my daughter is getting married"
    done = events(client.post("/api/chat", json={"message": msg, "lang": "en", "skip_questions": True}))[-1]
    assert "Kalyana Lakshmi if your family yearly income were ₹1,50,000 or less" in done["text"]
    assert "Aasara" not in done["text"]  # age unknown: lowering income alone would not make them eligible


def test_live_dictation_without_key_reports_error(client):
    # tests run without a Gemini key: the socket must say so instead of hanging
    with client.websocket_connect("/api/asr/live") as ws:
        assert ws.receive_json() == {"type": "error", "reason": "no-llm"}


def test_numpy_store_matches_qdrant():
    """The compact store for small servers must rank exactly like Qdrant."""
    from app.config import get_settings
    from app.corpus import get_corpus
    from app.retrieval.pipeline import Retriever

    chunks = get_corpus().chunks
    s = get_settings()
    a = Retriever(chunks, s, vector_store="qdrant-memory")
    b = Retriever(chunks, s, vector_store="numpy")
    for q in ["రైతు భరోసా ఎంత", "documents for Kalyana Lakshmi", "pension for elderly"]:
        assert a._dense(q, 10) == b._dense(q, 10)
        # sparse scores are identical; only passages with exactly tied scores may swap places at the cut-off
        assert a._sparse(q, 10)[0] == b._sparse(q, 10)[0]
        x, y = a._sparse(q, 10), b._sparse(q, 10)
        assert len(x) == len(y) and len(set(x) & set(y)) >= min(8, len(x))
