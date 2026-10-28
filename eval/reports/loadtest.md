# Load test (Locust)

MacBook (Apple M5, 16 GB), backend `uvicorn` single worker with `--reload`, light engine (hashing embedder +
lexical reranker, no LLM). 30 s per run; task mix: chat 5 : next-question 2 : source page 1. Raw CSVs:
`load_20_*.csv`, `load_50_*.csv`.

| users | requests | errors | chat p50 | chat p95 | next-question p50 | next-question p95 | throughput |
|---|---|---|---|---|---|---|---|
| 20 | 267 | 0 (0%) | 3 ms | 120 ms | 92 ms | ~240 ms | 9.9 req/s |
| 50 | 726 | 0 (0%) | 2 ms | 170 ms | 84 ms | ~590 ms | 24.3 req/s |

Cache: identical normalised questions are replayed from an in-memory LRU (events included), hit rate **85.9%**
during the run — inflated because the load script cycles through only 8 questions; real traffic will be lower.
Uncached chat (first time a question is seen): p50 64 ms, p95 415 ms time-to-full-answer.

With Gemini enabled, latency is dominated by the API (and free-tier rate limits): the client falls back to
`gemini-3.5-flash-lite`, then Ollama, and the UI shows the 🐢 tortoise after 3 s.
