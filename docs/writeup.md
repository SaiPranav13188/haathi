# Haathi: a multilingual, source-grounded eligibility assistant for Indian welfare schemes

*B. Sai Pranav · technical report (draft)*

## Problem

People who qualify for welfare schemes often never apply, for three reasons. They don't know which schemes
fit them. Rules are written in English bureaucratic prose. And a wrong "you're eligible" can cost a poor
family a wasted trip to an office. For a Telangana farmer who speaks Telugu, the useful answer is short: which
schemes, why (the exact rule), what to bring, and where to go.

## Approach

**Retrieval.** Scheme documents are parsed into pages, blocks and lines with bounding boxes. They are chunked
by structure (sections, and table rows with headers repeated) and indexed three ways: BM25, dense and sparse
vectors in Qdrant. The three result lists are fused with Reciprocal Rank Fusion. A reranker scores each
passage against both the original-script query and its English translation, and keeps the best score. If the
best passage is weak, the graph rewrites the query once and retries. If it's still weak, it abstains.

**Eligibility.** Rules are JSON: field, operator, value and a source quote with page and bbox. Logic
expressions combine them with AND/OR/NOT. A Python evaluator gives each rule pass / fail / unknown and combines
them with Kleene logic. Rules on the same field are correlated (area = rural OR area = urban), so when the
unknown fields are finite the evaluator enumerates their values and decides whenever every case agrees. For
"not eligible" schemes, a what-if search finds single numeric rules that would flip the result, and only
suggests reachable changes.

**Questioning.** Among the schemes still "maybe", the next question maximises expected information gain:
IG(f) = H − Σ_v P(f=v) Σ_s h(P(s eligible | f=v)). The probabilities come from Monte-Carlo completions of
unknown fields drawn from priors.

**Language.** Detection is script-based plus romanised wordlists. Facts come from deterministic multilingual
patterns ("2 ఎకరాల", "1.5 lakh", "నెలకు 12 వేలు" ×12) and are kept only for first-person statements. Answers
come from templates in the user's language, so amounts and eligibility always come from the rule engine.

**Verification.** Structured citations are checked by confirming each quote appears verbatim on its cited
page. Free-text claims must have all their numbers in the cited passage, enough content-word overlap, and,
when an LLM is configured, pass an NLI-style check. Unsupported claims are removed.

## Experiments (light engine, SchemeQA-Indic v0, 69 items)

| | result |
|---|---|
| Overall | Recall@5 95.9, key-fact correctness 98.0, eligibility F1 100, abstention on unanswerable 88.9, false abstention 1.7 |
| Biggest ablation gains | cross-lingual fusion (correctness 89.8 → 98.0); reranker (abstention 66.7 → 88.9) |
| Questioning | 11.77 questions vs 16.57 fixed (−29%), vs 12.87 for fixed order skipping irrelevant fields |
| Load | 50 concurrent users, 0 errors, chat p95 170 ms (cached), uncached p95 415 ms |

**Full models (BGE-M3 + bge-reranker-v2-m3, plus 15 official documents):** Recall@5 98.0, MRR 0.905, abstention 100
on unanswerable questions, at about 2 s per answer. Hybrid retrieval alone has the best MRR (0.963). The reranker lowers
recall but provides the abstention signal. Embedding the Telugu/Hindi query directly beats translating it first
(Telugu Recall@5 93.8 vs 81.2).

**Official sources:** Telangana Government Orders fetched from goir.telangana.gov.in corrected one rule. Since
G.O.Ms.No.18 (2022), rural minority students get the ₹2 lakh post-matric income limit, not ₹1.5 lakh. 37 citations now
quote official text.

## Failures and lessons

- A lexical reranker that sees only the English translation hurts Indic queries (Recall@5 fell from 100 to
  73.5). Scoring every query variant fixed it.
- Topic questions ("pension for unorganised workers?") were first parsed as facts about the user, which
  triggered an interview instead of an answer. Requiring first-person markers fixed four benchmark failures.
- Without an LLM, Contextual Retrieval reduces to template notes and doesn't move the metrics.
- `transformers` 5.x silently broke the cross-encoder: every score came out ≈0 with no error. Pinning 4.x fixed it.
  A sanity pair with an obvious answer is now part of setup checks.
- Remaining failures: one Hindi unanswerable question scores above the threshold, and one Telugu free-form
  question ("చేతివృత్తుల వారికి ఏ సాయం ఉంది?") is refused because the fallback retriever can't match it.

## Future work

Ingest official PDFs with Docling and review the extracted rules. Grow the benchmark to 150+
human-verified items and release it. Run the full-model ablations (BGE-M3, bge-reranker, Gemini). Measure
the LLM-only eligibility baseline and the Telugu ASR WER. Build a Rive Gajju. Deploy, then put the app in
front of 10–20 real users in Telangana.
