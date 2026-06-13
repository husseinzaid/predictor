# Frontend Track 2 — Full Fixtures & Scorelines

## Context

Nice work on v1 — the sliders, champion chart, group cards and bracket all
work. The next big ask from the product side: **this needs to feel like a
real tournament predictor for people doing sweepstakes/tipping**, which
means every match needs a predicted *score*, not just a winner — group
stage fixtures (all 6 per group) and every knockout match.

The backend/contract side has already been updated to support this:

1. [`API_CONTRACT.md`](../API_CONTRACT.md) — re-read the `POST
   /api/simulate` section, it changed shape.
2. `frontend/src/types/index.ts` — updated to match (new `GroupMatch`,
   expanded `GroupStanding`, expanded `BracketMatch`, new `Penalties`).
3. `frontend/src/mocks/simulate_response.json` — regenerated with the new
   shape (still the 16-team / 4-group / 3-round mock).

**Don't re-read or redo your v1 work from scratch** — this is additive.
The chart, power rankings table, and overall layout are good as-is.

## What changed in the data

### `group_stage[].matches` (new)

Each group now has a `matches` array — all 6 round-robin fixtures for that
group of 4, each with a `matchday` (1, 2, or 3) and a final score:

```json
{ "matchday": 1, "home": "USA", "away": "MEX", "home_goals": 2, "away_goals": 1 }
```

### `group_stage[].standings` (expanded)

Each standing row now has the full table stats, not just `points`:

```json
{
  "id": "USA", "name": "United States",
  "played": 3, "won": 1, "drawn": 1, "lost": 1,
  "goals_for": 4, "goals_against": 4, "goal_difference": 0,
  "points": 4, "qualified": true
}
```

### `bracket.rounds[].matches` (expanded)

Every knockout match now has a score, and `penalties` (nullable) for
matches decided by a shootout:

```json
{
  "home": "ARG", "away": "BRA",
  "home_goals": 1, "away_goals": 1,
  "winner": "BRA",
  "penalties": { "home": 3, "away": 4 }
}
```

`penalties` is `null` for matches decided in normal time.

## What to build

### 1. Group stage fixtures

For each group card (where you currently render the standings table), add
a fixtures list above or beside it:

- Group the 6 `matches` by `matchday` (1/2/3) — e.g. "Matchday 1", "Matchday
  2", "Matchday 3" as small subheadings, each with its 2 matches.
- Render each match as a scoreline, e.g. `🇺🇸 United States 2 - 1 🇲🇽 Mexico`
  (look up flag/name from the `teams` list by id, same pattern you already
  use elsewhere).
- Keep it compact — this roughly doubles the content of each group card, so
  a small font / tight spacing is fine. A simple stacked list per matchday
  is enough; no need for a calendar/grid layout.

### 2. Group standings table

Extend the existing standings table with the new columns: `P` (played),
`W`, `D`, `L`, `GF`, `GA`, `GD`, `Pts`. The backend already returns rows
sorted correctly (points, then goal difference, then goals for), so just
render in the given order. Keep `qualified` rows highlighted as before.

A reasonable column order: `Team | P | W | D | L | GF | GA | GD | Pts`.

### 3. Bracket scorelines

In each bracket match card (currently showing team name + "Winner" badge),
add the score: `home_goals - away_goals` between the two team rows (or next
to each team). If `penalties` is non-null, show it as a small annotation,
e.g. `(pen. 4-3)` — and the `winner` field already reflects the shootout
result, so the existing winner-highlight logic doesn't need to change.

### 4. Polish

- This is more information density per card — feel free to use smaller
  font sizes / tighter padding for the fixture lists and table additions so
  cards don't become huge. Collapsible/accordion sections are a nice-to-have
  if it gets crowded, but not required for v1.
- Mobile: the standings table will need horizontal scroll on narrow screens
  (you likely already have `.table-wrap { overflow-x: auto; }` — reuse it).

## Out of scope

- Don't touch `API_CONTRACT.md`, `src/types/index.ts`, `src/api/client.ts`,
  anything under `src/mocks/`, or `backend/` — the shapes are final for this
  task. If something doesn't fit, flag it instead of changing the contract.
- No new factors/sliders — this task is purely about rendering the richer
  `group_stage` and `bracket` data that's now in the response.

## How to verify your work

```
cd frontend
npm run dev          # click Simulate, check every group shows 6 fixtures + full table
npx tsc -b --noEmit  # type-check
```

Every group should show 6 scored fixtures across 3 matchdays and an 8-9
column standings table. Every bracket match (including the Final) should
show a score, with `(pen. X-Y)` on any match that needed a shootout (rare
with 16 teams / 3 knockout rounds, but possible).
