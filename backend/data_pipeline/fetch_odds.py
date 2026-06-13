"""Betting market implied win probabilities (World Cup outright winner).

Source: the-odds-api.com, `soccer_fifa_world_cup_winner` outright market.
Requires an API key, read from the ODDS_API_KEY env var (see backend/.env,
loaded via python-dotenv).

Decimal odds are converted to raw implied probabilities (1 / price) and
then normalized to sum to 1 across the 48 teams, which removes the
bookmaker's overround.

Writes: backend/data/raw/odds.csv with columns [team_id, betting_implied_prob]
"""

import os
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

from . import fetch_team_list

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
ODDS_URL = "https://api.the-odds-api.com/v4/sports/soccer_fifa_world_cup_winner/odds/"

# the-odds-api outcome names -> our team_id
NAME_TO_TEAM_ID = {
    "France": "FRA", "Spain": "ESP", "England": "ENG", "Portugal": "POR",
    "Brazil": "BRA", "Argentina": "ARG", "Germany": "GER", "Netherlands": "NED",
    "Norway": "NOR", "Belgium": "BEL", "Morocco": "MAR", "Mexico": "MEX",
    "Japan": "JPN", "Colombia": "COL", "USA": "USA", "Switzerland": "SUI",
    "Uruguay": "URU", "Turkey": "TUR", "Ecuador": "ECU", "Senegal": "SEN",
    "Croatia": "CRO", "Austria": "AUT", "Sweden": "SWE", "Paraguay": "PAR",
    "Ivory Coast": "CIV", "Scotland": "SCO", "South Korea": "KOR", "Australia": "AUS",
    "Canada": "CAN", "Algeria": "ALG", "Egypt": "EGY", "Czech Republic": "CZE",
    "Bosnia & Herzegovina": "BIH", "Ghana": "GHA", "Tunisia": "TUN", "Iran": "IRN",
    "Jordan": "JOR", "Uzbekistan": "UZB", "New Zealand": "NZL", "Qatar": "QAT",
    "Saudi Arabia": "KSA", "Cape Verde": "CPV", "South Africa": "RSA", "Curaçao": "CUW",
    "DR Congo": "COD", "Haiti": "HAI", "Iraq": "IRQ", "Panama": "PAN",
}


def load() -> pd.DataFrame:
    load_dotenv()
    api_key = os.environ["ODDS_API_KEY"]

    resp = requests.get(
        ODDS_URL,
        params={"apiKey": api_key, "regions": "uk,eu", "markets": "outrights"},
        timeout=30,
    )
    resp.raise_for_status()
    events = resp.json()
    outcomes = events[0]["bookmakers"][0]["markets"][0]["outcomes"]

    df = pd.DataFrame(
        [{"team_id": NAME_TO_TEAM_ID[o["name"]], "price": o["price"]} for o in outcomes]
    )
    raw_prob = 1 / df["price"]
    df["betting_implied_prob"] = raw_prob / raw_prob.sum()

    team_ids = set(fetch_team_list.load()["team_id"])
    assert set(df["team_id"]) == team_ids, "odds outcomes don't match the 48-team roster"
    assert df["team_id"].is_unique

    return df[["team_id", "betting_implied_prob"]]


if __name__ == "__main__":
    df = load()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(RAW_DIR / "odds.csv", index=False)
    print(f"Wrote {len(df)} teams to {RAW_DIR / 'odds.csv'}")
    print(df.sort_values("betting_implied_prob", ascending=False).head(10))
