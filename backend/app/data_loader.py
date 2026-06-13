"""Loads the team/factor dataset that the API serves.

For v1 this reads static JSON files from backend/data/. Those files are
currently the 16-team mock dataset (copied from mocks/) so the API is
usable end to end immediately. The data_pipeline/ scripts will replace
backend/data/teams.json with the real 48-team 2026 World Cup dataset
without requiring any change to this loader or the API shape.
"""

import json
from pathlib import Path
from typing import Dict, List

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_teams() -> List[dict]:
    return json.loads((DATA_DIR / "teams.json").read_text())


def load_factors() -> List[dict]:
    return json.loads((DATA_DIR / "factors.json").read_text())


def build_groups(teams: List[dict]) -> Dict[str, List[str]]:
    groups: Dict[str, List[str]] = {}
    for team in teams:
        groups.setdefault(team["group"], []).append(team["id"])
    return groups
