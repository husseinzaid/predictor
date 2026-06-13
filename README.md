# World Cup Predictor

"Your formula. Your World Cup champion." — adjust the weight of FIFA
ranking, squad quality, betting odds, and other factors, then simulate the
2026 World Cup with your own formula.

- [PLAN.md](PLAN.md) — roadmap and current status.
- [API_CONTRACT.md](API_CONTRACT.md) — data shapes shared by frontend and
  backend.
- [tasks/](tasks/) — self-contained task briefs for parallel work.

## Layout

```
backend/         FastAPI app (app/) + data pipeline (data_pipeline/)
frontend/        Vite + React + TypeScript
mocks/           Sample fixtures matching API_CONTRACT.md
tasks/           Task briefs for parallel agents
```

## Running locally

```
# Backend
cd backend && .venv/bin/uvicorn app.main:app --reload

# Frontend (defaults to mock data, no backend required)
cd frontend && npm run dev
```
