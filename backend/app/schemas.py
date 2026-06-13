"""Pydantic models matching API_CONTRACT.md."""

from typing import Dict, List, Optional

from pydantic import BaseModel


class SimulateRequest(BaseModel):
    weights: Dict[str, float]


class TeamScore(BaseModel):
    id: str
    name: str
    power_score: float
    rank: int


class ChampionProbability(BaseModel):
    id: str
    name: str
    probability: float


class GroupMatch(BaseModel):
    matchday: int
    home: str
    away: str
    home_goals: int
    away_goals: int


class GroupStanding(BaseModel):
    id: str
    name: str
    played: int
    won: int
    drawn: int
    lost: int
    goals_for: int
    goals_against: int
    goal_difference: int
    points: int
    qualified: bool


class GroupResult(BaseModel):
    group: str
    matches: List[GroupMatch]
    standings: List[GroupStanding]


class Penalties(BaseModel):
    home: int
    away: int


class BracketMatch(BaseModel):
    home: str
    away: str
    home_goals: int
    away_goals: int
    winner: str
    penalties: Optional[Penalties] = None


class BracketRound(BaseModel):
    name: str
    matches: List[BracketMatch]


class Bracket(BaseModel):
    rounds: List[BracketRound]
    champion: str


class SimulateResponse(BaseModel):
    weights_used: Dict[str, float]
    team_scores: List[TeamScore]
    champion_probabilities: List[ChampionProbability]
    group_stage: List[GroupResult]
    bracket: Bracket
    explanation: str
