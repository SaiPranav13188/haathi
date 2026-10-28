"""Human-readable explanations (en / hi / te) for rules, what-if results and documents."""
from __future__ import annotations

from typing import Any

from .dsl import Rule
from .fields import FIELDS, T

DOCUMENTS: dict[str, dict[str, str]] = {
    "aadhaar": T("Aadhaar card", "आधार कार्ड", "ఆధార్ కార్డు"),
    "land_record": T("Land record (pattadar passbook)", "भूमि रिकॉर्ड (पट्टादार पासबुक)", "భూ రికార్డు (పట్టాదారు పాస్‌బుక్)"),
    "bank_passbook": T("Bank passbook", "बैंक पासबुक", "బ్యాంకు పాస్‌బుక్"),
    "ration_card": T("White ration card", "सफ़ेद राशन कार्ड", "తెల్ల రేషన్ కార్డు"),
    "job_card": T("MGNREGS job card", "मनरेगा जॉब कार्ड", "ఉపాధి హామీ జాబ్ కార్డు"),
    "nominee_aadhaar": T("Nominee's Aadhaar", "नामांकित का आधार", "నామినీ ఆధార్"),
    "caste_certificate": T("Caste certificate", "जाति प्रमाण पत्र", "కుల ధృవీకరణ పత్రం"),
    "community_certificate": T("Community certificate", "समुदाय प्रमाण पत्र", "సామాజిక వర్గ ధృవీకరణ పత్రం"),
    "income_certificate": T("Income certificate", "आय प्रमाण पत्र", "ఆదాయ ధృవీకరణ పత్రం"),
    "age_proof": T("Age proof", "आयु प्रमाण", "వయస్సు రుజువు"),
    "marriage_proof": T("Marriage invitation / certificate", "शादी का निमंत्रण / प्रमाण पत्र", "పెళ్లి పత్రిక / ధృవీకరణ పత్రం"),
    "electricity_number": T("Electricity service number", "बिजली सेवा नंबर", "విద్యుత్ సర్వీస్ నంబర్"),
    "lpg_number": T("LPG consumer number", "एलपीजी उपभोक्ता नंबर", "LPG వినియోగదారు నంబర్"),
    "site_document": T("House site (plot) document", "प्लॉट का दस्तावेज़", "ఇంటి స్థలం పత్రం"),
    "sowing_certificate": T("Sowing certificate", "बुवाई प्रमाण पत्र", "విత్తన ధృవీకరణ పత్రం"),
    "photo": T("Passport size photo", "पासपोर्ट साइज़ फ़ोटो", "పాస్‌పోర్ట్ సైజు ఫోటో"),
    "birth_certificate": T("Birth certificate of the girl", "बेटी का जन्म प्रमाण पत्र", "అమ్మాయి జనన ధృవీకరణ పత్రం"),
    "address_proof": T("Address proof", "पते का प्रमाण", "చిరునామా రుజువు"),
    "marks_memo": T("Previous year marks memo", "पिछले साल की अंकसूची", "గత సంవత్సరం మార్కుల మెమో"),
    "study_certificate": T("School study certificate", "स्कूल अध्ययन प्रमाण पत्र", "పాఠశాల స్టడీ సర్టిఫికేట్"),
}


def doc_label(key: str, lang: str) -> str:
    d = DOCUMENTS.get(key)
    return d.get(lang, d["en"]) if d else key.replace("_", " ").title()


def inr(n: float) -> str:
    """Indian digit grouping: 150000 -> ₹1,50,000."""
    n = int(round(n))
    s = str(abs(n))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts) + "," + tail
    return ("-" if n < 0 else "") + "₹" + s


def _fmt_value(field: str, value: Any, lang: str) -> str:
    spec = FIELDS.get(field)
    if spec is None:
        return str(value)
    if spec.kind == "bool":
        return {True: T("Yes", "हाँ", "అవును"), False: T("No", "नहीं", "కాదు")}[bool(value)][lang]
    if spec.kind == "choice":
        for o in spec.options:
            if o.value == value:
                return o.label.get(lang, o.label["en"])
        return str(value)
    if field == "annual_income":
        return inr(value)
    unit = (spec.unit or {}).get(lang, "")
    v = int(value) if float(value).is_integer() else value
    return f"{v} {unit}".strip()


_OPS = {
    "lte": T("{f} up to {v}", "{f} {v} तक", "{f} {v} వరకు"),
    "lt": T("{f} below {v}", "{f} {v} से कम", "{f} {v} కంటే తక్కువ"),
    "gte": T("{f} {v} or more", "{f} {v} या अधिक", "{f} {v} లేదా ఎక్కువ"),
    "gt": T("{f} more than {v}", "{f} {v} से अधिक", "{f} {v} కంటే ఎక్కువ"),
    "between": T("{f} between {lo} and {hi}", "{f} {lo} से {hi} के बीच", "{f} {lo} నుండి {hi} మధ్య"),
    "eq": T("{f}: {v}", "{f}: {v}", "{f}: {v}"),
    "neq": T("{f}: not {v}", "{f}: {v} नहीं", "{f}: {v} కాదు"),
    "in": T("{f}: {v}", "{f}: {v}", "{f}: {v}"),
    "not_in": T("{f}: not {v}", "{f}: {v} नहीं", "{f}: {v} కాదు"),
    "exists": T("{f}", "{f}", "{f}"),
}


def rule_label(rule: Rule, lang: str = "en") -> str:
    spec = FIELDS.get(rule.field)
    f = spec.label.get(lang, spec.label["en"]) if spec else rule.field
    # special-case land "> 0" to read naturally
    if rule.field == "land_acres" and rule.op == "gt" and rule.value == 0:
        return T("Owns farm land", "खेती की ज़मीन है", "వ్యవసాయ భూమి ఉంది")[lang]
    if rule.field == "land_acres" and rule.op == "lte" and rule.value == 0:
        return T("Owns no farm land", "खेती की ज़मीन नहीं", "వ్యవసాయ భూమి లేదు")[lang]
    tmpl = _OPS[rule.op][lang]
    if rule.op == "between":
        lo, hi = rule.value
        return tmpl.format(f=f, lo=_fmt_value(rule.field, lo, lang), hi=_fmt_value(rule.field, hi, lang))
    if rule.op in {"in", "not_in"}:
        sep = {"en": " or ", "hi": " या ", "te": " లేదా "}[lang]
        v = sep.join(_fmt_value(rule.field, x, lang) for x in rule.value)
    else:
        v = _fmt_value(rule.field, rule.value, lang)
    return tmpl.format(f=f, v=v)


def value_label(field: str, value: Any, lang: str) -> str:
    return _fmt_value(field, value, lang) if value is not None else "—"


def what_if_text(w: dict, scheme_name: str, lang: str) -> str:
    field, th, cur = w["field"], w["threshold"], w["current"]
    if isinstance(th, list):
        th = th[0] if w["direction"] in {"higher", "reach"} else th[1]
    tv, cv = _fmt_value(field, th, lang), _fmt_value(field, cur, lang)
    if field == "age" and w["direction"] == "reach":
        return T(f"You'd qualify for {scheme_name} when you turn {int(th)}.",
                 f"{int(th)} वर्ष के होने पर आप {scheme_name} के पात्र होंगे।",
                 f"మీకు {int(th)} ఏళ్లు నిండగానే {scheme_name}కు అర్హులవుతారు.")[lang]
    spec = FIELDS[field]
    f = spec.label.get(lang, spec.label["en"])
    if w["direction"] == "lower":
        return T(f"You'd qualify for {scheme_name} if your {f.lower()} were {tv} or less (now {cv}).",
                 f"अगर आपकी {f} {tv} या कम होती (अभी {cv}), तो आप {scheme_name} के पात्र होते।",
                 f"మీ {f} {tv} లేదా తక్కువ ఉంటే (ఇప్పుడు {cv}) మీరు {scheme_name}కు అర్హులు.")[lang]
    return T(f"You'd qualify for {scheme_name} if your {f.lower()} were above {tv} (now {cv}).",
             f"अगर आपकी {f} {tv} से अधिक होती (अभी {cv}), तो आप {scheme_name} के पात्र होते।",
             f"మీ {f} {tv} కంటే ఎక్కువ ఉంటే (ఇప్పుడు {cv}) మీరు {scheme_name}కు అర్హులు.")[lang]
