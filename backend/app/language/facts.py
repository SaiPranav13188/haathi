"""Profile fact extraction from free text in English / Hindi / Telugu / romanised / code-mixed input.

Each fact remembers the exact text it came from ("user said '1.5 lakh'"), so the UI can show provenance.
Deterministic patterns run first; when an LLM is configured, `extract_with_llm` can add facts the patterns
missed (validated through fields.coerce, never trusted blindly).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from ..eligibility.fields import FIELDS, coerce


@dataclass
class Fact:
    field: str
    value: Any
    source_text: str
    method: str = "pattern"  # pattern | answer | llm

    def as_dict(self) -> dict:
        return {"field": self.field, "value": self.value, "source_text": self.source_text, "method": self.method}


def _rx(words: str) -> re.Pattern:
    return re.compile(words, re.I)


NEG = _rx(r"\b(no|not|don'?t|do not|dont|doesn'?t|never|without|nahi|nahin|nai|ledu|levu|kadu|kaadu|none)\b|నహీ|లేదు|లేవు|కాదు|नहीं|नही|ना\b")
HAVE = _rx(r"\b(have|has|got|own|owns|undi|unnadi|unnayi|hai|hain|yes|avunu|haan)\b|ఉంది|ఉన్నాయి|ఉన్నది|है|हैं|అవును|हाँ|हां")
YES = _rx(r"^\s*(yes|y|haan|ha|han|ji|ji haan|avunu|undi|unnadi|hai|ok|sure)\b|^\s*(అవును|ఉంది|ఉన్నాయి|हाँ|हां|है|జీ)")
NO = _rx(r"^\s*(no|n|nahi|nahin|nai|ledu|levu|kaadu|kadu|none)\b|^\s*(లేదు|లేవు|కాదు|नहीं|नही|ना)")

_NUM = r"(\d+(?:,\d{2,3})*(?:\.\d+)?)"
_MULT = {
    "lakh": 1e5, "lakhs": 1e5, "lac": 1e5, "lacs": 1e5, "l": 1e5, "लाख": 1e5, "లక్ష": 1e5, "లక్షలు": 1e5, "లక్షల": 1e5,
    "thousand": 1e3, "k": 1e3, "हज़ार": 1e3, "हजार": 1e3, "వేలు": 1e3, "వేల": 1e3, "velu": 1e3, "vela": 1e3, "hazar": 1e3,
    "crore": 1e7, "cr": 1e7, "करोड़": 1e7, "కోట్లు": 1e7, "కోట్ల": 1e7,
}
MONEY = re.compile(_NUM + r"\s*(lakhs?|lacs?|l\b|लाख|లక్షలు|లక్షల|లక్ష|thousand|k\b|हज़ार|हजार|వేలు|వేల|vel[ua]|hazar|crore|cr\b|करोड़|కోట్లు|కోట్ల)?", re.I)
MONTHLY = _rx(r"per month|a month|monthly|/\s*month|mahina|mahine|mahiney|nelaku|nelakki|నెలకు|నెల|महीना|महीने|प्रति माह|मासिक")
INCOME_KW = _rx(r"income|earn|earning|salary|kamai|kamaai|aay\b|aamdani|sampadana|adayam|jeetham|జీతం|ఆదాయం|సంపాదన|आय|आमदनी|कमाई|वेतन|తనఖా")
ACRES = re.compile(_NUM + r"\s*(acres?|ac\b|ekar\w*|ekaram|ఎకరా\w*|ఎకరం|एकड़|guntas?|గుంటలు|గుంటల)", re.I)
AGE = re.compile(r"(?:\b(?:age|aged|umar|umr|vayasu|vayassu)\s*(?:is|:)?\s*" + r"(\d{1,3}))|(?:(\d{1,3})\s*(?:years? old|yrs? old|yrs\b|years\b|year old|saal|sal\b|ఏళ్ల|ఏళ్లు|సంవత్సరాల|సంవత్సరాలు|वर्ष|साल))|(?:(?:వయస్సు|వయసు|उम्र|आयु)\s*(\d{1,3}))", re.I)

STATE = [
    ("Telangana", _rx(r"telangana|తెలంగాణ|तेलंगाना|hyderabad|హైదరాబాద్|हैदराबाद|secunderabad|warangal|వరంగల్|karimnagar|కరీంనగర్|khammam|ఖమ్మం|nizamabad|నిజామాబాద్|nalgonda|నల్గొండ|adilabad|mahabubnagar|medak|siddipet|sangareddy|suryapet|mancherial|jagtial|kamareddy|vikarabad|rangareddy|medchal")),
    ("Andhra Pradesh", _rx(r"andhra|ఆంధ్ర|आंध्र|\bap\b|vijayawada|విజయవాడ|visakhapatnam|vizag|విశాఖ|guntur|గుంటూరు|tirupati|తిరుపతి|nellore|నెల్లూరు|kurnool|కర్నూలు|kakinada|rajahmundry|anantapur|kadapa|ongole|eluru|srikakulam|vizianagaram|chittoor")),
    ("Other", _rx(r"karnataka|bangalore|bengaluru|maharashtra|mumbai|pune|tamil nadu|chennai|kerala|delhi|bihar|uttar pradesh|\bup\b|gujarat|rajasthan|odisha|west bengal|kolkata|madhya pradesh|punjab|haryana|assam|jharkhand|chhattisgarh|goa")),
]
AREA = [
    ("rural", _rx(r"village|rural|gram\b|gaon|gaanv|palle|pallе|గ్రామం|గ్రామంలో|పల్లె|ఊరు|गाँव|गांव|ग्रामीण")),
    ("urban", _rx(r"\bcity\b|\btown\b|urban|shahar|nagaram|pattanam|పట్టణం|నగరం|सिटी|शहर|शहरी|hyderabad|హైదరాబాద్|हैदराबाद")),
]
OCCUPATION = [  # order matters: more specific first
    ("agri_labourer", _rx(r"farm labou?r|agricultural labou?r|agri labou?r|farm worker|khet mazdoor|khetihar|vyavasaya kooli|వ్యవసాయ కూలీ|వ్యవసాయ కూలి|खेतिहर|खेत मज़दूर|landless labou?r")),
    ("artisan", _rx(r"artisan|carpenter|blacksmith|potter|goldsmith|tailor|cobbler|weaver|barber|washerman|dhobi|mason|basket|sculptor|vishwakarma|వడ్రంగి|కుమ్మరి|చేనేత|కంసాలి|దర్జీ|मोची|दर्जी|कुम्हार|बढ़ई|लोहार|बुनकर")),
    ("student", _rx(r"student|studying|i study|college|vidyarthi|chaduvutunna|chadhuvutunna|చదువుతున్న|విద్యార్థి|छात्र|छात्रा|पढ़ रहा|पढ़ रही|पढ़ाई")),
    ("farmer", _rx(r"farmer|farming|kisan|kisaan|raithu|rythu|raitu|cultivat|tenant farmer|రైతు|రైతుని|వ్యవసాయం|किसान|खेती")),
    ("unorganised_worker", _rx(r"daily wage|labou?rer|construction worker|domestic worker|street vendor|auto driver|coolie|kooli|mazdoor|majdoor|కూలీ|కూలి|మేస్త్రి|मज़दूर|मजदूर|दिहाड़ी|रेहड़ी")),
    ("retired", _rx(r"retired|pensioner|రిటైర్|सेवानिवृत्त")),
    ("homemaker", _rx(r"homemaker|housewife|house wife|గృహిణి|गृहिणी")),
    ("salaried", _rx(r"salaried|private job|software|it employee|office job|company job|ఉద్యోగం చేస్తున్న|नौकरी करता|नौकरी करती")),
    ("self_employed", _rx(r"small business|shop|self[- ]employed|vyaparam|dukan|kirana|వ్యాపారం|దుకాణం|व्यापार|दुकान")),
]
GENDER = [
    ("female", _rx(r"\b(woman|women|female|lady|girl|mother|widow|wife|housewife|mahila|stree|aurat|amma)\b|మహిళ|స్త్రీ|తల్లి|వితంతువు|గృహిణి|महिला|औरत|माँ|विधवा|गृहिणी|लड़की")),
    ("transgender", _rx(r"\b(transgender|trans woman|trans man|hijra|kinnar)\b|ట్రాన్స్‌జెండర్|ट्रांसजेंडर|किन्नर")),
    ("male", _rx(r"\b(man|male|husband|father|purush|abbayi|boy)\b|పురుషుడు|అబ్బాయి|पुरुष|लड़का")),
]
CATEGORY = [
    ("ebc", _rx(r"\bebc\b|ఈబీసీ")),
    ("sc", _rx(r"\bsc\b|scheduled caste|dalit|ఎస్సీ|ఎస్‌సీ|అనుసూచిత కులం|अनुसूचित जाति|दलित")),
    ("st", _rx(r"\bst\b|scheduled tribe|tribal|adivasi|lambada|గిరిజన|ఎస్టీ|ఆదివాసీ|अनुसूचित जनजाति|आदिवासी")),
    ("bc", _rx(r"\bbc\b|\bobc\b|backward class|బీసీ|पिछड़ा|ओबीसी")),
    ("minority", _rx(r"minority|muslim|christian|sikh|parsi|jain|buddhist|ముస్లిం|క్రైస్తవ|మైనారిటీ|मुस्लिम|ईसाई|अल्पसंख्यक")),
    ("general", _rx(r"general category|\bgeneral\b|\boc\b|open category|forward caste|సామాన్య|सामान्य वर्ग")),
]
EDUCATION = [
    ("class_11_12", _rx(r"\binter\b|intermediate|class 1[12]|1[12]th|ఇంటర్|ఇంటర్మీడియట్|इंटर|11वीं|12वीं")),
    ("college", _rx(r"degree|b\.?tech|b\.?sc|b\.?com|b\.?a\b|engineering|graduation|m\.?tech|mba|mca|\bpg\b|polytechnic|diploma|college|university|డిగ్రీ|ఇంజనీరింగ్|కాలేజీ|डिग्री|कॉलेज|स्नातक")),
    ("below_11", _rx(r"class [1-9]\b|class 10|10th|ssc|tenth|పదో తరగతి|दसवीं")),
]
BOOLS: dict[str, re.Pattern] = {
    "has_bank_account": _rx(r"bank account|bank khata|bank passbook|jan dhan|బ్యాంకు ఖాతా|బ్యాంక్ ఖాతా|బ్యాంక్ అకౌంట్|बैंक खाता|बैंक अकाउंट"),
    "has_ration_card": _rx(r"ration card|white card|rice card|food security card|\bbpl\b|రేషన్ కార్డు|రేషన్ కార్డ్|తెల్ల కార్డు|తెల్ల రేషన్|राशन कार्ड|बीपीएल"),
    "owns_pucca_house": _rx(r"own house|own a house|pucca house|pakka house|pakka ghar|sontha illu|సొంత ఇల్లు|పక్కా ఇల్లు|पक्का घर|अपना घर|own home"),
    "has_lpg_connection": _rx(r"\blpg\b|gas connection|gas cylinder|cooking gas|గ్యాస్ కనెక్షన్|గ్యాస్ సిలిండర్|गैस कनेक्शन|गैस सिलेंडर"),
    "is_income_tax_payer": _rx(r"income tax|\bitr\b|tax payer|taxpayer|ఆదాయపు పన్ను|आयकर|इनकम टैक्स"),
    "is_govt_employee": _rx(r"government employee|govt employee|government job|govt job|sarkari naukri|ప్రభుత్వ ఉద్యోగి|ప్రభుత్వ ఉద్యోగం|सरकारी नौकरी|सरकारी कर्मचारी"),
    "has_mgnregs_job_card": _rx(r"mgnrega|mgnregs|nrega|job card|upadhi hami|ఉపాధి హామీ|జాబ్ కార్డు|मनरेगा|जॉब कार्ड"),
    "has_epf_esic_nps": _rx(r"\bepf\b|\bpf\b|\besic?\b|\bnps\b|provident fund"),
}
NO_HOUSE = _rx(r"no house|don'?t have (a )?house|houseless|homeless|kutcha|kachcha|rented house|rent house|kiraye|ఇల్లు లేదు|అద్దె ఇల్లు|అద్దెకు|घर नहीं|किराए|कच्चा")
NO_LAND = _rx(r"no land|landless|don'?t (own|have) (any )?land|bhoomi ledu|zameen nahi|భూమి లేదు|భూమి లేని|ज़मीन नहीं|जमीन नहीं|भूमिहीन")
DAUGHTER = _rx(r"daughter|beti|kuthuru|kooturu|ammayi|కూతురు|అమ్మాయి|बेटी")
MARRIAGE = _rx(r"marriage|wedding|married|shaadi|shadi|pelli|vivaham|పెళ్లి|వివాహం|शादी|विवाह")
SCHOOL_CHILD = _rx(r"(child|children|kids?|son|daughter|pillalu|బిడ్డ|పిల్లలు|బాబు|పాప|बच्चे|बच्चा|बेटा|बेटी)[^.]{0,40}(school|class|బడి|తరగతి|స్కూల్|स्कूल|कक्षा)")


def _num(s: str) -> float:
    return float(s.replace(",", ""))


def _window(text: str, start: int, end: int, before: int = 18, after: int = 28) -> str:
    return text[max(0, start - before):min(len(text), end + after)]


def _bool_fact(text: str, m: re.Match) -> bool | None:
    """Decide yes/no for a mentioned item: negation just before it ("no ration card", "don't have a ...") wins;
    otherwise the first have/negation word after it decides ("ration card undi", "ration card ledu"); otherwise a
    'have' earlier in the same clause carries over ("we have a ration card and an LPG connection")."""
    before = text[max(0, m.start() - 18):m.start()]
    if NEG.search(before):
        return False
    after = text[m.end():m.end() + 28]
    after = re.split(r"[,.;!?।]", after)[0]
    marks = sorted([(x.start(), False) for x in NEG.finditer(after)] + [(x.start(), True) for x in HAVE.finditer(after)])
    if marks:
        return marks[0][1]
    clause_start = max(text.rfind(c, 0, m.start()) for c in ".;!?।") + 1
    clause = text[clause_start:m.start()]
    if HAVE.search(clause) and not NEG.search(clause):
        return True
    return None


def _first(patterns, text):
    for value, rx in patterns:
        if m := rx.search(text):
            return value, m
    return None, None


FIRST_PERSON = _rx(r"\b(i|i'm|im|i am|my|me|mine|we|we're|our|us|myself|mera|meri|mere|mujhe|main|hum|hamara|hamari|"
                   r"nenu|naku|naaku|na|maa|memu|maaku|mammalni|ni|hoon|hun|hu)\b|నేను|నా|నాకు|మా|మేము|మాకు|ని(?=[\s,.!?]|$)|"
                   r"मैं|मेरा|मेरी|मेरे|मुझे|हम|हमारा|हमारी|हमारे|हूँ|हूं")


def is_about_self(text: str) -> bool:
    """Facts only count when the person talks about themselves ("I am a farmer"), not when they ask about a
    group ("is there a pension for unorganised workers?")."""
    return bool(FIRST_PERSON.search(text))


def extract_facts(text: str, pending: list[str] | None = None) -> list[Fact]:
    facts: dict[str, Fact] = {}
    t = text.strip()

    def put(field: str, value: Any, snippet: str, method: str = "pattern") -> None:
        try:
            v = coerce(field, value)
        except (ValueError, KeyError):
            return
        facts[field] = Fact(field, v, snippet.strip(), method)

    # --- land
    if m := ACRES.search(t):
        n = _num(m.group(1))
        if re.match(r"g", m.group(2), re.I) or "గుంట" in m.group(2):
            n = n / 40  # 40 guntas = 1 acre
        put("land_acres", round(n, 2), m.group(0))
    elif m := NO_LAND.search(t):
        put("land_acres", 0, m.group(0))

    # --- age
    if m := AGE.search(t):
        age = next(g for g in m.groups() if g)
        put("age", int(age), m.group(0))

    # --- income (money near an income keyword, or with lakh/thousand units)
    acre_span = ACRES.search(t).span() if ACRES.search(t) else None
    age_span = AGE.search(t).span() if AGE.search(t) else None
    for m in MONEY.finditer(t):
        span = m.span()
        if acre_span and span[0] >= acre_span[0] and span[0] < acre_span[1]:
            continue
        if age_span and span[0] >= age_span[0] and span[0] < age_span[1]:
            continue
        unit = (m.group(2) or "").lower()
        near = _window(t, m.start(), m.end(), 40, 30)
        if not unit and not INCOME_KW.search(near) and "₹" not in near and "rs" not in near.lower():
            continue
        value = _num(m.group(1)) * _MULT.get(unit, 1.0)
        if MONTHLY.search(_window(t, m.start(), m.end(), 5, 25)):
            value *= 12
        if value < 1000:  # "2 lakh" fine; bare small numbers are not incomes
            continue
        put("annual_income", int(value), m.group(0))
        break

    # --- categorical fields
    for field, patterns in (("state", STATE), ("area", AREA), ("occupation", OCCUPATION), ("gender", GENDER),
                            ("category", CATEGORY), ("education_level", EDUCATION)):
        value, m = _first(patterns, t)
        if value is not None:
            put(field, value, m.group(0))
    if facts.get("occupation") and facts["occupation"].value == "homemaker" and "gender" not in facts:
        put("gender", "female", facts["occupation"].source_text)
    if facts.get("occupation") and facts["occupation"].value == "student" and "education_level" not in facts:
        pass  # level asked later if it matters
    if facts.get("education_level") and "occupation" not in facts and facts["education_level"].value != "below_11":
        put("occupation", "student", facts["education_level"].source_text)

    # --- yes/no facts
    for field, rx in BOOLS.items():
        if m := rx.search(t):
            b = _bool_fact(t, m)
            if b is not None:
                put(field, b, _window(t, m.start(), m.end()))
    if "owns_pucca_house" not in facts and (m := NO_HOUSE.search(t)):
        put("owns_pucca_house", False, m.group(0))
    if m := DAUGHTER.search(t):
        win = _window(t, m.start(), m.end(), 5, 30)
        if MARRIAGE.search(win) and not NEG.search(win):
            put("has_daughter_marrying", True, win)
        elif (n := re.search(r"(\d{1,2})\s*(years?|yrs?|saal|ఏళ్ల|ఏళ్లు|साल|वर्ष)?", t[m.end():m.end() + 25])) and int(n.group(1)) < 10:
            put("has_daughter_under_10", True, win)
    if m := SCHOOL_CHILD.search(t):
        put("has_school_child", True, m.group(0))

    if not is_about_self(t) and not pending:
        facts.clear()  # a topic question, not a statement about the user
    # --- answers to pending questions ("1.5 lakh, yes")
    if pending:
        _answers_for_pending(t, pending, facts, put)
    return list(facts.values())


def _answers_for_pending(t: str, pending: list[str], facts: dict, put) -> None:
    parts = [p for p in re.split(r"[,;/]|\band\b|\baur\b|\bmariyu\b|మరియు|और", t) if p.strip()]
    remaining = [f for f in pending if f not in facts]
    bool_fields = [f for f in remaining if FIELDS[f].kind == "bool"]
    num_fields = [f for f in remaining if FIELDS[f].kind == "number"]
    choice_fields = [f for f in remaining if FIELDS[f].kind == "choice"]
    for p in parts:
        ps = p.strip()
        if bool_fields and (YES.search(ps) or NO.search(ps)):
            put(bool_fields.pop(0), bool(YES.search(ps)) and not NO.search(ps), ps, "answer")
            continue
        if num_fields and (m := MONEY.search(ps)):
            f = num_fields.pop(0)
            unit = (m.group(2) or "").lower()
            v = _num(m.group(1)) * (_MULT.get(unit, 1.0) if f == "annual_income" else 1.0)
            if f == "annual_income" and MONTHLY.search(ps):
                v *= 12
            put(f, v, ps, "answer")
            continue
        for f in list(choice_fields):
            for o in FIELDS[f].options:
                labels = [str(o.value).replace("_", " ")] + list(o.label.values())
                if any(lbl.lower() in ps.lower() or ps.lower() in lbl.lower() for lbl in labels if len(ps) > 1):
                    put(f, o.value, ps, "answer")
                    choice_fields.remove(f)
                    break
            else:
                continue
            break


LLM_PROMPT = """Extract profile facts from this message to an Indian government-scheme assistant. The message may be
English, Hindi, Telugu, romanised, or mixed. Return JSON {{"facts": [{{"field": ..., "value": ..., "quote": ...}}]}}.
Only include facts the user clearly stated about themselves/their family. "quote" must be copied from the message.
Allowed fields and values:
{spec}
Never extract Aadhaar, bank account or phone numbers.
Message: {text}"""


async def extract_with_llm(text: str) -> list[Fact]:
    from .. import llm

    if not llm.available():
        return []
    spec = "\n".join(
        f"- {f.name}: {f.kind}" + (f" one of {[o.value for o in f.options]}" if f.kind == "choice" else "")
        + (" (₹ per year; convert lakh/monthly)" if f.name == "annual_income" else "")
        for f in FIELDS.values())
    data = await llm.complete_json(LLM_PROMPT.format(spec=spec, text=text))
    out = []
    for item in (data or {}).get("facts", []) if isinstance(data, dict) else []:
        try:
            if item.get("quote") and item["quote"] not in text:
                continue
            out.append(Fact(item["field"], coerce(item["field"], item["value"]), item.get("quote", ""), "llm"))
        except (KeyError, ValueError, TypeError):
            continue
    return out
