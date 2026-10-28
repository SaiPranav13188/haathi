# SchemeQA-Indic results (2026-10-28)

Engine: `{"embedder": "bge-m3", "reranker": "bge-reranker-v2-m3", "llm": false}` · items: 69 (benchmark v0, author-draft — needs human verification)

| config | n | recall@5 | mrr | correctness | eligibility_f1 | abstain_recall | false_abstain | faithfulness | p50_ms | p95_ms |
|---|---|---|---|---|---|---|---|---|---|---|
| all | 69 | 98.0 | 0.905 | 95.9 | 100.0 | 100.0 | 1.7 | 99.4 | 1871.6 | 4827.2 |
| en | 23 | 100.0 | 1.0 | 93.8 | 100.0 | 100.0 | 0.0 | 99.6 | 1606.4 | 4827.2 |
| hi | 23 | 100.0 | 0.843 | 100.0 | 100.0 | 100.0 | 0.0 | 99.0 | 2574.5 | 3890.5 |
| te | 23 | 93.8 | 0.875 | 93.8 | 100.0 | 100.0 | 5.0 | 99.5 | 3151.2 | 4147.8 |


Failures:

- `en-023` (factual): 'The student must be studying in Class 11 or a higher course after passing the matriculation (Class 10) examination. [1] SC majority district'
- `te-022` (factual): 'దీని గురించి నాకు ఖచ్చితంగా తెలియదు, ఊహించి చెప్పడం ఇష్టం లేదు. దయచేసి కింది అధికారిక వనరులు చూడండి.'
