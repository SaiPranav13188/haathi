import pytest

from app.language.detect import detect
from app.language.facts import extract_facts
from app.language.intent import classify
from app.language.translate import glossary_translate


def facts(text, pending=None):
    return {f.field: f.value for f in extract_facts(text, pending)}


@pytest.mark.parametrize("text,lang,romanized", [
    ("I am a farmer in Telangana", "en", False),
    ("What is the benefit of PM-KISAN?", "en", False),
    ("mera income 2 lakh hai", "hi", True),
    ("nenu raithu ni, naku 2 ekaralu undi", "te", True),
    ("నేను తెలంగాణలో రైతుని", "te", False),
    ("मैं किसान हूँ", "hi", False),
])
def test_detect(text, lang, romanized):
    info = detect(text)
    assert info.lang == lang and info.romanized == romanized


def test_code_mixed_flag():
    assert detect("నాకు PM Kisan scheme గురించి చెప్పండి").code_mixed


def test_spec_example_telugu_voice():
    f = facts("నేను తెలంగాణలో రైతుని, 2 ఎకరాల భూమి ఉంది")
    assert f["state"] == "Telangana" and f["occupation"] == "farmer" and f["land_acres"] == 2


def test_spec_followup_answer():
    f = facts("1.5 lakh, yes", pending=["annual_income", "has_bank_account"])
    assert f["annual_income"] == 150000 and f["has_bank_account"] is True


@pytest.mark.parametrize("text,field,value", [
    ("mera income 2 lakh hai", "annual_income", 200000),
    ("I earn 15000 per month", "annual_income", 180000),
    ("మా ఆదాయం 1.2 లక్షలు", "annual_income", 120000),
    ("मेरी आय 80 हज़ार है", "annual_income", 80000),
    ("I am 62 years old", "age", 62),
    ("నా వయస్సు 58", "age", 58),
    ("we don't have a ration card", "has_ration_card", False),
    ("मैं हैदराबाद में रहती हूँ", "state", "Telangana"),
    ("we have a white ration card", "has_ration_card", True),
    ("I don't own any land", "land_acres", 0),
    ("we live in a rented house", "owns_pucca_house", False),
    ("I'm a widow living in Warangal", "gender", "female"),
    ("10 guntas land is all I have", "land_acres", 0.25),
    ("I'm a widow living in Warangal", "state", "Telangana"),
    ("I am SC student doing B.Tech", "category", "sc"),
    ("I am SC student doing B.Tech", "education_level", "college"),
    ("I'm a carpenter", "occupation", "artisan"),
    ("vyavasaya kooli ni", "occupation", "agri_labourer"),
    ("my daughter is getting married next month", "has_daughter_marrying", True),
    ("I have a daughter aged 4", "has_daughter_under_10", True),
])
def test_fact_patterns(text, field, value):
    assert facts(text).get(field) == value


def test_never_extracts_ids():
    f = facts("my aadhaar is 1234 5678 9012 and phone 9876543210")
    assert "annual_income" not in f and "age" not in f


@pytest.mark.parametrize("text,mentions,n,intent", [
    ("hello", [], 0, "chitchat"),
    ("what documents for rythu bima", ["ts_rythu_bima"], 0, "documents"),
    ("how to apply for aarogyasri", ["ts_aarogyasri"], 0, "how_to_apply"),
    ("PM-KISAN ఎంత వస్తుంది", ["pm_kisan"], 0, "benefit"),
    ("which schemes are there for me", [], 0, "find_schemes"),
    ("I am a farmer", [], 1, "find_schemes"),
    ("what is the capital of France", [], 0, "general"),
    ("Is there any scheme for artisans like carpenters?", [], 0, "general"),
    ("which schemes can I get", [], 0, "find_schemes"),
])
def test_intent(text, mentions, n, intent):
    assert classify(text, mentions, n) == intent


def test_glossary_translation():
    assert "farmer" in glossary_translate("నేను రైతులకు పథకాలు")
    assert "pension" in glossary_translate("पेंशन योजना")


@pytest.mark.parametrize("text", ["Is there any pension scheme for unorganised workers?", "बेटी की पढ़ाई और शादी के लिए बचत योजना",
                                  "What help is there for building a house in a village?"])
def test_topic_questions_are_not_profile_facts(text):
    assert facts(text) == {}
