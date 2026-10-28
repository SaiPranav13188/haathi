# Eligibility: rule engine vs LLM-only

11 profile questions from SchemeQA-Indic v0.

| method | F1 | exact set match |
|---|---|---|
| Rule engine (Haathi) | 100.0 | 100.0 |
| LLM-only | 74.8 | 27.3 |

LLM-only = `gemini-3.5-flash-lite` (free tier) given all 30 scheme documents and the user's message, asked to list
the schemes the person is clearly eligible for. Caveat: the gold sets were written by the author from the same
rules the engine uses, so the engine's 100 shows it implements the written rules faithfully; the LLM-only gap
(mostly listing schemes that need facts the user never gave) is the meaningful part.
