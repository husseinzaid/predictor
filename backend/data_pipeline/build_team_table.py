"""Join all fetch_* outputs into backend/data/teams.json and factors.json.

Run after the individual fetch_*.py scripts (or just run this — it calls
their `load()` functions directly, so no raw CSVs need to exist first).

Per-factor handling:
  - elo: min-max normalize `elo_rating` (eloratings.net).
  - fifa_rank: Wikipedia's "Top 20" table only covers ~19/48 teams. For the
    rest, `fifa_points` is estimated via a linear fit against `elo_rating`
    (the two are highly correlated). `fifa_rank_source` ("official" /
    "estimated") is kept in `raw` so this can be swapped for a full feed
    later. The normalized factor is min-max over `fifa_points` (higher =
    better), and `raw.fifa_rank` is each team's rank (1-48) within this
    pool by `fifa_points`.
  - tournament_experience: combines world_cup_titles, world_cup_appearances
    and best_finish (1=winner..8=never qualified, inverted so higher is
    better) into one score, then min-max normalized.
  - home_advantage: 1.0 for CONCACAF (2026 host confederation), else 0.0.
  - gdp: min-max normalize `gdp_total_usd` (total national GDP, not
    per-capita -- see fetch_gdp.py).
  - population: min-max normalize `population` (total national population,
    see fetch_population.py). A "fun" companion to gdp.
  - squad_quality: min-max normalize `squad_avg_rating` (EA FC 26 overall
    rating, averaged over each team's top players by nationality).
  - league_strength: min-max normalize `league_strength_rating` (clubelo
    top-division Elo, averaged over the leagues those players ply their
    trade in).
  - betting_odds: min-max normalize `betting_implied_prob` (FIFA World Cup
    Winner outright market, the-odds-api.com).
  - travel_distance: min-max normalize the *inverse* of `travel_distance_km`
    (see fetch_travel.py) -- shorter travel gives a higher factor value.
  - heat_adaptation: min-max normalize the *inverse* of `heat_disadvantage_c`
    (see fetch_climate.py) -- squads whose club-league climates are closer
    to (or hotter than) the 2026 World Cup venues' average game-time
    temperature score higher.

Writes: backend/data/teams.json, backend/data/factors.json
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import (
    fetch_climate,
    fetch_elo,
    fetch_fifa_ranking,
    fetch_gdp,
    fetch_odds,
    fetch_population,
    fetch_squad_ratings,
    fetch_team_list,
    fetch_travel,
    fetch_wc_history,
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Same 11 factors as mocks/generate_mocks.py — keep the contract identical
# between the mock and real datasets.
FACTORS = [
    {
        "id": "elo",
        "label": "Elo Strength",
        "description": (
            "Long-run team strength from the World Football Elo Ratings, "
            "built up gradually over years of match results (with bigger "
            "swings for wins against strong opponents and competitive "
            "matches). Reflects sustained on-pitch performance by the "
            "national team itself, not the individual players' current "
            "club form."
        ),
        "category": "form",
        "default_weight": 20,
    },
    {
        "id": "fifa_rank",
        "label": "FIFA Ranking",
        "description": (
            "Official FIFA World Ranking points. Conceptually similar to "
            "Elo -- both are long-run, results-based ratings -- but FIFA "
            "uses its own formula and weights recent matches and "
            "competition importance (World Cup > friendly) more heavily. "
            "Usually tracks Elo closely, but can diverge for teams that "
            "play few official fixtures."
        ),
        "category": "ranking",
        "default_weight": 15,
    },
    {
        "id": "squad_quality",
        "label": "Squad Quality",
        "description": (
            "Average EA Sports FC 26 player rating across each squad's "
            "best ~26 eligible players right now. This is a snapshot of "
            "current individual talent at club level -- independent of "
            "how the national team itself has performed (a team can have "
            "world-class individual players but a poor national-team "
            "record, or vice versa)."
        ),
        "category": "squad",
        "default_weight": 15,
    },
    {
        "id": "league_strength",
        "label": "League Strength",
        "description": (
            "Average strength (clubelo top-division rating) of the "
            "domestic leagues those same squad players currently play in "
            "week to week. Distinguishes a squad of players competing in "
            "the Premier League or La Liga from one whose players mostly "
            "play in weaker domestic leagues, even if their individual "
            "Squad Quality ratings are similar."
        ),
        "category": "squad",
        "default_weight": 10,
    },
    {
        "id": "betting_odds",
        "label": "Betting Market",
        "description": (
            "Implied win probability from bookmaker outright odds for the "
            "World Cup winner. A single number that aggregates everything "
            "the market is pricing in -- form, squad news, injuries, "
            "fixture difficulty -- independent of any of the other "
            "factors here."
        ),
        "category": "market",
        "default_weight": 15,
    },
    {
        "id": "tournament_experience",
        "label": "Tournament Experience",
        "description": (
            "World Cup pedigree: titles won, total appearances, and best "
            "-ever finish, combined into one score. Rewards teams with a "
            "track record of performing specifically at this tournament "
            "(big-game temperament, squad depth for a long run), "
            "regardless of their current form."
        ),
        "category": "history",
        "default_weight": 10,
    },
    {
        "id": "home_advantage",
        "label": "Home Continent Advantage",
        "description": (
            "Flat boost for teams from the host confederation (CONCACAF "
            "for 2026): shorter travel, familiar time zones and climate, "
            "and a larger home-region crowd. Applies equally to every "
            "CONCACAF team regardless of their other ratings."
        ),
        "category": "fun",
        "default_weight": 5,
    },
    {
        "id": "gdp",
        "label": "Economic Power (GDP)",
        "description": (
            "A 'fun' wildcard based on each country's total GDP -- no "
            "direct footballing basis, though wealthier football "
            "federations can invest more in facilities, youth academies "
            "and coaching. Deliberately uses *total* GDP rather than "
            "GDP per capita, so it rewards large economies rather than "
            "just rich-per-person ones (see Population for the other "
            "half of that story)."
        ),
        "category": "fun",
        "default_weight": 10,
    },
    {
        "id": "population",
        "label": "Population",
        "description": (
            "Another 'fun' wildcard based on each country's total "
            "population -- a bigger pool of players to draw talent from, "
            "though obviously no guarantee of footballing success on its "
            "own. Pairs with the GDP factor: a country can score high on "
            "one, the other, both, or neither."
        ),
        "category": "fun",
        "default_weight": 5,
    },
    {
        "id": "travel_distance",
        "label": "Travel Burden",
        "description": (
            "How far a team has to travel between its assigned 2026 World "
            "Cup venues (group stage through the Round of 32, assuming it "
            "wins its group) -- shorter travel means less jet lag and more "
            "recovery time between matches. Unlike Home Continent "
            "Advantage, which is just a flat yes/no for the host "
            "confederation, this varies continuously based on each team's "
            "actual venue assignments."
        ),
        "category": "fun",
        "default_weight": 5,
    },
    {
        "id": "heat_adaptation",
        "label": "Heat Adaptation",
        "description": (
            "How used each squad is to playing in the heat: compares the "
            "average June-July temperature in the countries where each "
            "squad's club-league players normally ply their trade against "
            "the average June-July temperature across the 16 2026 World Cup "
            "host cities (which range from a cool ~18C in Vancouver and "
            "Mexico City to a sweltering ~30C in Monterrey, Houston, Dallas "
            "and Miami). Squads whose players are used to noticeably cooler "
            "club-league climates take a small penalty here; squads already "
            "accustomed to similar-or-hotter conditions are unaffected. "
            "Unlike Travel Burden, which is about distances between venues, "
            "this is purely about climate."
        ),
        "category": "fun",
        "default_weight": 5,
    },
]


def normalize(series: pd.Series) -> pd.Series:
    lo, hi = series.min(), series.max()
    span = (hi - lo) or 1
    return (series - lo) / span


def estimate_fifa_points(df: pd.DataFrame) -> pd.DataFrame:
    known = df.dropna(subset=["fifa_points"])
    slope, intercept = np.polyfit(known["elo_rating"], known["fifa_points"], 1)

    df = df.copy()
    df["fifa_rank_source"] = np.where(df["fifa_points"].notna(), "official", "estimated")
    estimated = intercept + slope * df["elo_rating"]
    df["fifa_points"] = df["fifa_points"].fillna(estimated)
    return df


def build() -> tuple[list[dict], list[dict]]:
    teams = fetch_team_list.load()
    teams = teams.merge(fetch_elo.load(), on="team_id", how="left")
    teams = teams.merge(fetch_fifa_ranking.load(), on="team_id", how="left")
    teams = teams.merge(fetch_wc_history.load(), on="team_id", how="left")
    teams = teams.merge(fetch_gdp.load(), on="team_id", how="left")
    teams = teams.merge(fetch_population.load(), on="team_id", how="left")
    teams = teams.merge(fetch_squad_ratings.load(), on="team_id", how="left")
    teams = teams.merge(fetch_odds.load(), on="team_id", how="left")
    teams = teams.merge(fetch_travel.load(), on="team_id", how="left")
    teams = teams.merge(fetch_climate.load(), on="team_id", how="left")

    teams = estimate_fifa_points(teams)
    teams["fifa_rank_in_pool"] = teams["fifa_points"].rank(ascending=False, method="min").astype(int)

    teams["tournament_experience_raw"] = (
        teams["world_cup_titles"] * 3
        + teams["world_cup_appearances"] * 0.5
        + (9 - teams["best_finish"])
    )

    teams["home_advantage"] = (teams["confederation"] == "CONCACAF").astype(float)

    norm_elo = normalize(teams["elo_rating"])
    norm_fifa = normalize(teams["fifa_points"])
    norm_experience = normalize(teams["tournament_experience_raw"])
    norm_gdp = normalize(teams["gdp_total_usd"])
    norm_population = normalize(teams["population"])
    norm_squad = normalize(teams["squad_avg_rating"])
    norm_league = normalize(teams["league_strength_rating"])
    norm_odds = normalize(teams["betting_implied_prob"])
    norm_travel = 1 - normalize(teams["travel_distance_km"])
    norm_heat = 1 - normalize(teams["heat_disadvantage_c"])

    team_records = []
    for i, row in teams.iterrows():
        team_records.append({
            "id": row["team_id"],
            "name": row["name"],
            "flag": row["flag"],
            "confederation": row["confederation"],
            "group": row["group"],
            "factors": {
                "elo": round(norm_elo[i], 4),
                "fifa_rank": round(norm_fifa[i], 4),
                "squad_quality": round(norm_squad[i], 4),
                "league_strength": round(norm_league[i], 4),
                "betting_odds": round(norm_odds[i], 4),
                "tournament_experience": round(norm_experience[i], 4),
                "home_advantage": row["home_advantage"],
                "gdp": round(norm_gdp[i], 4),
                "population": round(norm_population[i], 4),
                "travel_distance": round(norm_travel[i], 4),
                "heat_adaptation": round(norm_heat[i], 4),
            },
            "raw": {
                "elo_rating": round(row["elo_rating"], 1),
                "fifa_points": round(row["fifa_points"], 2),
                "fifa_rank": int(row["fifa_rank_in_pool"]),
                "fifa_rank_source": row["fifa_rank_source"],
                "squad_avg_rating": round(row["squad_avg_rating"], 1),
                "league_strength_rating": round(row["league_strength_rating"], 1),
                "betting_implied_prob": round(row["betting_implied_prob"], 4),
                "world_cup_titles": int(row["world_cup_titles"]),
                "world_cup_appearances": int(row["world_cup_appearances"]),
                "gdp_total_usd": round(row["gdp_total_usd"], 0),
                "population": int(row["population"]),
                "travel_distance_km": int(row["travel_distance_km"]),
                "squad_climate_c": round(row["squad_climate_c"], 1),
                "heat_disadvantage_c": round(row["heat_disadvantage_c"], 1),
            },
        })

    return team_records, FACTORS


if __name__ == "__main__":
    team_records, factors = build()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "teams.json").write_text(json.dumps(team_records, indent=2) + "\n")
    (DATA_DIR / "factors.json").write_text(json.dumps(factors, indent=2) + "\n")

    print(f"Wrote {len(team_records)} teams to {DATA_DIR / 'teams.json'}")
    print(f"Wrote {len(factors)} factors to {DATA_DIR / 'factors.json'}")

    estimated = [t["id"] for t in team_records if t["raw"]["fifa_rank_source"] == "estimated"]
    print(f"{len(estimated)} teams have estimated FIFA points: {estimated}")
