"""Query normalisation for retrieval: transliteration, glossary translation (offline) and LLM translation.

Cross-lingual strategies (haathi.md §7):  A = original query only, B = English translation only, C = both, fused.
"""
from __future__ import annotations

import re

from .. import llm
from .detect import LangInfo

# Hindi / Telugu / romanised terms → English retrieval keywords (offline fallback for strategy B).
GLOSSARY: dict[str, str] = {
    # people & work
    "రైతు": "farmer", "రైతుని": "farmer", "రైతులకు": "farmers", "raithu": "farmer", "rythu": "farmer", "raitu": "farmer",
    "किसान": "farmer", "kisan": "farmer", "कृषक": "farmer", "కూలీ": "labourer", "కూలి": "labourer", "मज़दूर": "labourer",
    "मजदूर": "labourer", "majdoor": "labourer", "mazdoor": "labourer", "coolie": "labourer",
    "విద్యార్థి": "student", "విద్యార్థిని": "student", "छात्र": "student", "छात्रा": "student", "vidyarthi": "student",
    "మహిళ": "woman", "మహిళలు": "women", "స్త్రీ": "woman", "महिला": "woman", "महिलाओं": "women", "mahila": "woman",
    "అమ్మాయి": "girl daughter", "కూతురు": "daughter", "बेटी": "daughter", "beti": "daughter", "ammayi": "girl daughter",
    "వృద్ధులు": "elderly old age", "వృద్ధాప్య": "old age", "बुज़ुर्ग": "elderly old age", "बुजुर्ग": "elderly old age",
    "కార్మికులు": "workers", "श्रमिक": "worker", "చేతివృత్తి": "artisan", "कारीगर": "artisan",
    # things
    "భూమి": "land", "ఎకరాలు": "acres land", "ఎకరాల": "acres land", "ఎకరం": "acre land", "ज़मीन": "land", "जमीन": "land",
    "एकड़": "acre land", "bhoomi": "land", "zameen": "land", "jameen": "land", "ekaralu": "acres land", "ekaram": "acre",
    "ఇల్లు": "house housing", "ఇళ్లు": "house housing", "घर": "house housing", "आवास": "housing house", "illu": "house",
    "ghar": "house", "పింఛను": "pension", "పెన్షన్": "pension", "पेंशन": "pension", "pinchanu": "pension",
    "స్కాలర్‌షిప్": "scholarship", "ఉపకార వేతనం": "scholarship", "छात्रवृत्ति": "scholarship", "वजीफा": "scholarship",
    "ప్రమాదం": "accident", "ప్రమాద": "accident", "दुर्घटना": "accident", "हादसा": "accident",
    "ఖర్చు": "expenses", "खर्च": "expenses", "బచత్": "savings", "बचत": "savings", "పొదుపు": "savings",
    "పెద్దలు": "elderly old age", "मदद": "assistance help", "సాయం": "assistance help", "సహాయం": "assistance help",
    "బీమా": "insurance", "बीमा": "insurance", "bima": "insurance", "ఆరోగ్యం": "health",
    "వైద్యం": "treatment hospital", "इलाज": "treatment hospital", "स्वास्थ्य": "health", "ఆసుపత్రి": "hospital",
    "अस्पताल": "hospital", "పెళ్లి": "marriage", "వివాహం": "marriage", "शादी": "marriage", "vivaham": "marriage",
    "pelli": "marriage", "shaadi": "marriage", "గ్యాస్": "gas lpg", "गैस": "gas lpg", "సిలిండర్": "cylinder lpg",
    "కరెంటు": "electricity", "విద్యుత్": "electricity", "बिजली": "electricity", "బస్సు": "bus travel", "बस": "bus travel",
    "రుణం": "loan credit", "ऋण": "loan credit", "कर्ज": "loan credit", "లోన్": "loan", "పంట": "crop", "फसल": "crop",
    "బ్యాంకు": "bank account", "बैंक": "bank account", "రేషన్": "ration card", "राशन": "ration card",
    "ఆదాయం": "income", "आय": "income", "आमदनी": "income", "aamdani": "income", "adayam": "income", "sampadana": "income",
    "లక్ష": "lakh", "లక్షలు": "lakh", "लाख": "lakh",
    # question words / intents
    "పత్రాలు": "documents required", "దస్తావేజులు": "documents required",
    "दस्तावेज़": "documents required", "दस्तावेज": "documents required", "कागज": "documents required", "kagaz": "documents",
    "దరఖాస్తు": "how to apply", "आवेदन": "how to apply", "apply": "apply", "ఎలా": "how", "कैसे": "how", "ela": "how",
    "ఎంత": "how much benefit amount", "कितना": "how much benefit amount", "कितने": "how much", "entha": "how much",
    "అర్హత": "eligibility eligible", "అర్హులు": "eligible", "पात्र": "eligible eligibility", "पात्रता": "eligibility",
    "పథకం": "scheme", "పథకాలు": "schemes", "योजना": "scheme", "योजनाएं": "schemes", "yojana": "scheme",
    "pathakam": "scheme", "pathakalu": "schemes", "ప్రయోజనం": "benefit", "लाभ": "benefit", "fayda": "benefit",
    "ఉచిత": "free", "मुफ्त": "free", "मुफ़्त": "free", "free": "free",
    # places
    "తెలంగాణ": "telangana", "तेलंगाना": "telangana", "ఆంధ్రప్రదేశ్": "andhra pradesh", "ఆంధ్ర": "andhra pradesh",
    "आंध्र": "andhra pradesh", "గ్రామం": "village rural", "गाँव": "village rural", "गांव": "village rural",
}
_TOKEN = re.compile(r"[ऀ-ॿఀ-౿]+|[A-Za-z]+|\d+(?:\.\d+)?")


def glossary_translate(text: str) -> str:
    out = []
    for tok in _TOKEN.findall(text):
        low = tok.lower()
        if low in GLOSSARY:
            out.append(GLOSSARY[low])
            continue
        # Indic agglutination: try progressively shorter prefixes (రైతులకు → రైతు)
        hit = next((GLOSSARY[low[:n]] for n in range(len(low) - 1, 2, -1) if low[:n] in GLOSSARY), None)
        if hit:
            out.append(hit)
        elif re.fullmatch(r"[A-Za-z]+|\d+(?:\.\d+)?", tok):
            out.append(low)
    return " ".join(out)


def transliterate_to_native(text: str, lang: str) -> str:
    """Romanised Hindi/Telugu → native script (indic-transliteration, ITRANS-ish). Best effort; used for
    display and as an extra retrieval variant, never as the only query."""
    try:
        from indic_transliteration import sanscript
        from indic_transliteration.sanscript import transliterate
    except ImportError:  # pragma: no cover
        return text
    target = sanscript.DEVANAGARI if lang == "hi" else sanscript.TELUGU
    return transliterate(text.lower(), sanscript.ITRANS, target)


async def to_english(text: str, info: LangInfo) -> tuple[str, str]:
    """Return (english_query, method)."""
    if info.lang == "en" and not info.code_mixed:
        return text, "none"
    if llm.available():
        out = await llm.complete(
            f"Translate this question about Indian government schemes into simple English. "
            f"It may be {'Hindi' if info.lang == 'hi' else 'Telugu'}, romanised, or mixed with English. "
            f"Keep scheme names and numbers exactly. Reply with only the translation.\n\n{text}")
        if out:
            return out.strip(), "llm"
    return glossary_translate(text) or text, "glossary"


async def query_variants(text: str, info: LangInfo, strategy: str) -> tuple[list[str], str, str]:
    """Return (queries to retrieve with, english_query, method)."""
    english, method = await to_english(text, info)
    if strategy == "A" or english == text:
        variants = [text]
    elif strategy == "B":
        variants = [english]
    else:
        variants = [text, english]
    if info.romanized:
        variants.append(transliterate_to_native(text, info.lang))
    return variants, english, method
