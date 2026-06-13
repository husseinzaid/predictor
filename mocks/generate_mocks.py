"""
Generates mocks/teams.json, mocks/factors.json, mocks/simulate_response.json.

These fixtures let the frontend be built against a stable, realistic shape
of the real API (see ../API_CONTRACT.md) before the backend is ready.
Uses a small 16-team "mini World Cup" (4 groups of 4 -> QF -> SF -> Final)
so the bracket shape is simple but structurally identical to the real
48-team tournament (which will just have two extra rounds: R32, R16).

Run: python3 generate_mocks.py
"""

import json
import sys
from pathlib import Path

OUT_DIR = Path(__file__).parent

# Reuse the real simulation engine (backend/app/simulate.py) so the mock
# response shape can never drift from the live API's shape.
sys.path.insert(0, str(OUT_DIR.parent / "backend"))
from app import data_loader, simulate  # noqa: E402

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

# raw stats: [confederation, group, fifa_rank, elo, squad_quality(0-99),
#             league_strength(0-99), betting_odds(0-1), wc_titles(0-5),
#             gdp_total_b_usd, population_m, travel_distance_km,
#             heat_disadvantage_c]
TEAMS_RAW = {
    "USA": ("CONCACAF", "A", 14, 1850, 78, 80, 0.03, 0, 27000, 340, 10485, 5.5),
    "MEX": ("CONCACAF", "A", 12, 1870, 76, 70, 0.02, 0, 1850, 128, 5163, 3.8),
    "JPN": ("AFC", "A", 17, 1840, 77, 75, 0.02, 0, 4200, 124, 10522, 6.9),
    "CRO": ("UEFA", "A", 9, 1960, 80, 84, 0.04, 0, 80, 3.9, 9948, 3.9),
    "BRA": ("CONMEBOL", "B", 5, 2089, 85, 88, 0.14, 5, 2200, 215, 9548, 3.1),
    "POR": ("UEFA", "B", 6, 2010, 84, 86, 0.06, 0, 270, 10.3, 10887, 2.6),
    "MAR": ("CAF", "B", 13, 1860, 76, 78, 0.02, 0, 140, 37, 9155, 2.7),
    "CAN": ("CONCACAF", "B", 24, 1790, 74, 65, 0.01, 0, 2200, 39, 8168, 4.4),
    "ARG": ("CONMEBOL", "C", 1, 2113, 86, 87, 0.16, 3, 640, 46, 6870, 5.2),
    "ENG": ("UEFA", "C", 4, 2042, 84, 92, 0.10, 1, 3300, 67, 10399, 7.6),
    "BEL": ("UEFA", "C", 10, 1955, 81, 89, 0.03, 0, 590, 11.7, 8833, 5.0),
    "ITA": ("UEFA", "C", 11, 1945, 80, 87, 0.03, 4, 2200, 59, 9500, 4.1),
    "FRA": ("UEFA", "D", 3, 2063, 87, 90, 0.13, 2, 3000, 66, 6137, 2.4),
    "ESP": ("UEFA", "D", 2, 2171, 86, 89, 0.12, 1, 1600, 47, 12637, 3.7),
    "GER": ("UEFA", "D", 7, 1980, 83, 88, 0.07, 4, 4500, 84, 8521, 6.1),
    "NED": ("UEFA", "D", 8, 1975, 82, 85, 0.05, 0, 1100, 17.9, 10933, 6.7),
}

TEAM_NAMES = {
    "USA": "United States", "MEX": "Mexico", "JPN": "Japan", "CRO": "Croatia",
    "BRA": "Brazil", "POR": "Portugal", "MAR": "Morocco", "CAN": "Canada",
    "ARG": "Argentina", "ENG": "England", "BEL": "Belgium", "ITA": "Italy",
    "FRA": "France", "ESP": "Spain", "GER": "Germany", "NED": "Netherlands",
}

FLAGS = {
    "USA": "\U0001F1FA\U0001F1F8", "MEX": "\U0001F1F2\U0001F1FD", "JPN": "\U0001F1EF\U0001F1F5", "CRO": "\U0001F1ED\U0001F1F7",
    "BRA": "\U0001F1E7\U0001F1F7", "POR": "\U0001F1F5\U0001F1F9", "MAR": "\U0001F1F2\U0001F1E6", "CAN": "\U0001F1E8\U0001F1E6",
    "ARG": "\U0001F1E6\U0001F1F7", "ENG": "\U0001F1EC\U0001F1E7", "BEL": "\U0001F1E7\U0001F1EA", "ITA": "\U0001F1EE\U0001F1F9",
    "FRA": "\U0001F1EB\U0001F1F7", "ESP": "\U0001F1EA\U0001F1F8", "GER": "\U0001F1E9\U0001F1EA", "NED": "\U0001F1F3\U0001F1F1",
}


def normalize(values, invert=False):
    lo, hi = min(values), max(values)
    span = hi - lo or 1
    if invert:
        return [(hi - v) / span for v in values]
    return [(v - lo) / span for v in values]


def build_teams():
    ids = list(TEAMS_RAW.keys())
    fifa_ranks = [TEAMS_RAW[t][2] for t in ids]
    elos = [TEAMS_RAW[t][3] for t in ids]
    squads = [TEAMS_RAW[t][4] for t in ids]
    leagues = [TEAMS_RAW[t][5] for t in ids]
    odds = [TEAMS_RAW[t][6] for t in ids]
    titles = [TEAMS_RAW[t][7] for t in ids]
    gdps = [TEAMS_RAW[t][8] for t in ids]
    populations = [TEAMS_RAW[t][9] for t in ids]
    travel_distances = [TEAMS_RAW[t][10] for t in ids]
    heat_disadvantages = [TEAMS_RAW[t][11] for t in ids]

    norm_fifa = normalize(fifa_ranks, invert=True)
    norm_elo = normalize(elos)
    norm_squad = normalize(squads)
    norm_league = normalize(leagues)
    norm_odds = normalize(odds)
    norm_titles = [t / 5 for t in titles]
    norm_gdp = normalize(gdps)
    norm_population = normalize(populations)
    norm_travel = normalize(travel_distances, invert=True)
    norm_heat = normalize(heat_disadvantages, invert=True)

    teams = []
    for i, tid in enumerate(ids):
        conf, group, fifa_rank, elo, squad, league, odd, wc_titles, gdp, population, travel_km, heat_disadvantage_c = TEAMS_RAW[tid]
        teams.append({
            "id": tid,
            "name": TEAM_NAMES[tid],
            "flag": FLAGS[tid],
            "confederation": conf,
            "group": group,
            "factors": {
                "elo": round(norm_elo[i], 3),
                "fifa_rank": round(norm_fifa[i], 3),
                "squad_quality": round(norm_squad[i], 3),
                "league_strength": round(norm_league[i], 3),
                "betting_odds": round(norm_odds[i], 3),
                "tournament_experience": round(norm_titles[i], 3),
                "home_advantage": 1.0 if conf == "CONCACAF" else 0.0,
                "gdp": round(norm_gdp[i], 3),
                "population": round(norm_population[i], 3),
                "travel_distance": round(norm_travel[i], 3),
                "heat_adaptation": round(norm_heat[i], 3),
            },
            "raw": {
                "fifa_rank": fifa_rank,
                "elo_rating": elo,
                "squad_avg_rating": squad,
                "league_strength_rating": league,
                "betting_implied_prob": odd,
                "world_cup_titles": wc_titles,
                "gdp_total_usd": gdp * 1_000_000_000,
                "population": int(population * 1_000_000),
                "travel_distance_km": travel_km,
                "heat_disadvantage_c": heat_disadvantage_c,
            },
        })
    return teams


def main():
    teams = build_teams()
    groups = data_loader.build_groups(teams)
    weights = {f["id"]: f["default_weight"] for f in FACTORS}

    simulate_response = simulate.run_simulation(teams, groups, weights)

    (OUT_DIR / "factors.json").write_text(json.dumps(FACTORS, indent=2) + "\n")
    (OUT_DIR / "teams.json").write_text(json.dumps(teams, indent=2) + "\n")
    (OUT_DIR / "simulate_response.json").write_text(json.dumps(simulate_response, indent=2) + "\n")
    print("Wrote factors.json, teams.json, simulate_response.json")


if __name__ == "__main__":
    main()
