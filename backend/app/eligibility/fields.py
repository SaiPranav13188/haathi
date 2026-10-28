"""Profile fields: type, question wording (en/hi/te), answer options, and priors used by smart questioning.

Priors are rough population shares for the target users (Telangana-first, then Andhra Pradesh). They only
steer *which question to ask next*; they never influence an eligibility decision.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


def T(en: str, hi: str, te: str) -> dict[str, str]:
    return {"en": en, "hi": hi, "te": te}


@dataclass
class Option:
    value: Any
    label: dict[str, str]
    prior: float


@dataclass
class FieldSpec:
    name: str
    kind: Literal["number", "bool", "choice"]
    question: dict[str, str]
    label: dict[str, str]
    options: list[Option] = field(default_factory=list)  # choice/bool options, or number buckets (value = representative)
    unit: dict[str, str] | None = None
    min: float | None = None
    max: float | None = None
    step: float | None = None
    help: dict[str, str] | None = None


YES = T("Yes", "हाँ", "అవును")
NO = T("No", "नहीं", "కాదు")


def _bool(name: str, question: dict, label: dict, p_yes: float, help: dict | None = None) -> FieldSpec:
    return FieldSpec(name, "bool", question, label, [Option(True, YES, p_yes), Option(False, NO, 1 - p_yes)], help=help)


FIELDS: dict[str, FieldSpec] = {}


def _add(spec: FieldSpec) -> None:
    FIELDS[spec.name] = spec


_add(FieldSpec(
    "state", "choice",
    T("Which state do you live in?", "आप किस राज्य में रहते हैं?", "మీరు ఏ రాష్ట్రంలో ఉంటున్నారు?"),
    T("State", "राज्य", "రాష్ట్రం"),
    [Option("Telangana", T("Telangana", "तेलंगाना", "తెలంగాణ"), 0.6),
     Option("Andhra Pradesh", T("Andhra Pradesh", "आंध्र प्रदेश", "ఆంధ్రప్రదేశ్"), 0.3),
     Option("Other", T("Other state", "अन्य राज्य", "ఇతర రాష్ట్రం"), 0.1)],
))
_add(FieldSpec(
    "area", "choice",
    T("Do you live in a village or a town/city?", "आप गाँव में रहते हैं या शहर में?", "మీరు గ్రామంలో ఉంటారా, పట్టణంలోనా?"),
    T("Area", "क्षेत्र", "ప్రాంతం"),
    [Option("rural", T("Village (rural)", "गाँव (ग्रामीण)", "గ్రామం (గ్రామీణ)"), 0.6),
     Option("urban", T("Town / city (urban)", "शहर (शहरी)", "పట్టణం / నగరం"), 0.4)],
))
_add(FieldSpec(
    "age", "number",
    T("How old are you?", "आपकी उम्र कितनी है?", "మీ వయస్సు ఎంత?"),
    T("Age", "उम्र", "వయస్సు"),
    [Option(12, T("Under 18", "18 से कम", "18 లోపు"), 0.08), Option(30, T("18–40", "18–40", "18–40"), 0.42),
     Option(48, T("41–50", "41–50", "41–50"), 0.17), Option(55, T("51–56", "51–56", "51–56"), 0.1),
     Option(65, T("57–69", "57–69", "57–69"), 0.15), Option(75, T("70+", "70+", "70+"), 0.08)],
    unit=T("years", "वर्ष", "సంవత్సరాలు"), min=0, max=110, step=1,
))
_add(FieldSpec(
    "gender", "choice",
    T("What is your gender?", "आपका लिंग क्या है?", "మీ లింగం ఏమిటి?"),
    T("Gender", "लिंग", "లింగం"),
    [Option("female", T("Woman", "महिला", "స్త్రీ"), 0.49), Option("male", T("Man", "पुरुष", "పురుషుడు"), 0.5),
     Option("transgender", T("Transgender", "ट्रांसजेंडर", "ట్రాన్స్‌జెండర్"), 0.01)],
))
_add(FieldSpec(
    "annual_income", "number",
    T("What is your family's total yearly income?", "आपके परिवार की कुल सालाना आय कितनी है?", "మీ కుటుంబ మొత్తం వార్షిక ఆదాయం ఎంత?"),
    T("Family yearly income", "परिवार की सालाना आय", "కుటుంబ వార్షిక ఆదాయం"),
    [Option(100000, T("Up to ₹1.5 lakh", "₹1.5 लाख तक", "₹1.5 లక్షల వరకు"), 0.4),
     Option(180000, T("₹1.5–2 lakh", "₹1.5–2 लाख", "₹1.5–2 లక్షలు"), 0.2),
     Option(240000, T("₹2–2.5 lakh", "₹2–2.5 लाख", "₹2–2.5 లక్షలు"), 0.1),
     Option(500000, T("₹2.5–9 lakh", "₹2.5–9 लाख", "₹2.5–9 లక్షలు"), 0.22),
     Option(1200000, T("Above ₹9 lakh", "₹9 लाख से ज़्यादा", "₹9 లక్షలకు పైగా"), 0.08)],
    unit=T("₹ per year", "₹ प्रति वर्ष", "₹ ఏటా"), min=0, max=10_000_000, step=5000,
    help=T("Add up the income of everyone in the family.", "परिवार के सभी सदस्यों की आय जोड़ें।", "కుటుంబ సభ్యులందరి ఆదాయాన్ని కలపండి."),
))
_add(FieldSpec(
    "occupation", "choice",
    T("What work do you mainly do?", "आप मुख्य रूप से क्या काम करते हैं?", "మీరు ప్రధానంగా ఏ పని చేస్తారు?"),
    T("Occupation", "पेशा", "వృత్తి"),
    [Option("farmer", T("Farmer (own / lease land)", "किसान (अपनी / पट्टे की ज़मीन)", "రైతు (సొంత / కౌలు భూమి)"), 0.3),
     Option("agri_labourer", T("Farm labourer", "खेतिहर मज़दूर", "వ్యవసాయ కూలీ"), 0.12),
     Option("unorganised_worker", T("Daily wage / unorganised worker", "दिहाड़ी / असंगठित श्रमिक", "రోజువారీ కూలీ / అసంఘటిత కార్మికుడు"), 0.12),
     Option("artisan", T("Artisan / craftsperson", "कारीगर / शिल्पकार", "చేతివృత్తి కళాకారుడు"), 0.05),
     Option("student", T("Student", "छात्र", "విద్యార్థి"), 0.12),
     Option("self_employed", T("Small business / self-employed", "छोटा व्यवसाय / स्वरोज़गार", "చిన్న వ్యాపారం / స్వయం ఉపాధి"), 0.08),
     Option("salaried", T("Salaried job", "नौकरी (वेतन)", "జీతం ఉద్యోగం"), 0.08),
     Option("homemaker", T("Homemaker", "गृहिणी", "గృహిణి"), 0.08),
     Option("retired", T("Retired / not working", "सेवानिवृत्त / काम नहीं", "పదవీ విరమణ / పని లేదు"), 0.05)],
))
_add(FieldSpec(
    "land_acres", "number",
    T("How many acres of farm land does your family own?", "आपके परिवार के पास कितने एकड़ खेती की ज़मीन है?", "మీ కుటుంబానికి ఎన్ని ఎకరాల వ్యవసాయ భూమి ఉంది?"),
    T("Land owned", "ज़मीन", "భూమి"),
    [Option(0, T("No land", "ज़मीन नहीं", "భూమి లేదు"), 0.45), Option(1.5, T("Up to 2.5 acres", "2.5 एकड़ तक", "2.5 ఎకరాల వరకు"), 0.3),
     Option(4, T("2.5–5 acres", "2.5–5 एकड़", "2.5–5 ఎకరాలు"), 0.15), Option(8, T("More than 5 acres", "5 एकड़ से ज़्यादा", "5 ఎకరాలకు పైగా"), 0.1)],
    unit=T("acres", "एकड़", "ఎకరాలు"), min=0, max=500, step=0.25,
))
_add(FieldSpec(
    "category", "choice",
    T("Which social category does your family belong to?", "आपका परिवार किस सामाजिक वर्ग से है?", "మీ కుటుంబం ఏ సామాజిక వర్గానికి చెందినది?"),
    T("Category", "वर्ग", "వర్గం"),
    [Option("sc", T("SC", "अनुसूचित जाति (SC)", "ఎస్సీ (SC)"), 0.16), Option("st", T("ST", "अनुसूचित जनजाति (ST)", "ఎస్టీ (ST)"), 0.1),
     Option("bc", T("BC / OBC", "पिछड़ा वर्ग (BC / OBC)", "బీసీ (BC / OBC)"), 0.45), Option("ebc", T("EBC", "आर्थिक रूप से पिछड़ा (EBC)", "ఈబీసీ (EBC)"), 0.05),
     Option("minority", T("Minority", "अल्पसंख्यक", "మైనారిటీ"), 0.12), Option("general", T("General", "सामान्य", "జనరల్"), 0.12)],
))
_add(_bool("has_bank_account", T("Do you have a bank account linked to Aadhaar?", "क्या आपका आधार से जुड़ा बैंक खाता है?", "మీకు ఆధార్‌తో లింక్ అయిన బ్యాంకు ఖాతా ఉందా?"),
           T("Bank account (Aadhaar-linked)", "बैंक खाता (आधार से जुड़ा)", "బ్యాంకు ఖాతా (ఆధార్ లింక్)"), 0.85,
           T("We never ask for your account number.", "हम कभी खाता नंबर नहीं माँगते।", "మేము మీ ఖాతా నంబర్ ఎప్పుడూ అడగము.")))
_add(_bool("has_ration_card", T("Does your family have a white ration card (food security card)?", "क्या आपके परिवार के पास सफ़ेद / बीपीएल राशन कार्ड है?", "మీ కుటుంబానికి తెల్ల రేషన్ కార్డు (ఆహార భద్రత కార్డు) ఉందా?"),
           T("White ration card", "सफ़ेद / बीपीएल राशन कार्ड", "తెల్ల రేషన్ కార్డు"), 0.7))
_add(_bool("is_income_tax_payer", T("Does anyone in your family pay income tax?", "क्या आपके परिवार में कोई आयकर देता है?", "మీ కుటుంబంలో ఎవరైనా ఆదాయపు పన్ను చెల్లిస్తారా?"),
           T("Income tax payer in family", "परिवार में आयकरदाता", "కుటుంబంలో పన్ను చెల్లింపుదారు"), 0.12))
_add(_bool("is_govt_employee", T("Is anyone in your family a government employee or pensioner?", "क्या परिवार में कोई सरकारी कर्मचारी या पेंशनभोगी है?", "మీ కుటుంబంలో ఎవరైనా ప్రభుత్వ ఉద్యోగి లేదా పింఛనుదారు ఉన్నారా?"),
           T("Govt employee / pensioner in family", "परिवार में सरकारी कर्मचारी / पेंशनभोगी", "కుటుంబంలో ప్రభుత్వ ఉద్యోగి / పింఛనుదారు"), 0.08))
_add(_bool("owns_pucca_house", T("Does your family own a pucca (brick/concrete) house?", "क्या आपके परिवार का अपना पक्का घर है?", "మీ కుటుంబానికి సొంత పక్కా ఇల్లు ఉందా?"),
           T("Owns a pucca house", "पक्का घर है", "పక్కా ఇల్లు ఉంది"), 0.55))
_add(_bool("has_lpg_connection", T("Does your household have an LPG gas connection?", "क्या आपके घर में एलपीजी गैस कनेक्शन है?", "మీ ఇంట్లో LPG గ్యాస్ కనెక్షన్ ఉందా?"),
           T("LPG connection", "एलपीजी कनेक्शन", "LPG కనెక్షన్"), 0.75))
_add(_bool("has_daughter_under_10", T("Do you have a daughter below 10 years of age?", "क्या आपकी 10 साल से कम उम्र की बेटी है?", "మీకు 10 ఏళ్ల లోపు కూతురు ఉందా?"),
           T("Daughter under 10", "10 से कम उम्र की बेटी", "10 ఏళ్ల లోపు కూతురు"), 0.15))
_add(_bool("has_school_child", T("Do you have a child studying in Class 1 to 12?", "क्या आपका कोई बच्चा कक्षा 1 से 12 में पढ़ता है?", "మీ పిల్లల్లో ఎవరైనా 1 నుండి 12వ తరగతి చదువుతున్నారా?"),
           T("Child in Class 1–12", "कक्षा 1–12 में बच्चा", "1–12 తరగతిలో బిడ్డ"), 0.4))
_add(_bool("has_daughter_marrying", T("Is your daughter (18 or older) getting married soon?", "क्या आपकी बेटी (18 या उससे अधिक) की शादी जल्द होने वाली है?", "మీ కూతురు (18 ఏళ్లు నిండిన) పెళ్లి త్వరలో జరగబోతోందా?"),
           T("Daughter's marriage soon", "बेटी की शादी जल्द", "త్వరలో కూతురి పెళ్లి"), 0.08))
_add(_bool("has_epf_esic_nps", T("Are you a member of EPF, ESIC or NPS?", "क्या आप EPF, ESIC या NPS के सदस्य हैं?", "మీరు EPF, ESIC లేదా NPS సభ్యులా?"),
           T("EPF / ESIC / NPS member", "EPF / ESIC / NPS सदस्य", "EPF / ESIC / NPS సభ్యులు"), 0.15))
_add(_bool("has_mgnregs_job_card", T("Did your family work under MGNREGS (job card, 20+ days) last year?", "क्या आपके परिवार ने पिछले साल मनरेगा में (जॉब कार्ड, 20+ दिन) काम किया?", "మీ కుటుంబం గత ఏడాది ఉపాధి హామీ పథకంలో (జాబ్ కార్డు, 20+ రోజులు) పని చేసిందా?"),
           T("MGNREGS work (20+ days)", "मनरेगा काम (20+ दिन)", "ఉపాధి హామీ పని (20+ రోజులు)"), 0.35))
_add(FieldSpec(
    "education_level", "choice",
    T("Are you studying now? Which level?", "क्या आप अभी पढ़ रहे हैं? किस स्तर पर?", "మీరు ఇప్పుడు చదువుతున్నారా? ఏ స్థాయి?"),
    T("Studying", "पढ़ाई", "చదువు"),
    [Option("below_11", T("Class 10 or below", "कक्षा 10 या नीचे", "10వ తరగతి లేదా తక్కువ"), 0.1),
     Option("class_11_12", T("Intermediate (Class 11–12)", "इंटरमीडिएट (कक्षा 11–12)", "ఇంటర్మీడియట్ (11–12)"), 0.08),
     Option("college", T("Degree / college / PG", "डिग्री / कॉलेज / पीजी", "డిగ్రీ / కాలేజీ / పీజీ"), 0.1),
     Option("not_studying", T("Not studying", "नहीं पढ़ रहे", "చదవడం లేదు"), 0.72)],
))

# Order used by the "fixed questionnaire" baseline (myScheme-style: same order for everyone).
FIXED_ORDER = [
    "state", "area", "gender", "age", "category", "occupation", "annual_income", "land_acres", "education_level",
    "has_bank_account", "has_ration_card", "is_income_tax_payer", "is_govt_employee", "owns_pucca_house",
    "has_lpg_connection", "has_daughter_under_10", "has_school_child", "has_daughter_marrying",
    "has_epf_esic_nps", "has_mgnregs_job_card",
]
assert set(FIXED_ORDER) == set(FIELDS), set(FIELDS) ^ set(FIXED_ORDER)


def coerce(field_name: str, value: Any) -> Any:
    """Normalise a raw answer into the field's type. Raises ValueError on bad input."""
    spec = FIELDS[field_name]
    if spec.kind == "number":
        v = float(value)
        if spec.min is not None and v < spec.min or spec.max is not None and v > spec.max:
            raise ValueError(f"{field_name} out of range")
        return int(v) if v.is_integer() else v
    if spec.kind == "bool":
        if isinstance(value, bool):
            return value
        s = str(value).strip().lower()
        if s in {"true", "yes", "1", "y"}:
            return True
        if s in {"false", "no", "0", "n"}:
            return False
        raise ValueError(f"{field_name}: not a yes/no value")
    allowed = [o.value for o in spec.options]
    if value not in allowed:
        raise ValueError(f"{field_name}: {value!r} not in {allowed}")
    return value


def spec_json(name: str, lang: str = "en") -> dict:
    s = FIELDS[name]
    return {
        "field": s.name, "kind": s.kind,
        "question": s.question.get(lang, s.question["en"]), "label": s.label.get(lang, s.label["en"]),
        "options": [] if s.kind == "number" else [{"value": o.value, "label": o.label.get(lang, o.label["en"])} for o in s.options],
        "buckets": [{"value": o.value, "label": o.label.get(lang, o.label["en"])} for o in s.options] if s.kind == "number" else [],
        "unit": (s.unit or {}).get(lang) if s.unit else None,
        "min": s.min, "max": s.max, "step": s.step,
        "help": s.help.get(lang, s.help["en"]) if s.help else None,
    }
