import os
import sys
from pathlib import Path

# Tests use the fast built-in engine and never call Gemini, whatever is installed or configured locally.
os.environ.setdefault("HAATHI_EMBEDDER", "hash")
os.environ.setdefault("HAATHI_RERANKER", "lexical")
os.environ["GEMINI_API_KEY"] = ""
os.environ["HAATHI_GEMINI_API_KEY"] = ""

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
