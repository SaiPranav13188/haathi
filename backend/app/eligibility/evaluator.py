"""Deterministic eligibility evaluator. The LLM never decides eligibility; this module does.

Each rule returns pass / fail / unknown; the logic expression is evaluated with Kleene three-valued logic,
so a scheme is eligible / not_eligible / maybe.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Literal, Mapping

from .dsl import NUMERIC_OPS, And, Node, Not, Or, Ref, Rule, Scheme

Tri = Literal["pass", "fail", "unknown"]
Status = Literal["eligible", "not_eligible", "maybe"]


def eval_rule(rule: Rule, profile: Mapping[str, Any]) -> Tri:
    if rule.field not in profile or profile[rule.field] is None:
        return "unknown"
    v = profile[rule.field]
    target = rule.value
    op = rule.op
    try:
        if op == "exists":
            ok = v not in (False, 0, "", [], None)
        elif op == "eq":
            ok = v == target
        elif op == "neq":
            ok = v != target
        elif op == "in":
            ok = v in target
        elif op == "not_in":
            ok = v not in target
        elif op == "lt":
            ok = float(v) < target
        elif op == "lte":
            ok = float(v) <= target
        elif op == "gt":
            ok = float(v) > target
        elif op == "gte":
            ok = float(v) >= target
        elif op == "between":
            ok = target[0] <= float(v) <= target[1]
        else:  # pragma: no cover - guarded by the Op literal
            raise ValueError(op)
    except (TypeError, ValueError):
        return "fail"
    return "pass" if ok else "fail"


def eval_logic(node: Node, results: Mapping[str, Tri]) -> Tri:
    if isinstance(node, Ref):
        return results[node.id]
    if isinstance(node, Not):
        r = eval_logic(node.child, results)
        return {"pass": "fail", "fail": "pass", "unknown": "unknown"}[r]  # type: ignore[return-value]
    if isinstance(node, And):
        vals = [eval_logic(c, results) for c in node.children]
        if "fail" in vals:
            return "fail"
        return "unknown" if "unknown" in vals else "pass"
    if isinstance(node, Or):
        vals = [eval_logic(c, results) for c in node.children]
        if "pass" in vals:
            return "pass"
        return "unknown" if "unknown" in vals else "fail"
    raise TypeError(node)  # pragma: no cover


def _status(t: Tri) -> Status:
    return {"pass": "eligible", "fail": "not_eligible", "unknown": "maybe"}[t]  # type: ignore[return-value]


@dataclass
class RuleOutcome:
    rule: Rule
    result: Tri
    user_value: Any = None


@dataclass
class SchemeOutcome:
    scheme: Scheme
    status: Status
    rules: list[RuleOutcome]
    missing_fields: list[str] = field(default_factory=list)
    what_if: dict | None = None

    @property
    def passed(self) -> int:
        return sum(r.result == "pass" for r in self.rules)


def _decisive_unknowns(scheme: Scheme, results: dict[str, Tri]) -> list[str]:
    """Fields whose unknown rules could still change the scheme outcome."""
    from itertools import product

    tree = scheme.logic_tree
    unknown = [r for r in scheme.rules if results[r.id] == "unknown"]
    out: list[str] = []
    for r in unknown:
        others = [o.id for o in unknown if o.id != r.id]
        # r matters if, for some completion of the other unknown rules, flipping r flips the outcome
        for combo in product(("pass", "fail"), repeat=len(others)):
            base = {**results, **dict(zip(others, combo))}
            if eval_logic(tree, {**base, r.id: "pass"}) != eval_logic(tree, {**base, r.id: "fail"}):
                if r.field not in out:
                    out.append(r.field)
                break
    return out


def _case_split(scheme: Scheme, profile: Mapping[str, Any], results: dict[str, Tri]) -> Tri:
    """Kleene logic treats unknown rules independently, but two rules on the same field are not independent
    (area = rural OR area = urban is always true). When the unknown fields are all finite (yes/no or choice),
    enumerate their values: if every case gives the same answer, the scheme is decided."""
    from itertools import product

    from .fields import FIELDS

    t = eval_logic(scheme.logic_tree, results)
    if t != "unknown":
        return t
    unknown = sorted({r.field for r in scheme.rules if results[r.id] == "unknown"})
    if not unknown or len(unknown) > 3 or any(f not in FIELDS or FIELDS[f].kind == "number" for f in unknown):
        return t
    seen = set()
    for combo in product(*[[o.value for o in FIELDS[f].options] for f in unknown]):
        filled = {**profile, **dict(zip(unknown, combo))}
        seen.add(eval_logic(scheme.logic_tree, {r.id: eval_rule(r, filled) for r in scheme.rules}))
        if len(seen) > 1:
            return "unknown"
    return seen.pop()


def evaluate(scheme: Scheme, profile: Mapping[str, Any]) -> SchemeOutcome:
    results = {r.id: eval_rule(r, profile) for r in scheme.rules}
    status = _status(_case_split(scheme, profile, results))
    outcome = SchemeOutcome(
        scheme=scheme,
        status=status,
        rules=[RuleOutcome(r, results[r.id], profile.get(r.field)) for r in scheme.rules],
        missing_fields=_decisive_unknowns(scheme, results) if status == "maybe" else [],
    )
    if status == "not_eligible":
        outcome.what_if = what_if(scheme, profile, results)
    return outcome


def status_only(scheme: Scheme, profile: Mapping[str, Any]) -> Status:
    results = {r.id: eval_rule(r, profile) for r in scheme.rules}
    return _status(_case_split(scheme, profile, results))


def what_if(scheme: Scheme, profile: Mapping[str, Any], results: dict[str, Tri] | None = None) -> dict | None:
    """For a not-eligible scheme: is there exactly one failing numeric rule whose passing would make it
    eligible (or still-open)? If so, return the threshold the user would need."""
    results = results or {r.id: eval_rule(r, profile) for r in scheme.rules}
    tree = scheme.logic_tree
    candidates = []
    for r in scheme.rules:
        if results[r.id] != "fail" or r.op not in NUMERIC_OPS:
            continue
        flipped = eval_logic(tree, {**results, r.id: "pass"})
        if flipped == "fail":
            continue
        current = profile.get(r.field)
        # Only suggest changes a person could plausibly reach (income lower, age reaching a minimum, more land).
        direction = _direction(r, current)
        if direction is None:
            continue
        candidates.append({
            "rule_id": r.id, "field": r.field, "op": r.op, "threshold": r.value, "current": current,
            "direction": direction, "would_be": "eligible" if flipped == "pass" else "maybe",
            "source": r.source.model_dump(),
        })
    if not candidates:
        return None
    # prefer flips that make the scheme fully eligible, then the smallest relative gap
    def gap(c: dict) -> float:
        t = c["threshold"][0] if isinstance(c["threshold"], list) else c["threshold"]
        cur = float(c["current"] or 0)
        return abs(cur - t) / max(abs(t), 1)

    candidates.sort(key=lambda c: (c["would_be"] != "eligible", gap(c)))
    return candidates[0]


def _direction(rule: Rule, current: Any) -> str | None:
    try:
        cur = float(current)
    except (TypeError, ValueError):
        return None
    if rule.op in {"lt", "lte"}:
        # needing to be *lower*; impossible for age
        return None if rule.field == "age" else "lower"
    if rule.op in {"gt", "gte"}:
        return "reach" if rule.field == "age" else "higher"
    if rule.op == "between":
        lo, hi = rule.value
        if cur < lo:
            return "reach" if rule.field == "age" else "higher"
        if cur > hi:
            return None if rule.field == "age" else "lower"
    return None


def evaluate_all(schemes: Iterable[Scheme], profile: Mapping[str, Any]) -> list[SchemeOutcome]:
    order = {"eligible": 0, "maybe": 1, "not_eligible": 2}
    outs = [evaluate(s, profile) for s in schemes]
    outs.sort(key=lambda o: (order[o.status], -(o.scheme.benefit.amount or 0)))
    return outs
