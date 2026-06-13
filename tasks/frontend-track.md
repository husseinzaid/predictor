# Frontend Track — Sliders + Results UI

## Project in one paragraph

"World Cup Predictor" — a fun, fan-facing web tool where users adjust
weight sliders for ~8 prediction factors (FIFA ranking, Elo strength, squad
quality, betting odds, etc.), hit "Simulate World Cup", and get a
personalized champion-probability chart, group standings, and bracket. The
tagline is **"Your formula. Your World Cup champion."** — keep the tone fun
and fan-friendly, not a dense betting dashboard.

## What already exists — read these first

1. [`API_CONTRACT.md`](../API_CONTRACT.md) — the data shapes for
   `/api/factors`, `/api/teams`, `/api/simulate`. This is the source of
   truth for every type.
2. `frontend/src/types/index.ts` — TypeScript interfaces matching the
   contract exactly.
3. `frontend/src/api/client.ts` — `getFactors()`, `getTeams()`,
   `simulate(weights)`. **By default (`VITE_USE_MOCKS=true`, the existing
   `.env` default) these read from `frontend/src/mocks/*.json` instead of a
   real backend** — so you do not need the backend running at all. Build
   and test everything against the mocks.
4. `frontend/src/mocks/{factors,teams,simulate_response}.json` — realistic
   sample data: 16 teams, 4 groups (A-D), 8 factors, a 3-round bracket
   (Quarterfinals -> Semifinals -> Final). The real backend will later serve
   48 teams / 12 groups / a 5-round bracket (Round of 32 -> ... -> Final) —
   **do not hardcode team counts, group counts, or round counts/names**;
   always render from the arrays/lists in the response (`bracket.rounds`,
   `group_stage`, etc.).
5. `frontend/src/App.tsx` — current placeholder. It already wires up
   fetching factors/teams on load and calling `simulate()`. Replace/expand
   this, but keep the same data-fetching pattern (the `api/client.ts`
   functions).

The project is Vite + React + TypeScript. `npm run dev` from `frontend/`
runs it (already has `npm install` done, including `recharts` for charts).

## What to build

### 1. Landing / intro
Short header + one-sentence explainer using the tagline. Doesn't need to be
fancy — a heading, a sentence, and the controls below.

### 2. Factor sliders
- One slider per item in `getFactors()` response, range 0-100, initialized
  to `default_weight`.
- Group/visually separate by `category` if it reads nicely (e.g. a small
  label per category), but don't over-engineer — a flat list with
  `label` + `description` (as a tooltip or small subtext) is fine too.
- Show the user's current weight as a percentage of their total (i.e.
  normalize live in the UI) so it's clear the app "does the math" — e.g. if
  they crank one slider to max, the displayed percentages for others should
  visually shrink. This can be a simple derived value: `weight / sum(all weights) * 100`.
- A "Reset to defaults" button.

### 3. Simulate action
- "Simulate World Cup" button -> calls `simulate(weights)` (raw 0-100
  values; the backend/mock normalizes — don't pre-normalize before sending).
- Loading state while waiting.

### 4. Results view
Render the `SimulateResponse`:
- **Champion probabilities**: horizontal bar chart (recharts) of
  `champion_probabilities`, showing team name + flag (look up flag from the
  `teams` list by `id`) and probability as a percentage. This is the
  headline visual.
- **Explanation**: render `result.explanation` as a short text blurb under
  the chart.
- **Power rankings table**: `team_scores` — rank, flag, name, power score
  (e.g. as a 0-100 bar or just a number).
- **Group stage**: for each entry in `group_stage`, show the group name and
  a small standings table (team, points, qualified teams highlighted/bolded).
  Render in a responsive grid/wrap of group cards.
- **Bracket**: for each round in `bracket.rounds`, show the round `name`
  and its `matches` (home vs away, winner highlighted). A simple vertical
  list of rounds (each round as a column or stacked section) is enough for
  v1 — a fully connected bracket-tree graphic is a nice-to-have, not
  required. Highlight `bracket.champion` prominently at the end (e.g. "Your
  Champion: 🇪🇸 Spain").

### 5. Polish
- Reasonably responsive (mobile-friendly-ish; this will be shared on social
  media).
- Keep styling simple — plain CSS or CSS modules, no need for a component
  library. A clean, modern, "sports app" feel (cards, a bit of color per
  confederation/group is a nice touch but optional).

## Out of scope for this task

- Real backend integration (works via mocks; `VITE_USE_MOCKS=false` +
  pointing at a live backend is a later step, handled separately).
- Shareable links, leaderboards, accounts, LLM explanations — all v1.1+.
- Don't modify `API_CONTRACT.md`, `src/types/index.ts`, `src/api/client.ts`,
  or anything under `src/mocks/` or `backend/` — if the contract seems to
  need a change to make the UI work well, flag it instead of changing it
  unilaterally (so the backend stays in sync).

## How to verify your work

```
cd frontend
npm run dev          # check it renders and the Simulate flow works end to end
npx tsc -b --noEmit  # type-check
```

Sliders should respond live, "Simulate World Cup" should populate the
results view from `mocks/simulate_response.json` within a frame or two
(it's static data, no real latency).
