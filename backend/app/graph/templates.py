"""Answer text templates in en / hi / te. Numbers and eligibility come from the rule engine, never the LLM."""
from __future__ import annotations

T = lambda en, hi, te: {"en": en, "hi": hi, "te": te}  # noqa: E731

DISCLAIMER = T(
    "Haathi is not a government service. Please confirm on the official portal before you apply.",
    "हाथी कोई सरकारी सेवा नहीं है। आवेदन से पहले आधिकारिक पोर्टल पर पुष्टि करें।",
    "హాథీ ప్రభుత్వ సేవ కాదు. దరఖాస్తు చేసే ముందు అధికారిక పోర్టల్‌లో నిర్ధారించుకోండి.",
)
GREETING = T(
    "Namaste! I'm Haathi 🐘. Tell me a little about yourself (for example: \"I'm a farmer in Telangana with 2 acres\") and I'll find government schemes you may be eligible for, with proof from the official rules.",
    "नमस्ते! मैं हाथी 🐘 हूँ। अपने बारे में थोड़ा बताइए (जैसे: \"मैं तेलंगाना में 2 एकड़ वाला किसान हूँ\"), मैं आपके लिए सरकारी योजनाएँ ढूँढूँगा, आधिकारिक नियमों के सबूत के साथ।",
    "నమస్తే! నేను హాథీ 🐘. మీ గురించి కొంచెం చెప్పండి (ఉదా: \"నేను తెలంగాణలో 2 ఎకరాల రైతుని\"), మీకు అర్హత ఉన్న ప్రభుత్వ పథకాలను అధికారిక నియమాల ఆధారంతో వెతికి చెబుతాను.",
)
THANKS = T("You're welcome! Ask me anything else about schemes.", "आपका स्वागत है! योजनाओं के बारे में और कुछ भी पूछिए।", "సంతోషం! పథకాల గురించి ఇంకేమైనా అడగండి.")
ASK_INTRO = T("To check the right schemes, {n} quick question{s}:", "सही योजनाएँ जाँचने के लिए {n} छोटे सवाल:", "సరైన పథకాలు చూడటానికి {n} చిన్న ప్రశ్నలు:")
SO_FAR = T("So far: {e} likely, {m} still to check.", "अब तक: {e} संभावित, {m} जाँचनी बाकी।", "ఇప్పటివరకు: {e} అర్హత ఉండొచ్చు, ఇంకా {m} చూడాలి.")
ELIGIBLE_HEAD = T("You're likely eligible for {n} scheme{s}:", "आप {n} योजनाओं के लिए संभवतः पात्र हैं:", "మీరు {n} పథకాలకు అర్హులు కావచ్చు:")
ELIGIBLE_ONE = T("You're likely eligible for {name}.", "आप {name} के लिए संभवतः पात्र हैं।", "మీరు {name}కు అర్హులు కావచ్చు.")
MAYBE_HEAD = T("Need a little more information: {names}.", "थोड़ी और जानकारी चाहिए: {names}।", "ఇంకొంచెం సమాచారం కావాలి: {names}.")
NONE_FOUND = T("I couldn't find a scheme you clearly qualify for yet, but you're close on some.",
               "अभी कोई योजना नहीं मिली जिसके आप साफ़ तौर पर पात्र हों, पर कुछ के बहुत करीब हैं।",
               "మీకు స్పష్టంగా అర్హత ఉన్న పథకం ఇంకా దొరకలేదు, కానీ కొన్నింటికి దగ్గరగా ఉన్నారు.")
NONE_AT_ALL = T("I couldn't find a matching scheme in my current list. Please check myScheme or your Mee Seva centre.",
                "मेरी मौजूदा सूची में कोई मेल खाती योजना नहीं मिली। कृपया myScheme या मी सेवा केंद्र देखें।",
                "నా ప్రస్తుత జాబితాలో సరిపోయే పథకం దొరకలేదు. దయచేసి myScheme లేదా మీ సేవా కేంద్రాన్ని సంప్రదించండి.")
ALMOST = T("Almost eligible:", "लगभग पात्र:", "దాదాపు అర్హులు:")
DOCS = T("Documents to bring: {docs}.", "साथ लाने वाले दस्तावेज़: {docs}।", "తీసుకెళ్లాల్సిన పత్రాలు: {docs}.")
BENEFIT = T("{name}: {benefit}", "{name}: {benefit}", "{name}: {benefit}")
DOCS_FOR = T("Documents for {name}: {docs}.", "{name} के लिए दस्तावेज़: {docs}।", "{name}కు కావాల్సిన పత్రాలు: {docs}.")
APPLY_FOR = T("How to apply for {name}: {how}", "{name} के लिए आवेदन कैसे करें: {how}", "{name}కు ఎలా దరఖాస్తు చేయాలి: {how}")
ELIG_FOR = T("Who can get {name}: {rules}.", "{name} किसे मिल सकता है: {rules}।", "{name} ఎవరికి వస్తుంది: {rules}.")
RENAMED = T("Note: “{old}” has been replaced by {name} (changed on {date}).", "ध्यान दें: “{old}” की जगह अब {name} है ({date} से)।", "గమనిక: “{old}” స్థానంలో ఇప్పుడు {name} ఉంది ({date} నుండి).")
CHANGED = T("This rule changed on {date}: {note}", "यह नियम {date} को बदला: {note}", "ఈ నియమం {date}న మారింది: {note}")
UNSURE = T("I'm not sure about this one, and I'd rather not guess. Please check the official sources below.",
           "मुझे इसके बारे में पक्का नहीं पता, और मैं अंदाज़ा नहीं लगाना चाहता। कृपया नीचे दिए आधिकारिक स्रोत देखें।",
           "దీని గురించి నాకు ఖచ్చితంగా తెలియదు, ఊహించి చెప్పడం ఇష్టం లేదు. దయచేసి కింది అధికారిక వనరులు చూడండి.")
EXTRACTIVE_NOTE = T("", "(आधिकारिक पाठ अंग्रेज़ी में है)", "(అధికారిక పాఠం ఇంగ్లీషులో ఉంది)")
STATUS = {
    "eligible": T("Likely eligible", "संभवतः पात्र", "అర్హత ఉండొచ్చు"),
    "maybe": T("Need more info", "और जानकारी चाहिए", "మరింత సమాచారం కావాలి"),
    "not_eligible": T("Not eligible", "पात्र नहीं", "అర్హత లేదు"),
}

OFFICIAL_LINKS = [
    {"label": "myScheme (Government of India)", "url": "https://www.myscheme.gov.in"},
    {"label": "Telangana Government portal", "url": "https://www.telangana.gov.in"},
    {"label": "Andhra Pradesh Government portal", "url": "https://www.ap.gov.in"},
]


def plural(n: int, lang: str) -> str:
    return "" if n == 1 or lang != "en" else "s"


def join(items: list[str], lang: str) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    conj = {"en": " and ", "hi": " और ", "te": " మరియు "}[lang]
    return ", ".join(items[:-1]) + conj + items[-1]
