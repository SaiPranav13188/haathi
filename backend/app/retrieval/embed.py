"""Embedders. BGE-M3 gives dense + sparse vectors in one multilingual model (Apple GPU via MPS when available).
The hashing embedder (char n-grams) is the zero-download fallback so the app runs without the ml extra."""
from __future__ import annotations

import hashlib
import logging
from functools import lru_cache

import numpy as np

from .tokenize import tokenize

log = logging.getLogger(__name__)


def pick_device() -> str:
    try:
        import torch

        if torch.backends.mps.is_available():
            return "mps"
        if torch.cuda.is_available():
            return "cuda"
    except ImportError:
        pass
    return "cpu"


class HashEmbedder:
    name = "hash"
    dim = 2048

    def _h(self, s: str, mod: int) -> int:
        return int.from_bytes(hashlib.blake2b(s.encode(), digest_size=8).digest(), "little") % mod

    def encode(self, texts: list[str]) -> tuple[np.ndarray, list[dict[int, float]]]:
        dense = np.zeros((len(texts), self.dim), dtype=np.float32)
        sparse: list[dict[int, float]] = []
        for i, t in enumerate(texts):
            norm = " " + " ".join(t.lower().split()) + " "
            for n in (3, 4, 5):
                for j in range(len(norm) - n + 1):
                    dense[i, self._h(norm[j:j + n], self.dim)] += 1.0
            sp: dict[int, float] = {}
            for tok in tokenize(t):
                k = self._h(tok, 2**31 - 1)
                sp[k] = sp.get(k, 0.0) + 1.0
            sparse.append({k: float(np.log1p(v)) for k, v in sp.items()})
        dense = np.sqrt(dense)
        dense /= np.linalg.norm(dense, axis=1, keepdims=True) + 1e-9
        return dense, sparse


class BGEM3Embedder:  # pragma: no cover - needs the ml extra and a model download
    name = "bge-m3"
    dim = 1024

    def __init__(self) -> None:
        from FlagEmbedding import BGEM3FlagModel

        device = pick_device()
        log.info("loading BGE-M3 on %s", device)
        self.model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=device != "cpu", devices=device)

    def encode(self, texts: list[str]) -> tuple[np.ndarray, list[dict[int, float]]]:
        out = self.model.encode(texts, batch_size=16, max_length=1024, return_dense=True, return_sparse=True)
        dense = np.asarray(out["dense_vecs"], dtype=np.float32)
        sparse = [{int(k): float(v) for k, v in w.items()} for w in out["lexical_weights"]]
        return dense, sparse


@lru_cache
def get_embedder(kind: str = "auto"):
    if kind in ("auto", "bge-m3"):
        try:
            return BGEM3Embedder()
        except Exception as e:
            if kind == "bge-m3":
                raise
            log.info("BGE-M3 unavailable (%s); using hashing embedder", type(e).__name__)
    return HashEmbedder()
