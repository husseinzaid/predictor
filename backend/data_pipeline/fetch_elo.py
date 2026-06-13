"""World Football Elo ratings from eloratings.net.

The site is a thin SPA over plain TSV files with no auth required. The
"World" page (https://eloratings.net/World.tsv) lists every national team's
current global rating, one per row, with no header. Columns of interest:
  col[1] = global rank
  col[2] = eloratings.net's 2-letter team code (see fetch_team_list.elo_code)
  col[3] = current Elo rating

Writes: backend/data/raw/elo.csv with columns [team_id, elo_rating, elo_rank]
"""

from io import StringIO
from pathlib import Path

import pandas as pd
import requests

from . import fetch_team_list

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
WORLD_TSV_URL = "https://eloratings.net/World.tsv"


def load() -> pd.DataFrame:
    resp = requests.get(WORLD_TSV_URL, timeout=30)
    resp.raise_for_status()

    raw = pd.read_csv(StringIO(resp.text), sep="\t", header=None)
    elo = raw[[1, 2, 3]].copy()
    elo.columns = ["elo_rank", "elo_code", "elo_rating"]

    teams = fetch_team_list.load()[["team_id", "elo_code"]]
    merged = teams.merge(elo, on="elo_code", how="left")

    missing = merged[merged["elo_rating"].isna()]
    if not missing.empty:
        raise ValueError(f"No Elo rating found for: {missing['team_id'].tolist()}")

    return merged[["team_id", "elo_rating", "elo_rank"]]


if __name__ == "__main__":
    df = load()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(RAW_DIR / "elo.csv", index=False)
    print(f"Wrote {len(df)} rows to {RAW_DIR / 'elo.csv'}")
    print(df.sort_values("elo_rank").head(10))
