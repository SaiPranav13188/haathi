"""Hybrid retrieval: BM25 + dense + sparse (Qdrant), fused with RRF, then reranked. Every stage is a flag."""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field

import bm25s
import numpy as np
from qdrant_client import QdrantClient, models

from ingestion.chunk import Chunk

from ..config import Settings, get_settings
from .embed import get_embedder
from .fusion import rrf
from .rerank import get_reranker
from .tokenize import tokenize

log = logging.getLogger(__name__)
COLLECTION = "haathi_chunks"


@dataclass
class Hit:
    chunk: Chunk
    fused: float
    rerank: float | None = None
    sources: dict[str, int] = field(default_factory=dict)  # which retriever ranked it, and where

    @property
    def score(self) -> float:
        return self.rerank if self.rerank is not None else self.fused


class Retriever:
    def __init__(self, chunks: list[Chunk], settings: Settings | None = None, **overrides):
        base = settings or get_settings()
        self.s = base.model_copy(update=overrides) if overrides else base
        self.chunks = chunks
        self.by_id = {c.id: c for c in chunks}
        self.embedder = get_embedder(self.s.embedder)
        self.reranker = get_reranker(self.s.reranker, self.embedder) if self.s.use_rerank else None
        self._build_bm25()
        self._build_vectors()

    # ------------------------------------------------------------------ indexes
    def _build_bm25(self) -> None:
        self.bm25 = bm25s.BM25()
        corpus = [tokenize(c.index_text) or ["_"] for c in self.chunks]
        self.bm25.index(corpus, show_progress=False)
        self.vocab = set(t for doc in corpus for t in doc)

    def _emb_cache(self) -> tuple[np.ndarray, list[dict[int, float]]]:
        texts = [c.index_text for c in self.chunks]
        digest = hashlib.sha1("\x1e".join(texts).encode()).hexdigest()[:12]
        path = self.s.index_dir / f"emb_{self.embedder.name}_{digest}.npz"
        if path.exists():
            z = np.load(path, allow_pickle=True)
            return z["dense"], list(z["sparse"])
        dense, sparse = self.embedder.encode(texts)
        self.s.index_dir.mkdir(parents=True, exist_ok=True)
        np.savez(path, dense=dense, sparse=np.array(sparse, dtype=object))
        return dense, sparse

    def _build_vectors(self) -> None:
        dense, sparse = self._emb_cache()
        if self.s.vector_store == "qdrant-server":
            self.q = QdrantClient(url=self.s.qdrant_url)
        else:
            self.q = QdrantClient(":memory:")
        if self.q.collection_exists(COLLECTION):
            self.q.delete_collection(COLLECTION)
        self.q.create_collection(
            COLLECTION,
            vectors_config={"dense": models.VectorParams(size=dense.shape[1], distance=models.Distance.COSINE)},
            sparse_vectors_config={"sparse": models.SparseVectorParams()},
        )
        points = []
        for i, (c, d, sp) in enumerate(zip(self.chunks, dense, sparse)):
            vec: dict = {"dense": d.tolist()}
            if sp:
                vec["sparse"] = models.SparseVector(indices=list(sp.keys()), values=list(sp.values()))
            points.append(models.PointStruct(id=i, vector=vec, payload={"cid": c.id, "scheme_id": c.scheme_id}))
        self.q.upsert(COLLECTION, points)

    # ------------------------------------------------------------------ search
    def _dense(self, query: str, k: int) -> list[str]:
        d, _ = self.embedder.encode([query])
        res = self.q.query_points(COLLECTION, query=d[0].tolist(), using="dense", limit=k).points
        return [p.payload["cid"] for p in res]

    def _sparse(self, query: str, k: int) -> list[str]:
        _, sp = self.embedder.encode([query])
        if not sp[0]:
            return []
        res = self.q.query_points(COLLECTION, query=models.SparseVector(indices=list(sp[0].keys()), values=list(sp[0].values())),
                                  using="sparse", limit=k).points
        return [p.payload["cid"] for p in res]

    def _bm25(self, query: str, k: int) -> list[str]:
        toks = [t for t in tokenize(query) if t in self.vocab]
        if not toks:
            return []
        docs, scores = self.bm25.retrieve([toks], k=min(k, len(self.chunks)), show_progress=False)
        return [self.chunks[int(i)].id for i, sc in zip(docs[0], scores[0]) if sc > 0]

    def search(self, queries: list[str], k: int | None = None) -> list[Hit]:
        k = k or self.s.top_k
        rankings: list[list[str]] = []
        provenance: dict[str, dict[str, int]] = {}
        for q in queries:
            if not q.strip():
                continue
            runs = {}
            if self.s.retrieval in ("dense", "hybrid"):
                runs["dense"] = self._dense(q, k)
            if self.s.retrieval == "hybrid" and self.s.use_sparse:
                runs["sparse"] = self._sparse(q, k)
            if self.s.retrieval in ("bm25", "hybrid"):
                runs["bm25"] = self._bm25(q, k)
            for name, r in runs.items():
                rankings.append(r)
                for rank, cid in enumerate(r):
                    provenance.setdefault(cid, {}).setdefault(name, rank + 1)
        fused = rrf(rankings)[:k]
        return [Hit(self.by_id[cid], score, sources=provenance.get(cid, {})) for cid, score in fused]

    def rerank(self, query: str | list[str], hits: list[Hit], keep: int | None = None) -> list[Hit]:
        """Score each passage against every query variant (original script + English) and keep the best."""
        keep = keep or self.s.rerank_keep
        if not hits:
            return []
        if self.reranker is None:
            # no reranker: normalise fused scores to [0,1] so grading still has a usable signal
            top = hits[0].fused or 1.0
            for h in hits:
                h.rerank = h.fused / top * 0.5
            return hits[:keep]
        queries = [query] if isinstance(query, str) else [q for q in dict.fromkeys(query) if q.strip()]
        texts = [h.chunk.index_text for h in hits]
        scores = [max(col) for col in zip(*(self.reranker.score(q, texts) for q in queries))]
        for h, s in zip(hits, scores):
            h.rerank = s
        return sorted(hits, key=lambda h: -h.score)[:keep]
