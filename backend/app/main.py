"""FastAPI app for the World Cup Prediction Simulator. See API_CONTRACT.md."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import data_loader, simulate
from .schemas import SimulateRequest

app = FastAPI(title="World Cup Predictor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

TEAMS = data_loader.load_teams()
FACTORS = data_loader.load_factors()
GROUPS = data_loader.build_groups(TEAMS)


@app.get("/api/factors")
def get_factors():
    return FACTORS


@app.get("/api/teams")
def get_teams():
    return TEAMS


@app.post("/api/simulate")
def post_simulate(request: SimulateRequest):
    return simulate.run_simulation(TEAMS, GROUPS, request.weights)
