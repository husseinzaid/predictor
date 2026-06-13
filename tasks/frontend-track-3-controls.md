# Frontend Track 3 — Factor Controls & Results Declutter

## Context

v1 (sliders, chart, rankings, bracket) and Track 2 (fixtures/scorelines) both
look good. This round is about making the **controls more useful for
understanding the model** and **trimming a redundant results section**. All
of this is additive — keep the existing layout/structure otherwise.

No contract changes in this task: `API_CONTRACT.md`, `src/types/index.ts`,
`src/api/client.ts`, `src/mocks/` are untouched. Everything below works with
the data you already have.

## 1. Combine "Champion probabilities" and "Power rankings"

Right now these are two separate sections that show almost the same
ranking twice — and with the full 48-team dataset, the champion
probabilities chart (one bar per team) has gotten very tall.

**What to do:**
- Replace the two sections with **one** "Power rankings" table that has
  both pieces of info per team: `Rank | Team | Power Score | Champion %`.
  - `Power Score` from `result.team_scores` (already has rank + score).
  - `Champion %` from `result.champion_probabilities` — note this array
    only includes teams with `probability > 0`, so most teams will show
    `0%` or `—`. Build a lookup map (`id -> probability`) and default to 0
    for teams not present.
  - Keep the existing score-bar styling (`.score-cell` / `.score-track`)
    for the Power Score column; add a similar small bar or just a percent
    for Champion %.
- Keep a **small** headline chart — e.g. just the **top 5-8** teams by
  champion probability, using the existing `BarChart` — as the "Headline
  result" visual at the top of the results stack. This keeps the nice
  visual without a 48-row chart. Reuse `CHART_COLORS`.
- Keep the `champion-pill` ("Your Champion: ...") as-is.

The full 48-row table can be long — that's fine, it's tabular data, not a
chart. Consider keeping it inside the existing `.table-wrap` (scrollable)
pattern if it gets unwieldy, but no special collapsing is required.

## 2. Factor enable/disable + "isolate" (solo)

Goal: let users understand what a *single* factor does by isolating it, or
exclude factors they don't care about, without having to drag every other
slider to 0 by hand.

**What to do:**
- Add a checkbox (or toggle) next to each factor's slider. Unchecked =
  factor is excluded from the simulation (contributes 0 regardless of its
  slider value).
- Add a small "Solo" / "Only this" button per factor. Clicking it: checks
  *only* this factor, unchecks all others. (Clicking another factor's
  checkbox afterwards re-enables normal multi-factor mode.)
- A factor that's unchecked should look visually disabled (dim the slider,
  disable the input) but **keep its slider value** — toggling it back on
  should restore the previous weight, not reset it.
- When calling `POST /api/simulate`, send `0` as the weight for any
  disabled factor (the backend normalizes weights, so disabled factors
  must be excluded from that normalization — sending `0` achieves that).
- The "% of total" readout per factor and the `totalWeight` calculation
  should also only consider enabled factors, so the percentages shown
  still sum to ~100% across enabled factors.

Suggested state shape: a new `enabled: Record<string, boolean>` map,
defaulting every factor to `true`. Keep the existing `weights` map
unchanged (slider values), and derive the actual payload sent to
`/api/simulate` by zeroing out disabled entries.

## 3. Randomize weights

Add a "Randomize" button next to "Reset to defaults" / "Simulate". Clicking
it assigns each **enabled** factor a random weight (e.g. an integer 0-100)
and leaves disabled factors alone. This is just for fun / exploration —
no special distribution needed, `Math.random() * 100` is fine.

## 4. Heads-up: factor descriptions are getting longer (and there may be a new factor)

The backend is rewriting the `description` text for each factor to be more
specific (e.g. distinguishing "Squad Quality" from "Elo Strength" — one is
current player ratings, the other is historical match-result strength), and
may add 1-2 new factors (e.g. splitting the GDP "fun" factor into separate
GDP and Population factors). You don't need to do anything special for new
factors — they flow through `factorsByCategory` automatically — but please
sanity-check that:
- Longer description text in `.factor-description` doesn't break the
  layout (wraps cleanly, doesn't overflow).
- An extra category/factor or two doesn't make the controls panel
  unreasonably long — a scrollable controls panel (if not already) would be
  fine if needed.

## How to verify your work

```
cd frontend
npm run dev          # click Simulate
npx tsc -b --noEmit  # type-check
```

Checklist:
- One combined rankings table (Rank/Team/Power/Champion %), plus a small
  top-5-8 headline chart — no full-height 48-row chart.
- Each factor has a working checkbox and "Solo" button; unchecking/solo-ing
  changes the simulation result on the next "Simulate" click.
- Percent-of-total readouts still sum to ~100% across enabled factors.
- "Randomize" button gives each enabled factor a new random value.
