# Light engine (what the free live site runs)

Hashing embedder + lexical reranker + NumPy store, 30 summaries + 15 official documents, Gemini off.

| config | recall@5 | mrr | correctness | eligibility_f1 | abstain_recall | false_abstain | faithfulness | p50_ms |
|---|---|---|---|---|---|---|---|---|
| all | 81.6 | 0.656 | 95.9 | 100.0 | 77.8 | 1.7 | 99.4 | 89.3 |
| en | 100.0 | 0.969 | 93.8 | 100.0 | 100.0 | 0.0 | 99.5 | 67.1 |
| hi | 76.5 | 0.541 | 100.0 | 100.0 | 66.7 | 0.0 | 99.0 | 87.9 |
| te | 68.8 | 0.466 | 93.8 | 100.0 | 66.7 | 5.0 | 99.5 | 132.4 |
