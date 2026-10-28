"""Runtime configuration. Every retrieval technique sits behind a flag so ablations can toggle it."""
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(ROOT / ".env", ROOT / "backend" / ".env"), env_prefix="HAATHI_", extra="ignore")

    data_dir: Path = ROOT / "data"
    index_dir: Path = ROOT / "data" / "index"
    cache_dir: Path = ROOT / "data" / "cache"

    # --- retrieval flags (ablations) ---
    retrieval: Literal["dense", "bm25", "hybrid"] = "hybrid"
    use_sparse: bool = True
    use_rerank: bool = True
    contextual: bool = True
    # Gemini-written context notes cost one request per chunk (~330); opt in when you have quota to spare
    contextual_llm: bool = False
    chunking: Literal["structure", "fixed"] = "structure"
    corrective: bool = True
    verify: bool = True
    crosslingual: Literal["A", "B", "C"] = "C"
    top_k: int = 20
    rerank_keep: int = 6

    # "auto" uses BGE-M3 when FlagEmbedding is installed, otherwise the light hashing embedder.
    embedder: Literal["auto", "bge-m3", "hash"] = "auto"
    reranker: Literal["auto", "bge", "lexical"] = "auto"
    # "numpy" = compact in-process store for small servers (e.g. 512 MB free tiers); same scores as Qdrant
    vector_store: Literal["qdrant-memory", "qdrant-server", "numpy"] = "qdrant-memory"
    qdrant_url: str = "http://localhost:6333"

    # Abstention threshold on the (normalised) top rerank score; tuned via eval/risk_coverage.py
    # None = the value tuned for the active reranker (eval/reports/risk_coverage.md); set to override
    abstain_threshold: float | None = None

    # --- LLM ---
    # accepted as GEMINI_API_KEY or HAATHI_GEMINI_API_KEY, in the shell or in backend/.env
    gemini_api_key: str | None = Field(default=None, validation_alias=AliasChoices("GEMINI_API_KEY", "HAATHI_GEMINI_API_KEY"))
    gemini_model: str = "gemini-3.5-flash-lite"  # free tier: 15 requests/min
    gemini_fallback_model: str = "gemini-3.8-flash"  # free tier: only 20 requests/day
    gemini_rpm: int = 14
    gemini_live_model: str = "gemini-2.5-flash-native-audio-latest"  # streams the speaker's words while they talk  # stay just under the free-tier per-minute limit
    ollama_url: str | None = None
    ollama_model: str = "qwen2.5:3b"

    max_questions: int = 6
    # "production" disables dev-only endpoints such as recording speech-test clips
    env: str = "dev"
    langfuse_enabled: bool = False


@lru_cache
def get_settings() -> Settings:
    import os

    s = Settings()
    # also accept the conventional unprefixed variable
    if not s.gemini_api_key and os.environ.get("GEMINI_API_KEY"):
        s.gemini_api_key = os.environ["GEMINI_API_KEY"]
    return s
