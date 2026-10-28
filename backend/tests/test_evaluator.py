import json
from pathlib import Path

import pytest
from hypothesis import given, strategies as st

from app.eligibility.dsl import Rule, Scheme, parse_logic
from app.eligibility.evaluator import eval_logic, eval_rule, evaluate, evaluate_all, status_only, what_if
from app.eligibility.explain import inr, rule_label, what_if_text

DATA = Path(__file__).resolve().parents[2] / "data" / "schemes"


def load(sid: str) -> Scheme:
    return Scheme.model_validate(json.loads((DATA / f"{sid}.json").read_text()))


def R(op, value, field="x"):
    return Rule(id="r", field=field, op=op, value=value, source={"doc": "d", "page": 1})


@pytest.mark.parametrize("op,value,x,expected", [
    ("eq", 5, 5, "pass"), ("eq", 5, 6, "fail"), ("neq", 5, 6, "pass"), ("neq", 5, 5, "fail"),
    ("in", ["a", "b"], "a", "pass"), ("in", ["a"], "c", "fail"), ("not_in", ["a"], "c", "pass"), ("not_in", ["a"], "a", "fail"),
    ("lt", 10, 9, "pass"), ("lt", 10, 10, "fail"), ("lte", 10, 10, "pass"), ("lte", 10, 11, "fail"),
    ("gt", 0, 0.5, "pass"), ("gt", 0, 0, "fail"), ("gte", 18, 18, "pass"), ("gte", 18, 17, "fail"),
    ("between", [18, 40], 18, "pass"), ("between", [18, 40], 40, "pass"), ("between", [18, 40], 41, "fail"),
    ("exists", None, "yes", "pass"), ("exists", None, False, "fail"), ("lte", 10, "abc", "fail"),
])
def test_ops(op, value, x, expected):
    assert eval_rule(R(op, value), {"x": x}) == expected


def test_missing_is_unknown():
    assert eval_rule(R("eq", 1), {}) == "unknown"
    assert eval_rule(R("eq", 1), {"x": None}) == "unknown"


tri = st.sampled_from(["pass", "fail", "unknown"])


@given(tri, tri)
def test_kleene_tables(a, b):
    res = {"a": a, "b": b}
    AND = eval_logic(parse_logic("a AND b"), res)
    OR = eval_logic(parse_logic("a OR b"), res)
    assert AND == ("fail" if "fail" in (a, b) else "unknown" if "unknown" in (a, b) else "pass")
    assert OR == ("pass" if "pass" in (a, b) else "unknown" if "unknown" in (a, b) else "fail")
    # De Morgan holds in Kleene logic
    assert eval_logic(parse_logic("NOT (a AND b)"), res) == eval_logic(parse_logic("NOT a OR NOT b"), res)


@given(tri, tri, tri)
def test_monotonic_resolving_unknown_never_flips_decided(a, b, c):
    """If the outcome is decided with unknowns, any completion gives the same outcome."""
    expr = parse_logic("a AND (b OR c)")
    base = eval_logic(expr, {"a": a, "b": b, "c": c})
    if base == "unknown":
        return
    for x in ("pass", "fail"):
        filled = {k: (x if v == "unknown" else v) for k, v in {"a": a, "b": b, "c": c}.items()}
        assert eval_logic(expr, filled) == base


def test_example_from_spec_telangana_farmer():
    s = load("ts_rythu_bharosa")
    out = evaluate(s, {"occupation": "farmer", "land_acres": 2, "state": "Telangana"})
    assert out.status == "eligible"
    assert all(r.result == "pass" for r in out.rules)


def test_or_logic_rural_urban_income():
    s = load("ts_aasara_pension")
    base = {"age": 65, "state": "Telangana", "is_govt_employee": False}
    assert status_only(s, {**base, "area": "rural", "annual_income": 140000}) == "eligible"
    assert status_only(s, {**base, "area": "rural", "annual_income": 180000}) == "not_eligible"
    assert status_only(s, {**base, "area": "urban", "annual_income": 180000}) == "eligible"
    assert status_only(s, {**base, "annual_income": 180000}) == "maybe"  # area decides


def test_missing_fields_only_decisive_ones():
    s = load("ts_aasara_pension")
    out = evaluate(s, {"age": 65, "state": "Telangana", "is_govt_employee": False, "annual_income": 180000})
    assert out.status == "maybe"
    assert out.missing_fields == ["area"]  # 1.8 lakh: fine in a town, too high in a village


def test_case_split_resolves_same_field_branches():
    s = load("ts_aasara_pension")
    # ₹1 lakh passes both the rural and the urban limit, so area cannot change the answer
    assert evaluate(s, {"age": 65, "state": "Telangana", "is_govt_employee": False, "annual_income": 100000}).status == "eligible"


def test_short_circuit_fail_with_unknowns():
    s = load("pm_kisan")
    out = evaluate(s, {"occupation": "student"})
    assert out.status == "not_eligible"
    assert out.missing_fields == []


def test_what_if_income_threshold():
    s = load("ts_kalyana_lakshmi")
    p = {"category": "bc", "has_daughter_marrying": True, "state": "Telangana", "area": "rural", "annual_income": 180000}
    out = evaluate(s, p)
    assert out.status == "not_eligible"
    assert out.what_if["field"] == "annual_income" and out.what_if["threshold"] == 150000
    assert "₹1,50,000" in what_if_text(out.what_if, "Kalyana Lakshmi", "en")
    assert "₹1,50,000" in what_if_text(out.what_if, "కళ్యాణ లక్ష్మి", "te")


def test_what_if_age_reach_and_no_impossible_suggestions():
    aasara = load("ts_aasara_pension")
    w = what_if(aasara, {"age": 55, "state": "Telangana", "is_govt_employee": False, "area": "rural", "annual_income": 1})
    assert w["direction"] == "reach" and "57" in what_if_text(w, "Aasara", "en")
    apy = load("apy")  # too old for APY: we must not suggest becoming younger
    assert what_if(apy, {"age": 45, "has_bank_account": True, "is_income_tax_payer": False}) is None


def test_what_if_requires_single_rule_flip():
    s = load("pm_sym")
    # fails on both occupation (non-numeric) and income → no what-if
    assert what_if(s, {"occupation": "salaried", "age": 30, "annual_income": 500000, "has_epf_esic_nps": False,
                       "is_income_tax_payer": False}) is None


def test_evaluate_all_orders_eligible_first():
    schemes = [Scheme.model_validate(json.loads(p.read_text())) for p in DATA.glob("*.json")]
    outs = evaluate_all(schemes, {"occupation": "farmer", "land_acres": 2, "state": "Telangana"})
    order = [o.status for o in outs]
    assert order == sorted(order, key={"eligible": 0, "maybe": 1, "not_eligible": 2}.get)


def test_inr_formatting():
    assert inr(150000) == "₹1,50,000"
    assert inr(1000000) == "₹10,00,000"
    assert inr(999) == "₹999"
    assert inr(100116) == "₹1,00,116"


def test_rule_labels_all_languages():
    for p in DATA.glob("*.json"):
        s = Scheme.model_validate(json.loads(p.read_text()))
        for r in s.rules:
            for lang in ("en", "hi", "te"):
                assert rule_label(r, lang)


# ---- edge cases for full evaluator / parser coverage
from app.eligibility.evaluator import _direction


def test_scheme_rule_lookup_and_passed_count():
    s = load("pm_kisan")
    assert s.rule("r2").field == "land_acres"
    out = evaluate(s, {"occupation": "farmer", "land_acres": 2})
    assert out.passed == 2


@pytest.mark.parametrize("op,value,field,current,expected", [
    ("lte", 10, "annual_income", "n/a", None),          # unparsable current value
    ("lte", 10, "age", 20, None),                        # cannot become younger
    ("lte", 10, "annual_income", 20, "lower"),
    ("gte", 60, "age", 50, "reach"),
    ("gt", 0, "land_acres", 0, "higher"),
    ("between", [18, 40], "age", 10, "reach"),
    ("between", [18, 40], "annual_income", 10, "higher"),
    ("between", [18, 40], "age", 50, None),
    ("between", [18, 40], "annual_income", 50, "lower"),
    ("between", [18, 40], "annual_income", 30, None),    # inside the range: nothing to change
    ("eq", 5, "annual_income", 3, None),                 # non-numeric op
])
def test_what_if_direction(op, value, field, current, expected):
    assert _direction(R(op, value, field), current) == expected


def test_what_if_prefers_full_eligibility_then_smallest_gap():
    s = load("ts_epass_post_matric")
    p = {"state": "Telangana", "education_level": "college", "category": "sc", "annual_income": 260000}
    w = what_if(s, p)
    assert w["threshold"] == 200000 and w["would_be"] == "eligible"


def test_case_split_skips_numeric_unknowns():
    s = load("ts_aasara_pension")
    # income unknown (numeric) → can't enumerate → stays maybe
    assert status_only(s, {"age": 65, "state": "Telangana", "is_govt_employee": False}) == "maybe"
