"""Build the Hugging Face Space folder and upload it.

    cd backend && uv run python ../deploy/deploy_hf_space.py <hf-username>

Needs `hf auth login` (a write token). Sets GEMINI_API_KEY as a Space secret from backend/.env.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "deploy" / ".build" / "hf-space"


def stage() -> None:
    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)
    shutil.copy(ROOT / "deploy" / "hf-space" / "Dockerfile", STAGE / "Dockerfile")
    shutil.copy(ROOT / "deploy" / "hf-space" / "README.md", STAGE / "README.md")
    # pinned runtime requirements: base deps + FlagEmbedding (torch is installed from the CPU index in the Dockerfile)
    base = subprocess.run(["uv", "export", "--no-dev", "--no-hashes", "--no-emit-project", "--frozen"],
                          cwd=ROOT / "backend", capture_output=True, text=True, check=True).stdout
    reqs = [l for l in base.splitlines() if l and not l.startswith(("#", " ", "-e"))]
    reqs += ["FlagEmbedding>=1.3", "transformers>=4.44,<5"]
    (STAGE / "requirements.txt").write_text("\n".join(reqs) + "\n")
    ignore = shutil.ignore_patterns("__pycache__", ".venv", ".pytest_cache", ".hypothesis", ".coverage", "tests", ".env",
                                    "*.log", "locustfile.py")
    shutil.copytree(ROOT / "backend", STAGE / "backend", ignore=ignore)
    data = STAGE / "data"
    for sub in ("schemes", "seed"):
        shutil.copytree(ROOT / "data" / sub, data / sub)
    shutil.copy(ROOT / "data" / "manifest.csv", data / "manifest.csv")
    # official documents (served by the source viewer) and their download records
    (data / "raw").mkdir(parents=True)
    for p in (ROOT / "data" / "raw").iterdir():
        if p.suffix.lower() in {".pdf", ".html", ".json"}:
            shutil.copy(p, data / "raw" / p.name)
    # parsed documents + cached BGE-M3 vectors so the Space doesn't re-embed 2,000+ passages on every start
    (data / "index").mkdir()
    shutil.copytree(ROOT / "data" / "index" / "parsed", data / "index" / "parsed")
    shutil.copy(current_vectors(), data / "index")
    (data / "cache").mkdir()
    if (ROOT / "data" / "cache" / "context_notes.json").exists():
        shutil.copy(ROOT / "data" / "cache" / "context_notes.json", data / "cache" / "context_notes.json")
    size = sum(f.stat().st_size for f in STAGE.rglob("*") if f.is_file()) / 1e6
    print(f"staged {STAGE} ({size:.0f} MB)")


def current_vectors() -> Path:
    """The cached BGE-M3 vectors for the default configuration (same digest the retriever computes)."""
    import hashlib

    sys.path.insert(0, str(ROOT / "backend"))
    from app.corpus import Corpus

    texts = [c.index_text for c in Corpus().chunks]
    digest = hashlib.sha1("\x1e".join(texts).encode()).hexdigest()[:12]
    path = ROOT / "data" / "index" / f"emb_bge-m3_{digest}.npz"
    if not path.exists():
        raise SystemExit(f"{path.name} missing: run `make ingest` with the ml extra first")
    return path


def gemini_key() -> str | None:
    env = ROOT / "backend" / ".env"
    for line in env.read_text().splitlines() if env.exists() else []:
        if line.startswith(("GEMINI_API_KEY=", "HAATHI_GEMINI_API_KEY=")):
            return line.split("=", 1)[1].strip() or None
    return None


def main(user: str) -> None:
    stage()
    api = HfApi()
    repo = f"{user}/haathi-api"
    api.create_repo(repo, repo_type="space", space_sdk="docker", exist_ok=True)
    key = gemini_key()
    if key:
        api.add_space_secret(repo, "GEMINI_API_KEY", key)
    api.add_space_variable(repo, "HAATHI_ENV", "production")
    api.upload_folder(repo_id=repo, repo_type="space", folder_path=str(STAGE), commit_message="Deploy Haathi backend")
    sub = f"{user.lower().replace('_', '-')}-haathi-api"
    print(f"Space: https://huggingface.co/spaces/{repo}\nAPI:   https://{sub}.hf.space/api/health")


if __name__ == "__main__":
    main(sys.argv[1])
