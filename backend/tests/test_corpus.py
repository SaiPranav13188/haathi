"""The rule DB must be traceable: every rule quote exists verbatim on its cited page and gets a bbox."""
from app.corpus import get_corpus


def test_all_schemes_load():
    c = get_corpus()
    assert len(c.schemes) >= 30
    assert sum(s.state == "Telangana" for s in c.schemes.values()) >= 10


def test_every_rule_quote_is_located_with_bbox():
    c = get_corpus()
    for s in c.schemes.values():
        for src in [r.source for r in s.rules] + [s.benefit.source, s.how_to_apply.source]:
            page = c.docs[src.doc].page(src.page)
            assert " ".join(src.quote.split()) in " ".join(page.text.split()), (s.scheme_id, src.quote)
            assert src.bbox is not None, (s.scheme_id, src.quote)


def test_bboxes_inside_page():
    c = get_corpus()
    for d in c.docs.values():
        for p in d.pages:
            for b in p.blocks:
                assert 0 <= b.bbox[0] < b.bbox[2] <= p.width
                assert 0 <= b.bbox[1] < b.bbox[3] <= p.height, (d.doc_id, b.id)


def test_mentions_and_renamed():
    c = get_corpus()
    hits = dict(c.find_mentions("Is Rythu Bandhu still there?"))
    assert "ts_rythu_bharosa" in hits and hits["ts_rythu_bharosa"] == "rythu bandhu"
    assert "pm_kisan" in dict(c.find_mentions("పీఎం-కిసాన్ ఎంత వస్తుంది"))


def test_chunk_order_is_deterministic_across_processes():
    """The embedding cache key depends on chunk order; it must not change with Python's hash seed."""
    import os
    import subprocess
    import sys

    code = ("import hashlib; from app.corpus import Corpus; "
            "print(hashlib.sha1('|'.join(c.id for c in Corpus().chunks).encode()).hexdigest())")
    keys = {subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True,
                           env={**os.environ, "PYTHONHASHSEED": seed}).stdout.strip() for seed in ("1", "2", "3")}
    assert len(keys) == 1
