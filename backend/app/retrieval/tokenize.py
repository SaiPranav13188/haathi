"""Script-aware tokenizer for English, Hindi (Devanagari) and Telugu, used by BM25 and the light embedder."""
from __future__ import annotations

import re

_SPLIT = re.compile(r"[^0-9a-zऀ-ॿఀ-౿₹]+")
_INDIC = re.compile(r"[ऀ-ॿఀ-౿]")
STOP = set("""a an the of for in on to and or is are be was were it this that with by as at from can i my me we our you
your am do does did have has had what which who how when where will shall should would there their they them its not no
any all per if than then so such into also may""".split())


def _stem(tok: str) -> list[str]:
    if _INDIC.search(tok):
        # Telugu/Hindi are agglutinative (రైతుని, రైతులకు → రైతు): add short prefixes as extra terms
        out = [tok]
        if len(tok) > 4:
            out += [tok[:4], tok[:5]]
        return out
    if len(tok) > 4 and tok.endswith("ies"):
        return [tok[:-3] + "y"]
    if len(tok) > 3 and tok.endswith("s") and not tok.endswith("ss"):
        return [tok[:-1]]
    return [tok]


def tokenize(text: str) -> list[str]:
    toks = []
    for t in _SPLIT.split(text.lower()):
        if not t or t in STOP:
            continue
        toks.extend(_stem(t))
    return toks
