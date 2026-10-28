"""Citation verifier: is each claim supported by the passage it cites?

Offline check (always): every number in the claim must appear in the cited passage, and (for English free
text) enough content words must overlap. With an LLM configured, free-text claims also get an NLI-style
check. Unsupported claims are removed from the answer; uncertain ones are flagged.
"""
from __future__ import annotations

import re

from .. import llm
from ..retrieval.tokenize import tokenize

_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


def numbers(text: str) -> set[str]:
    out = set()
    for m in _NUM.findall(text):
        v = m.replace(",", "").rstrip(".")
        if v:
            out.add(v.rstrip("0").rstrip(".") if "." in v else v)
    return out


_MARKER = re.compile(r"\[\d+\]")


def check_offline(claim: str, passage: str, structured: bool) -> str:
    claim = _MARKER.sub("", claim)  # citation markers like [2] are not facts to verify
    cn, pn = numbers(claim), numbers(passage)
    if cn - pn:
        return "unsupported"
    if structured:  # claim was generated from this exact quote; numbers already matched
        return "supported"
    ct = set(tokenize(claim))
    if not ct:
        return "unclear"
    overlap = len(ct & set(tokenize(passage))) / len(ct)
    return "supported" if overlap >= 0.45 else "unclear" if overlap >= 0.2 else "unsupported"


NLI = """Passage: \"\"\"{p}\"\"\"
Claim: \"\"\"{c}\"\"\"
Does the passage fully support the claim? Answer JSON {{"label": "supported" | "unsupported" | "unclear"}}."""


async def verify(claim: str, passage: str, structured: bool = False) -> str:
    status = check_offline(claim, passage, structured)
    if structured or status == "unsupported" or not llm.available():
        return status
    data = await llm.complete_json(NLI.format(p=passage[:2000], c=_MARKER.sub("", claim)))
    label = (data or {}).get("label") if isinstance(data, dict) else None
    return label if label in {"supported", "unsupported", "unclear"} else status
