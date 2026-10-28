"""Rerankers: bge-reranker-v2-m3 (multilingual cross-encoder) or a lexical fallback. Scores are in [0, 1]."""
from __future__ import annotations

import logging
from functools import lru_cache

import numpy as np

from .tokenize import tokenize

log = logging.getLogger(__name__)


class LexicalReranker:
    name = "lexical"

    def __init__(self, embedder) -> None:
        self.embedder = embedder

    def score(self, query: str, passages: list[str]) -> list[float]:
        if not passages:
            return []
        q = set(tokenize(query))
        qd, _ = self.embedder.encode([query])
        pd, _ = self.embedder.encode(passages)
        cos = (pd @ qd[0]).tolist()
        out = []
        for p, c in zip(passages, cos):
            pt = set(tokenize(p))
            overlap = len(q & pt) / max(len(q), 1)
            out.append(float(np.clip(0.55 * overlap + 0.45 * c, 0, 1)))
        return out


class BGEReranker:  # pragma: no cover - needs the ml extra
    name = "bge-reranker-v2-m3"

    def __init__(self) -> None:
        from FlagEmbedding import FlagReranker

        from .embed import pick_device

        device = pick_device()
        self.model = FlagReranker("BAAI/bge-reranker-v2-m3", use_fp16=device != "cpu", devices=device)

    def score(self, query: str, passages: list[str]) -> list[float]:
        if not passages:
            return []
        s = self.model.compute_score([[query, p] for p in passages], normalize=True)
        return [float(x) for x in (s if isinstance(s, list) else [s])]


@lru_cache
def get_reranker(kind: str, embedder):
    if kind in ("auto", "bge"):
        try:
            return BGEReranker()
        except Exception as e:
            if kind == "bge":
                raise
            log.info("bge reranker unavailable (%s); using lexical reranker", type(e).__name__)
    return LexicalReranker(embedder)
