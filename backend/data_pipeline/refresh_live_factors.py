"""Refresh the live-changing factors (elo, fifa_rank, betting_odds) in
backend/data/teams.json without re-running the full pipeline.

During a live tournament, three factors can meaningfully move day to day:
  - elo: eloratings.net recomputes every team's Elo rating after each match.
  - fifa_rank: ~2/3 of teams have their fifa_points *estimated* via a linear
    fit against elo_rating (see build_team_table.estimate_fifa_points), so
    this needs recomputing whenever elo changes, even though FIFA's official
    points/rank only update on fixed dates.
  - betting_odds: bookmakers re-price the outright-winner market continuously
    as teams advance or get eliminated -- the single highest-signal factor
    for "this team is still alive."

Everything else (squad ratings, league strength, GDP, population, travel,
climate, tournament history, home advantage) is fixed for the duration of a
single tournament. This script leaves those untouched, avoiding unnecessary
network calls -- especially to the-odds-api (metered quota) and the slow
Kaggle squad-ratings download that the full build_team_table.build() pipeline
would otherwise repeat.

Run manually or via a scheduled job:
    python3 -m data_pipeline.refresh_live_factors
"""

import json
from pathlib import Path

from . import fetch_elo, fetch_fifa_ranking, fetch_odds, fetch_team_list
from .build_team_table import estimate_fifa_points, normalize

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def refresh() -> None:
    teams = fetch_team_list.load()[["team_id"]]
    teams = teams.merge(fetch_elo.load(), on="team_id", how="left")
    teams = teams.merge(fetch_fifa_ranking.load(), on="team_id", how="left")
    teams = teams.merge(fetch_odds.load(), on="team_id", how="left")

    teams = estimate_fifa_points(teams)
    teams["fifa_rank_in_pool"] = teams["fifa_points"].rank(ascending=False, method="min").astype(int)

    teams["norm_elo"] = normalize(teams["elo_rating"])
    teams["norm_fifa"] = normalize(teams["fifa_points"])
    teams["norm_odds"] = normalize(teams["betting_implied_prob"])

    by_id = teams.set_index("team_id")

    team_records = json.loads((DATA_DIR / "teams.json").read_text())
    changed = []
    for record in team_records:
        row = by_id.loc[record["id"]]
        factors, raw = record["factors"], record["raw"]

        before = (factors["elo"], factors["fifa_rank"], factors["betting_odds"])

        factors["elo"] = round(float(row["norm_elo"]), 4)
        factors["fifa_rank"] = round(float(row["norm_fifa"]), 4)
        factors["betting_odds"] = round(float(row["norm_odds"]), 4)

        raw["elo_rating"] = round(float(row["elo_rating"]), 1)
        raw["fifa_points"] = round(float(row["fifa_points"]), 2)
        raw["fifa_rank"] = int(row["fifa_rank_in_pool"])
        raw["fifa_rank_source"] = row["fifa_rank_source"]
        raw["betting_implied_prob"] = round(float(row["betting_implied_prob"]), 4)

        after = (factors["elo"], factors["fifa_rank"], factors["betting_odds"])
        if before != after:
            changed.append(record["id"])

    (DATA_DIR / "teams.json").write_text(json.dumps(team_records, indent=2) + "\n")
    print(f"Refreshed elo/fifa_rank/betting_odds for {len(team_records)} teams.")
    print(f"{len(changed)} teams changed: {changed}")


if __name__ == "__main__":
    refresh()
