# Questions to decision

30 synthetic profiles (seed 2025) drawn from the field priors; 30 schemes. A decision = no scheme left in 'maybe'.

| strategy | mean | median | max | fewer than fixed |
|---|---|---|---|---|
| Fixed questionnaire (all fields, fixed order) | 16.57 | 16 | 20 | +0% |
| Fixed order, skip irrelevant fields | 12.87 | 13 | 16 | +22% |
| Information gain (Haathi) | 11.77 | 12 | 15 | +29% |

Formula: IG(f) = H − Σ_v P(f=v)·Σ_s h(P(s eligible | f=v)), estimated by Monte-Carlo completion of unknown fields from priors (see backend/app/eligibility/questioner.py).
