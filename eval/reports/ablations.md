# Ablations (2026-10-28)

embedder `bge-m3`, reranker `bge-reranker-v2-m3`, LLM off. SchemeQA-Indic v0 (69 items, author-draft).

Each row adds one technique to the row above.

| config | recall@5 | mrr | correctness | eligibility_f1 | abstain_recall | false_abstain | faithfulness | p50_ms |
|---|---|---|---|---|---|---|---|---|
| naive RAG (dense, fixed chunks) | 93.9 | 0.852 | 93.9 | 100.0 | 88.9 | 0.0 | 100.0 | 38.7 |
| + hybrid (BM25 + dense + sparse, RRF) | 100.0 | 0.963 | 85.7 | 100.0 | 55.6 | 8.3 | 100.0 | 92.6 |
| + reranker | 89.8 | 0.811 | 91.8 | 100.0 | 77.8 | 5.0 | 100.0 | 1126.4 |
| + Contextual Retrieval | 95.9 | 0.896 | 91.8 | 100.0 | 88.9 | 5.0 | 100.0 | 1451.7 |
| + structure-aware chunking | 98.0 | 0.939 | 91.8 | 100.0 | 88.9 | 5.0 | 100.0 | 1900.3 |
| + cross-lingual C (orig + English) | 100.0 | 0.925 | 95.9 | 100.0 | 88.9 | 1.7 | 100.0 | 2437.4 |
| + corrective loop | 98.0 | 0.905 | 95.9 | 100.0 | 88.9 | 1.7 | 100.0 | 2666.5 |
| + citation verifier | 98.0 | 0.905 | 95.9 | 100.0 | 88.9 | 1.7 | 99.4 | 2808.0 |


## Cross-lingual strategies

A = embed the original query, B = translate to English first, C = both fused.

| config | recall@5 | mrr | correctness | abstain_recall |
|---|---|---|---|---|
| A · en | 100.0 | 1.0 | 93.8 | 100.0 |
| A · hi | 100.0 | 0.912 | 88.2 | 100.0 |
| A · te | 93.8 | 0.906 | 93.8 | 66.7 |
| B · en | 100.0 | 1.0 | 93.8 | 100.0 |
| B · hi | 88.2 | 0.647 | 100.0 | 100.0 |
| B · te | 81.2 | 0.719 | 93.8 | 66.7 |
| C · en | 100.0 | 1.0 | 93.8 | 100.0 |
| C · hi | 100.0 | 0.843 | 100.0 | 100.0 |
| C · te | 93.8 | 0.875 | 93.8 | 66.7 |


With LLM off, strategy B translates with the offline glossary only.
