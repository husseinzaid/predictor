# Formula Review — Session Notes (Handover)

Notes from a review session on the scoring/simulation formula
(`backend/app/simulate.py`), before starting the planned UI/GUI work (see
`HANDOVER.md`). Written for whoever picks this up next.

## How it started

User was sanity-checking the **Population** factor: with the `population`
slider maxed out, Egypt ranked above Iran in Group G's table, which seemed
right (Egypt ~116.5M people vs Iran ~91.6M). But in some configurations
Iran finished *below* New Zealand (~5.3M) and Belgium (~11.9M) in the
simulated group standings, which felt wrong given Iran's much larger
population.

## What we found

1. **The Power Score / power-rankings math was correct all along.**
   Population is min-max normalized across all 48 teams
   (`build_team_table.py`'s `normalize()`), and Egypt > Iran > Belgium > New
   Zealand in that normalized factor, both within Group G and globally.
   `compute_power_scores` / `normalize_weights` in `simulate.py` are sound.

2. **The "Group Stage" table was not the power ranking — it was one frozen
   random trial.** `run_simulation` ran 2,000 Monte Carlo trials (Poisson
   goal sampling) to compute `champion_probabilities`, but used **trial #1
   only** (fixed `seed=42`) as the "representative" group stage/bracket
   shown in the UI. Because the seed never changed, the *same* random
   outcome was shown every time — so it looked deterministic/broken rather
   than "one possible dice roll."

3. **Concretely**: with population maxed + defaults, that one frozen trial
   had Iran lose 2-5 to New Zealand — a ~1-in-450 fluke under Poisson, given
   Iran's expected goals (1.97) vs New Zealand's (0.92). Frozen forever by
   the fixed seed, it always showed this fluke.

(We also walked through Monte Carlo / Poisson in plain-English terms in
this session if useful for explaining to the user again — analogy used:
"weighted dice" for Poisson, "free throw average" for expected goals,
"replay the tournament 2,000 times and count" for Monte Carlo.)

## What we tried / changed

### Change 1 — Poisson → Binomial(6, p) goal sampling

- **Why**: Poisson's tail is unbounded and proportionally heavy for small
  means, which is what let New Zealand "score 5" against a much stronger
  Iran.
- **What**: replaced `_poisson_sample` with `_binomial_sample` — each team
  gets `SCORING_CHANCES = 6` scoring chances, each converted independently
  with probability `expected_goals / 6`. Same mean as before, much lower
  variance, hard 0-6 ceiling.
- **Result**: Iran 2-5 NZL became Iran 2-2 NZL (same seed). The
  "freak underdog blowout" probability dropped from ~1/450 to ~1/22,700.
  Verified `pytest` still green and default-weight champion probabilities
  still sensible (France/Spain/Brazil/Argentina at the top).

### Change 2 — Deterministic Group Stage / Bracket

- User feedback after Change 1: liked the reduced variance, but ultimately
  wanted the **displayed** group stage/bracket to have **no randomness at
  all** — "stick to the calculation" — while still allowing genuine ties
  (no forced tiebreaks for small power-score gaps).
- We clarified scope explicitly with the user: **Champion %** keeps the
  Monte Carlo treatment (2,000 trials, binomial scoring) since "probability
  of winning it all" is meaningful as a probability. Only the **Group Stage
  + Bracket display** becomes deterministic.
- **Implementation** (`backend/app/simulate.py`):
  - Added `_simulate_score_deterministic(score_a, score_b, rng)` — rounds
    each side's `_expected_goals(...)` to the nearest int. No randomness.
  - Added `_play_knockout_match_deterministic(...)` — if rounded scores
    tie, the higher power-score team wins (ties broken toward home side),
    with a fixed 4-3 penalty display (no real formula for a shootout score).
  - `_simulate_once` now takes `score_fn` / `knockout_fn` params (default =
    the random versions, used by the Monte Carlo loop).
  - `run_simulation`: the 2,000-trial Monte Carlo loop now *only* computes
    `champion_counts`. A **separate** deterministic pass (fresh
    `Random(seed)`, used only for bracket-draw shuffling — i.e., which
    qualifiers land in which bracket half/match — not for scores) produces
    `rep_group_results` / `rep_bracket_rounds`.

## Current status

- Backend restarted and live on `:8000` with the new code. Only
  `backend/app/simulate.py` changed; `backend/tests/test_simulate.py`
  untouched and all 3 tests pass.
- **Group Stage & Bracket**: fully deterministic, reproducible (same
  weights → byte-identical result every time), always consistent with the
  Power Score ranking. Ties are real ties.
- **Champion %**: unchanged in spirit — genuine Monte Carlo probability
  over 2,000 trials, now using the binomial scoring model from Change 1.
- Verified: Solo-population Group G now gives Egypt 9 pts → Iran 6 pts →
  Belgium/NZ 1 pt each (tied) — exactly the population order. Default
  weights: deterministic bracket champion (France) matches the Monte Carlo
  favorite (France, 41%) in this run.

## Resolved — log-scale normalization for population & GDP

While testing the new deterministic mode with **population solo'd**, the
user noticed: **Germany (83.5M people) vs Curaçao (156K people) →
deterministic result Germany 2-1 Curaçao.**

That's only a 2-1 despite Germany having ~536x Curaçao's population. Why:

- Population (like every factor) is **min-max normalized across the
  48-team field** (`build_team_table.py`'s `normalize()`), i.e. squeezed
  onto a 0-1 "ruler" where 0 = smallest population in the pool (Curaçao,
  156K) and 1 = largest (USA, 340M).
- Germany's 83.5M lands at **0.245** on that ruler (because the USA's huge
  population stretches the top of the range). Curaçao is at **0.0**. The
  *gap* the formula sees is **0.245**, not "536x".
- `_expected_goals` turns a 0.245 gap into ~2.3 vs ~0.8 expected goals →
  rounds to 2-1. The *maximum possible* gap (1.0, e.g. USA vs Curaçao) would
  give 6 vs 0.15 → 6-0.

This is "working as designed" — population is treated like every other
factor (relative rank within the field, not raw real-world ratio). But the
user flagged that a 536x real-world gap producing only a 2-1 *feels*
underwhelming, and this is their **current open concern with the formula**.

**Implemented**: `population` and `gdp` now use `log_normalize()` (min-max
over `log10(value)`) instead of plain `normalize()`, in both
`backend/data_pipeline/build_team_table.py` and `mocks/generate_mocks.py`.
Data rebuilt (`teams.json`/`factors.json`, mocks resynced to
`frontend/src/mocks/`), backend restarted, all 3 tests still pass.

Result: Germany's normalized population went from 0.245 → **0.817**
(Curaçao stays at 0.0, since it's still the pool minimum). **Germany vs
Curaçao, solo population → 6-0** (was 2-1).

Verified no regressions:
- Group G solo-population standings: Egypt 1st (7pts, GD+4) → Iran 2nd
  (7pts, GD+3) → Belgium 3rd → New Zealand 4th — still matches population
  order, and individual results now look sensible too (Egypt 1-1 Iran,
  since both are "large" countries on a log scale; Iran 3-1 NZ).
- Default-weight champion probabilities **unchanged** (France 41%, Spain
  24.5%, Brazil 11.4%, Argentina 10.5%, England 7.4%) — the default blend
  (elo/fifa/squad/odds-heavy, gdp/population as minor "fun" factors) was
  never the problem, so it wasn't affected.
- Default-weight bottom-of-table reranking vs Elo-only is modest (e.g.
  Cabo Verde 41→47) and arguably *more* realistic than before — gdp/pop now
  meaningfully separate true micro-economies (Curaçao, Cabo Verde, ~0) from
  "normal small" ones (Qatar, Haiti, NZ, ~0.4-0.7), instead of bunching
  everyone near 0.

Considered but **not implemented** (math agent's recommendations #2/#3 —
solo-mode-specific goal-scale amplification, and most-likely-scoreline
instead of rounded expected goals): the log fix alone already produces the
expected Germany 6-0 Curaçao without either, so neither was needed.
Default weights were also reviewed and left unchanged (see above).

## Reference — key constants (`backend/app/simulate.py`)

```python
LOGISTIC_K = 6.0          # win-probability steepness
BASE_GOALS = 1.35         # avg goals between two equal teams
GOAL_SCALE = 2.2          # how strongly a power-score gap shifts expected goals
MAX_EXPECTED_GOALS = 6.0  # cap on expected goals (also = SCORING_CHANCES)
SCORING_CHANCES = 6       # binomial "chances per match"
```

## Suggested next steps

1. Resolve the log-scale-normalization question above with the user
   (Germany/Curaçao case) — decide whether to change `build_team_table.py`.
2. Once the formula is signed off, proceed to the UI/GUI enhancements
   listed in `HANDOVER.md` ("What's left / suggested next steps").
