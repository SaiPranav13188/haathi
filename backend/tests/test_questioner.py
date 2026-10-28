from app.corpus import get_corpus
from app.eligibility.evaluator import status_only
from app.eligibility.questioner import next_fixed, next_questions, rank_questions


def schemes():
    return list(get_corpus().schemes.values())


def test_no_questions_when_nothing_is_open():
    s = [get_corpus().schemes["ts_rythu_bharosa"]]
    assert next_questions({"occupation": "farmer", "land_acres": 2, "state": "Telangana"}, s) == []


def test_asks_only_decisive_fields():
    s = [get_corpus().schemes["ts_aasara_pension"]]
    q = next_questions({"age": 65, "state": "Telangana", "is_govt_employee": False, "annual_income": 180000}, s)
    assert q == ["area"]


def test_gain_non_negative_and_sorted():
    ranked = rank_questions({}, schemes())
    assert ranked and all(c.gain >= -1e-9 for c in ranked)
    gains = [round(c.gain, 9) for c in ranked]
    assert gains == sorted(gains, reverse=True)


def test_smart_beats_fixed_on_a_farmer():
    truth = {"state": "Telangana", "area": "rural", "age": 45, "gender": "male", "annual_income": 120000,
             "occupation": "farmer", "land_acres": 2, "category": "bc", "has_bank_account": True, "has_ration_card": True,
             "is_income_tax_payer": False, "is_govt_employee": False, "owns_pucca_house": True, "has_lpg_connection": True,
             "has_daughter_under_10": False, "has_school_child": True, "has_daughter_marrying": False,
             "has_epf_esic_nps": False, "has_mgnregs_job_card": False, "education_level": "not_studying"}

    def run(pick):
        prof, n = {}, 0
        while (f := pick(prof)) is not None and n < 25:
            prof[f] = truth[f]
            n += 1
        assert all(status_only(s, prof) != "maybe" for s in schemes())
        return n

    smart = run(lambda p: (next_questions(p, schemes()) or [None])[0])
    fixed = run(lambda p: next_fixed(p, schemes(), skip_irrelevant=False))
    assert smart <= fixed
