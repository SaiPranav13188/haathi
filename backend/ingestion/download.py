"""Polite downloader for official scheme documents (haathi.md §5).

Reads data/manifest.csv, respects robots.txt, waits between requests, identifies itself, and records URL,
download date and SHA-256 for every file in data/raw/manifest_state.json.
"""
from __future__ import annotations

import csv
import hashlib
import json
import logging
import time
import urllib.robotparser
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx
import truststore

from app.config import get_settings

# Many government sites omit intermediate certificates; the OS trust store (like a browser) handles them
truststore.inject_into_ssl()

log = logging.getLogger(__name__)
UA = "HaathiBot/0.1 (+https://github.com/; educational, non-commercial; contact via repo issues)"
DELAY_S = 3.0


def _robots_ok(url: str, cache: dict[str, urllib.robotparser.RobotFileParser]) -> bool:
    p = urlparse(url)
    base = f"{p.scheme}://{p.netloc}"
    if base not in cache:
        rp = urllib.robotparser.RobotFileParser()
        try:
            r = httpx.get(f"{base}/robots.txt", headers={"User-Agent": UA}, timeout=15, follow_redirects=True)
            rp.parse(r.text.splitlines() if r.status_code == 200 else [])
        except httpx.HTTPError:
            rp.parse([])
        cache[base] = rp
    return cache[base].can_fetch(UA, url)


def read_manifest(path: Path | None = None) -> list[dict]:
    path = path or get_settings().data_dir / "manifest.csv"
    with path.open(encoding="utf-8") as f:
        return [row for row in csv.DictReader(f) if row.get("url")]


def download_all(only: set[str] | None = None) -> dict:
    s = get_settings()
    raw = s.data_dir / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    state_path = raw / "manifest_state.json"
    state: dict = json.loads(state_path.read_text()) if state_path.exists() else {}
    robots: dict = {}
    with httpx.Client(headers={"User-Agent": UA}, timeout=60, follow_redirects=True) as client:
        for row in read_manifest():
            sid, url = row["scheme_id"], row["url"]
            if only and sid not in only:
                continue
            if row.get("doc_type", "pdf") not in {"pdf", "html"}:
                continue  # "portal" rows are homepages, not guideline documents; nothing useful to extract
            if not _robots_ok(url, robots):
                log.warning("robots.txt disallows %s; skipping", url)
                state[sid] = {**state.get(sid, {}), "url": url, "status": "robots_disallowed"}
                continue
            try:
                r = client.get(url)
                r.raise_for_status()
            except httpx.HTTPError as e:
                log.warning("download failed %s: %s", url, e)
                state[sid] = {**state.get(sid, {}), "url": url, "status": f"error: {type(e).__name__}"}
                time.sleep(DELAY_S)
                continue
            ext = ".pdf" if "pdf" in r.headers.get("content-type", "") or url.lower().endswith(".pdf") else ".html"
            path = raw / f"{sid}{ext}"
            digest = hashlib.sha256(r.content).hexdigest()
            prev = state.get(sid, {})
            path.write_bytes(r.content)
            state[sid] = {"url": url, "file": path.name, "sha256": digest, "status": "ok",
                          "downloaded_at": datetime.now(timezone.utc).isoformat(),
                          "changed": bool(prev.get("sha256") and prev["sha256"] != digest), "previous_sha256": prev.get("sha256")}
            log.info("saved %s (%d bytes)", path.name, len(r.content))
            time.sleep(DELAY_S)
    state_path.write_text(json.dumps(state, indent=2))
    return state
