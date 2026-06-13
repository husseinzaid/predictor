# World Cup Predictor — v1 Plan

"Your formula. Your World Cup champion." Users adjust weights for ~8
factors, hit Simulate, and get a personalized bracket + champion
probabilities. Full product context: see the original brief (not in repo)
and [API_CONTRACT.md](API_CONTRACT.md) for the concrete data shapes.

## Current state (done)

- Repo scaffolded: `backend/` (FastAPI), `frontend/` (Vite + React + TS),
  `mocks/`, `tasks/`.
- [API_CONTRACT.md](API_CONTRACT.md) defines `/api/factors`, `/api/teams`,
  `/api/simulate` — the contract both tracks build against.
- `mocks/generate_mocks.py` produces `mocks/{factors,teams,simulate_response}.json`
  — a realistic 16-team / 4-group "mini World Cup" sample (same shape the
  real 48-team API will return, just smaller). Copied into
  `backend/data/` (live API currently serves this) and
  `frontend/src/mocks/` (frontend dev fallback).
- Backend: `app/main.py` (3 endpoints), `app/simulate.py` (scoring +
  Monte Carlo bracket simulation, generalizes to any group-stage shape —
  works for 16 *and* 48 teams unchanged), `app/schemas.py`,
  `app/data_loader.py`. Tests pass (`backend/.venv/bin/python -m pytest`).
  Verified end-to-end with `uvicorn app.main:app`.
- Frontend: minimal placeholder `App.tsx` that fetches factors/teams and
  calls `/api/simulate` via `src/api/client.ts`, which reads from
  `src/mocks/*.json` by default (`VITE_USE_MOCKS=true`) so the frontend
  doesn't need the backend running at all to develop against.
- `data_pipeline/` stubs (`backend/data_pipeline/`) — one file per data
  source, each with a docstring describing what it needs to do. None
  implemented yet.

## Two parallel workstreams from here

**Track A — Data + backend (this agent)**
1. Implement `data_pipeline/fetch_team_list.py` — curate the real 48-team
   2026 roster (groups, confederations).
2. Implement `fetch_elo.py`, `fetch_fifa_ranking.py`, `fetch_wc_history.py`,
   `fetch_gdp.py` (simplest/no-key sources first).
3. Implement `fetch_clubelo.py` + `fetch_squad_ratings.py` (EA FC ratings
   join — the most involved one).
4. Implement `fetch_odds.py` (needs an API key decision).
5. `build_team_table.py` joins everything -> real `backend/data/teams.json`
   (48 teams) + `factors.json`. Swap into the API — no contract change
   needed.
6. Tune `simulate.py` (draw probability, logistic K, Monte Carlo trial
   count) once real data is in, and expand `tests/`.
7. Deploy backend (Render/Fly.io).

**Track B — Frontend (helper agent)**
See [tasks/frontend-track.md](tasks/frontend-track.md). Builds the slider
UI, results view (probability chart, group standings, bracket), and
landing page — entirely against the mock fixtures, so it doesn't block on
Track A. Once Track A lands the real 48-team data, the frontend should work
unchanged (just bigger arrays) — flip `VITE_USE_MOCKS=false` to point at
the live backend.

## Running things locally

Backend:
```
cd backend
.venv/bin/uvicorn app.main:app --reload
```

Frontend:
```
cd frontend
npm run dev
```

## Deferred to v1.1+

Travel/climate fatigue, head-to-head, injuries, coaching, market value,
shareable links, LLM-generated explanations, leaderboards, accounts.
