"""Official FIFA Men's World Ranking (rank + points).

Source: the "Top 20 rankings" table on the Wikipedia FIFA Men's World
Ranking page. This only covers ~20 of our 48 teams (the strongest ones) —
a full live table requires a paid API (see backend/data_pipeline/README.md).
For the remaining teams, build_team_table.py estimates fifa_points via a
linear fit against Elo rating, and marks them with fifa_rank_source=
"estimated" so this can be swapped for real data later without changing
the output shape.

Writes: backend/data/raw/fifa_ranking.csv with columns
[team_id, fifa_rank, fifa_points] — one row per team that appears in the
Wikipedia top-20 table (NOT all 48; build_team_table.py fills the rest).
"""

from io import StringIO
from pathlib import Path

import pandas as pd
import requests

from . import fetch_team_list

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
WIKI_URL = "https://en.wikipedia.org/wiki/FIFA_Men%27s_World_Ranking"

# Wikipedia team name -> our team name, where they differ.
NAME_OVERRIDES = {
    "Iran": "IR Iran",
}


def load() -> pd.DataFrame:
    resp = requests.get(WIKI_URL, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()

    tables = pd.read_html(StringIO(resp.text))
    top20 = tables[0]
    top20.columns = top20.iloc[2]
    top20 = top20.iloc[3:23].reset_index(drop=True)
    top20 = top20.rename(columns={"Rank": "fifa_rank", "Team": "name", "Points": "fifa_points"})
    top20["name"] = top20["name"].replace(NAME_OVERRIDES)
    top20["fifa_rank"] = pd.to_numeric(top20["fifa_rank"])
    top20["fifa_points"] = pd.to_numeric(top20["fifa_points"])

    teams = fetch_team_list.load()[["team_id", "name"]]
    merged = teams.merge(top20[["name", "fifa_rank", "fifa_points"]], on="name", how="inner")
    return merged[["team_id", "fifa_rank", "fifa_points"]]


if __name__ == "__main__":
    df = load()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(RAW_DIR / "fifa_ranking.csv", index=False)
    print(f"Wrote {len(df)}/48 teams (from FIFA top 20) to {RAW_DIR / 'fifa_ranking.csv'}")
    print(df.sort_values("fifa_rank"))
