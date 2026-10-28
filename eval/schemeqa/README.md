---
license: cc-by-4.0
language: [en, hi, te]
task_categories: [question-answering]
tags: [rag, government-schemes, india, telangana, multilingual, code-mixed, abstention]
pretty_name: SchemeQA-Indic
size_categories: [n<1K]
---

# SchemeQA-Indic (v0, draft)

Multilingual questions about Indian government welfare schemes (central, **Telangana**, Andhra Pradesh), for
evaluating retrieval-augmented assistants on retrieval, answer correctness, eligibility decisions and
abstention. Built for the Haathi project.

## Status

**v0 has 69 author-drafted items and is not yet human-verified.** Each item has `"verified": "author-draft"`.
Before publishing on Hugging Face: check every item against the official PDF, have a second person check a
sample, flip `verified` to `human-verified`, and grow to 150+ items (50 per language) as planned.

## Composition (v0)

| | English | Hindi (incl. Hinglish) | Telugu (incl. Tenglish) |
|---|---|---|---|
| items | 23 | 23 | 23 |

Types: `factual`, `documents`, `how_to_apply`, `eligibility` (profile → gold set of eligible schemes),
`comparison`, `outdated` (renamed/changed schemes, e.g. Rythu Bandhu → Rythu Bharosa), `unanswerable`
(must abstain). 9 free-form answerable items name no scheme, to exercise retrieval and the abstention gate.

## Fields

| field | meaning |
|---|---|
| `id` | `<lang>-NNN` |
| `language` | `en` / `hi` / `te` (language of the question; romanised + code-mixed noted in `note`) |
| `type` | see above |
| `question` | the user message |
| `answerable` | `false` → the system should abstain |
| `gold_sources` | `[{doc, page}]` where the answer is found |
| `gold_answer_must_include` | key facts (numbers, names) a correct answer must contain |
| `gold_eligible` | for `eligibility` items: scheme ids the person is *clearly* eligible for from what they said |
| `verified` | `author-draft` or `human-verified` |

## How it was made

Questions were written by the author to mirror how people in Telangana and Andhra Pradesh ask: Telugu
script, Hindi, and English letters ("nenu raithu ni", "mera income 2 lakh hai"). Gold answers come from the
scheme guideline summaries in `data/seed/docs/`, which cite the official portal for each scheme.

## Limitations

- The seed documents are summaries of official guidelines, not the official PDFs themselves. Amounts and
  limits change. Verify against the official source and record the version date.
- The set is small. Scores move a lot with a single item.
- Eligibility golds only count what the person said. Real eligibility depends on official records (e.g. SECC
  lists, land records).
- Written by one author. It has not yet been checked by a second annotator.

## Evaluation

`make eval` runs Haathi on this set and writes `eval/reports/` (Recall@5, MRR, key-fact correctness, eligibility
F1, abstention, faithfulness, latency, per language; ablations; risk–coverage).
