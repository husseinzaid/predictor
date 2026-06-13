"""Club Elo ratings, aggregated to a per-country top-division strength score.

Source: the free api.clubelo.com CSV API, no key required. Querying with
today's date returns every club's current Elo, country and division level
(Level 1 = top division). We average Level-1 club Elo per country to get a
"league strength" score (e.g. England/Premier League comes out highest).

This is an *input* to fetch_squad_ratings.py (not yet implemented, needs a
Kaggle squad dataset to map each national team's players to a club ->
country/league), which will join this table to compute each national
team's `league_strength` factor. Until that pipeline exists,
build_team_table.py keeps `league_strength` as a neutral placeholder.

Writes: backend/data/raw/league_strength.csv with columns
[country, league_strength_elo, num_clubs]
"""

import datetime
from io import StringIO
from pathlib import Path

import pandas as pd
import requests

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
CLUBELO_URL = "http://api.clubelo.com/{date}"


def load() -> pd.DataFrame:
    today = datetime.date.today().isoformat()
    resp = requests.get(CLUBELO_URL.format(date=today), timeout=30)
    resp.raise_for_status()

    clubs = pd.read_csv(StringIO(resp.text))
    top_division = clubs[clubs["Level"] == 1]

    league_strength = (
        top_division.groupby("Country")["Elo"]
        .agg(league_strength_elo="mean", num_clubs="count")
        .reset_index()
        .rename(columns={"Country": "country"})
    )
    return league_strength.sort_values("league_strength_elo", ascending=False).reset_index(drop=True)


if __name__ == "__main__":
    df = load()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(RAW_DIR / "league_strength.csv", index=False)
    print(f"Wrote {len(df)} countries to {RAW_DIR / 'league_strength.csv'}")
    print(df.head(10))
