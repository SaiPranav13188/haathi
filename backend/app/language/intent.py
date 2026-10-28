"""Intent classification (find schemes / one scheme: benefit, documents, how to apply, eligibility / general / chit-chat)."""
from __future__ import annotations

import re

_P = lambda s: re.compile(s, re.I)  # noqa: E731

CHITCHAT = _P(r"^\s*(hi+|hello|hey|namaste|namaskar|namaskaram|vanakkam|thanks?|thank you|thx|ok+|okay|good (morning|evening)|bye|"
              r"నమస్తే|నమస్కారం|ధన్యవాదాలు|థాంక్స్|हाय|नमस्ते|नमस्कार|धन्यवाद|शुक्रिया)\W*$")
DOCUMENTS = _P(r"document|papers?|certificate|proof|kagaz|kaagaz|patralu|పత్రాలు|దస్తావేజు|ఏమి తీసుకెళ్ల|దాఖలాలు|दस्तावेज|कागज|क्या लेकर|what (do i|to) bring")
HOW_APPLY = _P(r"how (do|can|to) (i )?(apply|register|enrol|get)|apply|application|register|enrol|where to|ela apply|"
               r"దరఖాస్తు|ఎలా పొంద|ఎక్కడ|నమోదు|आवेदन|कैसे (मिले|मिलेगा|करें|लें)|पंजीकरण|कहाँ")
BENEFIT = _P(r"how much|benefit|amount|money|kitna|kitne|entha|enta|ఎంత|ప్రయోజనం|లాభం|డబ్బు|कितना|कितने|लाभ|पैसा|राशि|what (do|will) i get")
ELIGIBILITY = _P(r"eligib|qualify|can i (get|apply)|am i|who can|criteria|ardhata|patr|అర్హత|అర్హుల|నాకు వస్తుందా|వస్తుందా|पात्र|मिलेगा क्या|मिल सकता")
FIND = _P(r"which schemes?|what schemes?|schemes? for me|any schemes?|schemes? (i|can)|suggest|recommend|help me find|benefits? for me|"
          r"ఏ పథకాలు|ఏయే పథకాలు|పథకాలు|నాకు ఏ|कौन सी योजना|कौन-सी योजना|योजनाएं|योजनाओं|मेरे लिए|kaun si yojana|konsi yojana|"
          r"emi pathakalu|e pathakalu|pathakalu|yojanaye")


def classify(text: str, mentioned: list[str], n_facts: int) -> str:
    t = text.strip()
    if CHITCHAT.match(t):
        return "chitchat"
    if mentioned:
        if DOCUMENTS.search(t):
            return "documents"
        if HOW_APPLY.search(t):
            return "how_to_apply"
        if ELIGIBILITY.search(t):
            return "scheme_eligibility"
        if BENEFIT.search(t):
            return "benefit"
        return "scheme_info"
    if n_facts >= 1:
        return "find_schemes"
    if FIND.search(t) or ELIGIBILITY.search(t):
        from .facts import is_about_self

        # "which schemes can I get" → interview; "any scheme for artisans?" → answer about that group
        return "find_schemes" if is_about_self(t) else "general"
    return "general"
