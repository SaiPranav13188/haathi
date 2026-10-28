"""Smart questioning vs fixed questionnaire (haathi.md §6 / §10.3 exp. 5) on 30 synthetic profiles.

A synthetic person is drawn from the field priors (seeded). Each strategy asks one field at a time (answered
truthfully from the profile) until no scheme is "maybe". We count questions-to-decision.
"""
from __future__ import annotations

import random
import statistics

from harness import REPORTS

from app.corpus import get_corpus
from app.eligibility.evaluator import status_only
from app.eligibility.fields import FIELDS
from app.eligibility.questioner import next_fixed, next_questions


def person(rng: random.Random) -> dict:
    p = {}
    for f, spec in FIELDS.items():
        x, acc = rng.random(), 0.0
        for o in spec.options:
            acc += o.prior
            if x <= acc:
                p[f] = o.value
                break
        else:
            p[f] = spec.options[-1].value
    if p["occupation"] != "farmer":
        p["land_acres"] = 0 if rng.random() < 0.8 else p["land_acres"]
    return p


def run(truth: dict, pick, schemes) -> int:
    prof, n = {}, 0
    while n < 30:
        f = pick(prof)
        if f is None:
            break
        prof[f] = truth[f]
        n += 1
    assert all(status_only(s, prof) != "maybe" for s in schemes), "strategy stopped early"
    return n


def main(n_profiles: int = 30) -> None:
    schemes = list(get_corpus().schemes.values())
    rng = random.Random(2025)
    people = [person(rng) for _ in range(n_profiles)]
    strategies = {
        "Fixed questionnaire (all fields, fixed order)": lambda p: next_fixed(p, schemes, skip_irrelevant=False),
        "Fixed order, skip irrelevant fields": lambda p: next_fixed(p, schemes, skip_irrelevant=True),
        "Information gain (Haathi)": lambda p: (next_questions(p, schemes) or [None])[0],
    }
    rows = []
    for name, pick in strategies.items():
        counts = [run(t, pick, schemes) for t in people]
        rows.append((name, statistics.mean(counts), statistics.median(counts), max(counts)))
        print(name, rows[-1])
    base = rows[0][1]
    text = ["# Questions to decision", "", f"{n_profiles} synthetic profiles (seed 2025) drawn from the field priors; "
            f"{len(schemes)} schemes. A decision = no scheme left in 'maybe'.", "",
            "| strategy | mean | median | max | fewer than fixed |", "|---|---|---|---|---|"]
    text += [f"| {n} | {m:.2f} | {md:.0f} | {mx} | {100 * (base - m) / base:+.0f}% |" for n, m, md, mx in rows]
    text += ["", "Formula: IG(f) = H − Σ_v P(f=v)·Σ_s h(P(s eligible | f=v)), estimated by Monte-Carlo completion "
             "of unknown fields from priors (see backend/app/eligibility/questioner.py)."]
    (REPORTS / "questioning.md").write_text("\n".join(text) + "\n")
    print("\n".join(text))


if __name__ == "__main__":
    main()
