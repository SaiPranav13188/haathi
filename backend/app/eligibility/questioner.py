"""Smart questioning by expected information gain (haathi.md §6).

Formula (documented for the report):
    Let S be the schemes still "maybe". For each scheme s, P(s) = P(eligible | known facts), estimated by
    Monte-Carlo completion of the unknown fields from per-field priors (fields.py, independent).
    Uncertainty  H = Σ_s h(P(s)),   h(p) = −p log2 p − (1−p) log2(1−p)
    For a candidate field f with answer buckets v:
        IG(f) = H − Σ_v P(f = v) · Σ_s h(P(s | f = v))
    Ask argmax_f IG(f). Stop when S is empty, the best IG is ~0, or the question budget is used.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .dsl import Scheme
from .evaluator import evaluate, status_only
from .fields import FIELDS, FIXED_ORDER

N_SAMPLES = 400


def _h(p: float) -> float:
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -(p * math.log2(p) + (1 - p) * math.log2(1 - p))


def _draw(field: str, rng: random.Random) -> tuple[int, Any]:
    opts = FIELDS[field].options
    x = rng.random()
    acc = 0.0
    for i, o in enumerate(opts):
        acc += o.prior
        if x <= acc:
            return i, o.value
    return len(opts) - 1, opts[-1].value


@dataclass
class Candidate:
    field: str
    gain: float


def rank_questions(profile: Mapping[str, Any], schemes: Sequence[Scheme], seed: int = 7,
                   exclude: set[str] | None = None) -> list[Candidate]:
    exclude = exclude or set()
    maybe = [s for s in schemes if status_only(s, profile) == "maybe"]
    if not maybe:
        return []
    fields = sorted({f for s in maybe for f in evaluate(s, profile).missing_fields} - set(profile) - exclude,
                    key=FIXED_ORDER.index)
    if not fields:
        return []
    needed = sorted({r.field for s in maybe for r in s.rules} - set(profile))
    rng = random.Random(seed)
    # samples: list of (bucket index per field, completed profile)
    samples = []
    for _ in range(N_SAMPLES):
        idx, completion = {}, dict(profile)
        for f in needed:
            i, v = _draw(f, rng)
            idx[f] = i
            completion[f] = v
        elig = [status_only(s, completion) == "eligible" for s in maybe]
        samples.append((idx, elig))

    def uncertainty(rows: list) -> float:
        if not rows:
            return 0.0
        n = len(rows)
        return sum(_h(sum(r[1][k] for r in rows) / n) for k in range(len(maybe)))

    base = uncertainty(samples)
    out = []
    for f in fields:
        groups: dict[int, list] = {}
        for row in samples:
            groups.setdefault(row[0][f], []).append(row)
        cond = sum(len(g) / len(samples) * uncertainty(g) for g in groups.values())
        out.append(Candidate(f, base - cond))
    out.sort(key=lambda c: (-round(c.gain, 9), FIXED_ORDER.index(c.field)))
    return out


def next_questions(profile: Mapping[str, Any], schemes: Sequence[Scheme], k: int = 1,
                   exclude: set[str] | None = None) -> list[str]:
    ranked = [c for c in rank_questions(profile, schemes, exclude=exclude) if c.gain > 1e-6]
    return [c.field for c in ranked[:k]]


def next_fixed(profile: Mapping[str, Any], schemes: Sequence[Scheme], skip_irrelevant: bool) -> str | None:
    """Baseline: ask fields in a fixed order (optionally skipping fields no open scheme depends on)."""
    maybe = [s for s in schemes if status_only(s, profile) == "maybe"]
    if not maybe:
        return None
    relevant = {f for s in maybe for f in evaluate(s, profile).missing_fields}
    for f in FIXED_ORDER:
        if f in profile:
            continue
        if skip_irrelevant and f not in relevant:
            continue
        return f
    return None
