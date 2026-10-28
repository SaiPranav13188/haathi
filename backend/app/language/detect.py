"""Language + script detection, including code-mixing and Latin-script (romanised) Hindi / Telugu."""
from __future__ import annotations

import re
from dataclasses import dataclass

DEV = re.compile(r"[ऀ-ॿ]")
TEL = re.compile(r"[ఀ-౿]")
LAT = re.compile(r"[A-Za-z]")
WORD = re.compile(r"[A-Za-z]+")

# Frequent function words / common words in romanised chat ("Hinglish", "Tenglish").
ROMAN_HI = set("""hai hain mera meri mere mujhe hum ham aap kya kaise kitna kitni kitne nahi nahin haan ha ji
kaun konsi kaunsi paisa paise milega milegi chahiye karna kare karo hoga rehta rehti hoon hu
beti beta saal umar aay aamdani kamai liye wala wali tak aur bhi lekin abhi sabse batao bataye bataiye""".split())
ROMAN_TE = set("""nenu naku naaku maa ma memu meeru miru undi unnadi unnayi ledu levu kavali emi enti ela entha
ekkada evaru avunu kaadu bhoomi ekaralu ekaram illu pathakalu prabhutvam dabbulu raithuni
ammayi abbayi vayasu samvatsaralu sampadana adayam chesthunnanu chestunna chadhuvutunna chaduvutunna istara
istaru vastundi vasthundi cheppandi cheppu gurinchi kosam""".split())


@dataclass
class LangInfo:
    lang: str          # en | hi | te  (language to answer in)
    script: str        # latin | devanagari | telugu | mixed
    code_mixed: bool
    romanized: bool    # Hindi/Telugu written in Latin letters

    def as_dict(self) -> dict:
        return self.__dict__.copy()


def detect(text: str, hint: str | None = None) -> LangInfo:
    dev, tel, lat = len(DEV.findall(text)), len(TEL.findall(text)), len(LAT.findall(text))
    total = dev + tel + lat or 1
    words = [w.lower() for w in WORD.findall(text)]
    hi_hits = sum(w in ROMAN_HI for w in words)
    te_hits = sum(w in ROMAN_TE for w in words)

    if tel / total > 0.3:
        return LangInfo("te", "telugu" if lat / total < 0.15 else "mixed", lat / total >= 0.15, False)
    if dev / total > 0.3:
        return LangInfo("hi", "devanagari" if lat / total < 0.15 else "mixed", lat / total >= 0.15, False)
    # Latin script: English, or romanised Hindi/Telugu (possibly mixed with English words)
    hits = max(hi_hits, te_hits)
    if words and ((hits >= 2 and hits >= 0.2 * len(words)) or (len(words) <= 3 and hits >= 1)):
        lang = "te" if te_hits > hi_hits else "hi"
        mixed = max(hi_hits, te_hits) < 0.7 * len(words)
        return LangInfo(lang, "latin", mixed, True)
    lang = hint if hint in {"hi", "te"} and not words else "en"
    return LangInfo(lang, "latin", False, False)
