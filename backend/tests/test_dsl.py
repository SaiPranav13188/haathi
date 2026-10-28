import pytest
from hypothesis import given, strategies as st

from app.eligibility.dsl import And, LogicError, Not, Or, Ref, Rule, Scheme, parse_logic


def test_precedence_and_binds_tighter_than_or():
    assert parse_logic("r1 OR r2 AND r3") == Or((Ref("r1"), And((Ref("r2"), Ref("r3")))))


def test_parentheses_and_not():
    assert parse_logic("NOT (r1 OR r2) AND r3") == And((Not(Or((Ref("r1"), Ref("r2")))), Ref("r3")))


def test_case_insensitive_keywords():
    assert parse_logic("r1 and not r2") == And((Ref("r1"), Not(Ref("r2"))))


@pytest.mark.parametrize("bad", ["", "r1 AND", "(r1", "r1 r2", "AND r1", "r1 OR )", "r1 $ r2", "NOT", "()"])
def test_invalid_expressions(bad):
    with pytest.raises(LogicError):
        parse_logic(bad)


def _src():
    return {"doc": "d.md", "page": 1, "quote": "q"}


@pytest.mark.parametrize("op,value", [("in", "x"), ("between", [5, 1]), ("between", [1]), ("lte", "ten"), ("not_in", 3)])
def test_rule_value_validation(op, value):
    with pytest.raises(ValueError):
        Rule(id="r1", field="age", op=op, value=value, source=_src())


def test_scheme_rejects_unknown_rule_reference(tmp_path):
    import json
    from pathlib import Path

    raw = json.loads(next(Path(__file__).resolve().parents[2].joinpath("data/schemes").glob("*.json")).read_text())
    raw["logic"] = raw["logic"] + " AND r99"
    with pytest.raises(ValueError):
        Scheme.model_validate(raw)


def test_scheme_rejects_duplicate_rule_ids():
    import json
    from pathlib import Path

    raw = json.loads(Path(__file__).resolve().parents[2].joinpath("data/schemes/pm_kisan.json").read_text())
    raw["rules"].append(raw["rules"][0])
    with pytest.raises(ValueError):
        Scheme.model_validate(raw)


# ---- property-based: random ASTs round-trip through a printer and the parser
ids = st.sampled_from(["r1", "r2", "r3", "r4"])
trees = st.recursive(
    ids.map(Ref),
    lambda kids: st.one_of(
        kids.map(Not),
        st.lists(kids, min_size=2, max_size=3).map(lambda xs: And(tuple(xs))),
        st.lists(kids, min_size=2, max_size=3).map(lambda xs: Or(tuple(xs))),
    ),
    max_leaves=8,
)


def show(n) -> str:
    if isinstance(n, Ref):
        return n.id
    if isinstance(n, Not):
        return f"NOT ({show(n.child)})"
    op = " AND " if isinstance(n, And) else " OR "
    return "(" + op.join(show(c) for c in n.children) + ")"


def flatten(n):
    """Parser flattens nested same-type groups only when not parenthesised; compare semantics instead."""
    return n


@given(trees, st.dictionaries(st.sampled_from(["r1", "r2", "r3", "r4"]), st.sampled_from(["pass", "fail", "unknown"]), min_size=4))
def test_printed_tree_parses_to_same_semantics(tree, results):
    from app.eligibility.evaluator import eval_logic

    assert eval_logic(parse_logic(show(tree)), results) == eval_logic(tree, results)


@given(trees)
def test_refs_preserved(tree):
    assert parse_logic(show(tree)).refs() == tree.refs()
