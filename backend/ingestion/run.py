"""`make ingest`: (optionally download) → parse → chunk + contextualize → embed/index → extract rules.

    uv run python -m ingestion.run              # seed corpus + anything already in data/raw
    uv run python -m ingestion.run --download   # fetch official docs from data/manifest.csv first
"""
from __future__ import annotations

import argparse
import json
import logging
import time

from app.config import get_settings

log = logging.getLogger("ingest")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--download", action="store_true", help="download official documents from the manifest first")
    ap.add_argument("--extract", action="store_true", help="run LLM rule extraction on downloaded docs")
    ap.add_argument("--extract-only", action="store_true", help="skip download/parse/index; only extract rules from parsed docs")
    args = ap.parse_args()
    s = get_settings()
    t0 = time.perf_counter()
    if args.extract_only:
        args.extract = True
    if args.download and not args.extract_only:
        from .download import download_all

        state = download_all()
        log.info("downloaded: %s", {k: v.get("status") for k, v in state.items()})

    from .parse import parse_any, save

    parsed = s.index_dir / "parsed"
    n = 0
    for base in [] if args.extract_only else (s.data_dir / "seed" / "docs", s.data_dir / "raw"):
        if not base.exists():
            continue
        for p in sorted(base.iterdir()):
            if p.suffix.lower() not in {".md", ".pdf", ".html"}:
                continue
            try:
                save(parse_any(p), parsed)
                n += 1
            except ImportError:
                log.warning("Docling not installed (uv sync --extra ml); skipping %s", p.name)
    log.info("parsed %d documents", n)

    from app.corpus import Corpus
    from app.retrieval.pipeline import Retriever

    for chunking in () if args.extract_only else ("structure", "fixed"):
        for contextual in (True, False):
            c = Corpus(chunking=chunking, contextual=contextual)
            Retriever(c.chunks, s)  # builds + caches embeddings, BM25, Qdrant collection
            log.info("indexed %s/%s: %d chunks", chunking, "ctx" if contextual else "plain", len(c.chunks))
            (s.index_dir / f"chunks_{chunking}_{'ctx' if contextual else 'plain'}.jsonl").write_text(
                "\n".join(json.dumps(ch.to_json(), ensure_ascii=False) for ch in c.chunks))

    if args.extract:
        from .download import read_manifest
        from .extract_rules import extract
        from .parse import ParsedDoc

        state = {}
        # documents fetched by download.py, plus G.O.s fetched from goir.telangana.gov.in
        for name in ("manifest_state.json", "goir_state.json"):
            p = s.data_dir / "raw" / name
            if p.exists():
                for sid, st in json.loads(p.read_text()).items():
                    state[sid] = {**st, "status": st.get("status", "ok"), "url": st.get("url", st.get("source", ""))}
        meta = {r["scheme_id"]: r for r in read_manifest()}
        for sid, st in state.items():
            if st.get("status") != "ok":
                continue
            pj = parsed / f"{st['file']}.json"
            if pj.exists():
                extract(ParsedDoc.from_json(json.loads(pj.read_text())), f"{sid}_extracted", {**meta.get(sid, {}), **st})
    log.info("ingest done in %.1fs", time.perf_counter() - t0)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    main()
