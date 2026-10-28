"""Rule DSL (haathi.md §6) as Pydantic models, plus a small parser for the logic expression.

Logic grammar:  expr   := or
                or     := and ("OR" and)*
                and    := not ("AND" not)*
                not    := "NOT" not | atom
                atom   := RULE_ID | "(" expr ")"
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal, Union

from pydantic import BaseModel, Field, field_validator, model_validator

Op = Literal["eq", "neq", "in", "not_in", "lt", "lte", "gt", "gte", "between", "exists"]
NUMERIC_OPS = {"lt", "lte", "gt", "gte", "between"}


class Source(BaseModel):
    doc: str
    page: int
    quote: str | None = None
    bbox: list[float] | None = None


class I18n(BaseModel):
    en: str
    hi: str | None = None
    te: str | None = None

    def get(self, lang: str) -> str:
        return getattr(self, lang, None) or self.en


class Rule(BaseModel):
    id: str
    field: str
    op: Op
    value: Any = None
    source: Source

    @model_validator(mode="after")
    def _check_value(self) -> "Rule":
        if self.op in {"in", "not_in"} and not isinstance(self.value, list):
            raise ValueError(f"rule {self.id}: '{self.op}' needs a list value")
        if self.op == "between":
            if not (isinstance(self.value, list) and len(self.value) == 2):
                raise ValueError(f"rule {self.id}: 'between' needs [low, high]")
            if self.value[0] > self.value[1]:
                raise ValueError(f"rule {self.id}: 'between' low > high")
        if self.op in {"lt", "lte", "gt", "gte"} and not isinstance(self.value, (int, float)):
            raise ValueError(f"rule {self.id}: '{self.op}' needs a number")
        return self


class Benefit(BaseModel):
    summary: I18n
    amount: float | None = None
    unit: I18n | None = None
    per_acre: bool = False
    source: Source


class HowToApply(BaseModel):
    summary: I18n
    source: Source


class Scheme(BaseModel):
    scheme_id: str
    version: str
    doc: str
    name: I18n
    tagline: I18n
    level: Literal["central", "state"]
    state: str | None = None
    categories: list[str] = Field(default_factory=list)
    official_url: str
    last_verified: str
    review_status: Literal["seed", "pending", "approved", "edited", "rejected"] = "seed"
    changed_on: str | None = None
    change_note: I18n | None = None
    rules: list[Rule]
    logic: str
    benefit: Benefit
    documents_required: list[str] = Field(default_factory=list)
    how_to_apply: HowToApply
    official_sources: list[dict] = Field(default_factory=list)  # official PDFs / G.O.s backing the rules

    @field_validator("rules")
    @classmethod
    def _unique_ids(cls, rules: list[Rule]) -> list[Rule]:
        ids = [r.id for r in rules]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate rule ids")
        return rules

    @model_validator(mode="after")
    def _logic_refs(self) -> "Scheme":
        tree = parse_logic(self.logic)
        known = {r.id for r in self.rules}
        missing = tree.refs() - known
        if missing:
            raise ValueError(f"logic references unknown rules: {sorted(missing)}")
        return self

    @property
    def logic_tree(self) -> "Node":
        return parse_logic(self.logic)

    def rule(self, rid: str) -> Rule:
        return next(r for r in self.rules if r.id == rid)


# ---------------------------------------------------------------- logic AST

@dataclass(frozen=True)
class Ref:
    id: str

    def refs(self) -> set[str]:
        return {self.id}


@dataclass(frozen=True)
class Not:
    child: "Node"

    def refs(self) -> set[str]:
        return self.child.refs()


@dataclass(frozen=True)
class And:
    children: tuple["Node", ...]

    def refs(self) -> set[str]:
        return set().union(*(c.refs() for c in self.children))


@dataclass(frozen=True)
class Or:
    children: tuple["Node", ...]

    def refs(self) -> set[str]:
        return set().union(*(c.refs() for c in self.children))


Node = Union[Ref, Not, And, Or]

_TOKEN = re.compile(r"\s*(\(|\)|[A-Za-z_][A-Za-z0-9_]*)")
_KEYWORDS = {"AND", "OR", "NOT"}


class LogicError(ValueError):
    pass


def _tokenize(expr: str) -> list[str]:
    tokens, pos = [], 0
    expr = expr.rstrip()
    while pos < len(expr):
        m = _TOKEN.match(expr, pos)
        if not m:
            raise LogicError(f"unexpected character at {pos}: {expr[pos:pos + 10]!r}")
        tokens.append(m.group(1))
        pos = m.end()
    return tokens


def parse_logic(expr: str) -> Node:
    tokens = _tokenize(expr)
    if not tokens:
        raise LogicError("empty logic expression")
    pos = 0

    def peek() -> str | None:
        return tokens[pos] if pos < len(tokens) else None

    def take(expected: str | None = None) -> str:
        nonlocal pos
        tok = peek()
        if tok is None or (expected is not None and tok.upper() != expected):
            raise LogicError(f"expected {expected or 'token'}, got {tok!r}")
        pos += 1
        return tok

    def parse_or() -> Node:
        parts = [parse_and()]
        while (t := peek()) is not None and t.upper() == "OR":
            take("OR")
            parts.append(parse_and())
        return parts[0] if len(parts) == 1 else Or(tuple(parts))

    def parse_and() -> Node:
        parts = [parse_not()]
        while (t := peek()) is not None and t.upper() == "AND":
            take("AND")
            parts.append(parse_not())
        return parts[0] if len(parts) == 1 else And(tuple(parts))

    def parse_not() -> Node:
        t = peek()
        if t is not None and t.upper() == "NOT":
            take("NOT")
            return Not(parse_not())
        return parse_atom()

    def parse_atom() -> Node:
        t = peek()
        if t == "(":
            take("(")
            node = parse_or()
            take(")")
            return node
        if t is None or t == ")" or t.upper() in _KEYWORDS:
            raise LogicError(f"expected rule id, got {t!r}")
        take()
        return Ref(t)

    tree = parse_or()
    if pos != len(tokens):
        raise LogicError(f"trailing tokens: {tokens[pos:]}")
    return tree
