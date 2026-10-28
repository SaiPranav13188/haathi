"""Process-wide singletons: corpus and retrievers (one per ablation configuration)."""
from __future__ import annotations

import json
import threading
from functools import lru_cache

from .config import get_settings
from .corpus import Corpus, get_corpus
from .retrieval.pipeline import Retriever

_RETRIEVER_KEYS = {"retrieval", "use_sparse", "use_rerank", "contextual", "chunking", "embedder", "reranker", "top_k", "rerank_keep"}


class Services:
    def __init__(self) -> None:
        self.corpus: Corpus = get_corpus()
        self._retrievers: dict[str, Retriever] = {}
        self._corpora: dict[str, Corpus] = {}
        self._lock = threading.Lock()

    def retriever(self, overrides: dict | None = None) -> Retriever:
        ov = {k: v for k, v in (overrides or {}).items() if k in _RETRIEVER_KEYS}
        key = json.dumps(ov, sort_keys=True)
        with self._lock:
            if key not in self._retrievers:
                corpus = self.corpus
                if "chunking" in ov or "contextual" in ov:
                    ck = f"{ov.get('chunking')}-{ov.get('contextual')}"
                    if ck not in self._corpora:
                        self._corpora[ck] = Corpus(chunking=ov.get("chunking"), contextual=ov.get("contextual"))
                    corpus = self._corpora[ck]
                self._retrievers[key] = Retriever(corpus.chunks, get_settings(), **ov)
            return self._retrievers[key]


@lru_cache
def services() -> Services:
    return Services()
