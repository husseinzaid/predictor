"""2026 World Cup travel distances (the 'fun' travel-fatigue factor).

Hand-curated from a third-party analysis of the official 2026 World Cup
schedule and venue assignments:
https://mikami3345.cloudfree.jp/WorldCup2026/English-ver/TravelDistanceRanking-En.html

That source gives each team's total *minimum* travel distance (km, as the
crow flies between consecutive venues) for the group stage + Round of 32
slot it's assigned to in the official bracket, assuming the team wins its
group. Two of the original 48 slots were intercontinental-playoff slots not
yet resolved when that page was written ("Playoff 1" in Group K, "Playoff 2"
in Group I) -- those have been mapped to the teams that ultimately filled
those slots (COD and IRQ, per fetch_team_list.py's groups).

This is necessarily an approximation (it doesn't account for a team's
training-camp location before the tournament, or how the bracket plays out
if a team finishes 2nd/3rd instead of winning its group), but it's a
reasonable proxy for how much a team's travel logistics matter -- shorter
distances mean less jet lag/fatigue and more time to train between matches.

Writes: backend/data/raw/travel.csv with columns [team_id, travel_distance_km]
"""

from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

# (team_id, travel_distance_km)
DISTANCES = [
    ("MEX", 5163),
    ("KOR", 5586),
    ("EGY", 6133),
    ("FRA", 6137),
    ("NOR", 6183),
    ("SEN", 6365),
    ("QAT", 6480),
    ("IRQ", 6791),  # "Playoff 2" (Group I)
    ("ARG", 6870),
    ("CIV", 7087),
    ("SUI", 7108),
    ("PAR", 7395),
    ("IRN", 7678),
    ("NZL", 7678),
    ("AUS", 8124),
    ("PAN", 8150),
    ("CAN", 8168),
    ("GER", 8521),
    ("JOR", 8522),
    ("GHA", 8599),
    ("CUW", 8712),
    ("CZE", 8767),
    ("BEL", 8833),
    ("HAI", 8850),
    ("RSA", 8883),
    ("MAR", 9155),
    ("TUR", 9235),
    ("ECU", 9301),
    ("AUT", 9466),
    ("BRA", 9548),
    ("SCO", 9797),
    ("SWE", 9831),
    ("CRO", 9948),
    ("BIH", 10043),
    ("ENG", 10399),
    ("USA", 10485),
    ("JPN", 10522),
    ("UZB", 10756),
    ("POR", 10887),
    ("NED", 10933),
    ("TUN", 11115),
    ("ALG", 11192),
    ("COD", 12076),  # "Playoff 1" (Group K)
    ("COL", 12221),
    ("KSA", 12492),
    ("ESP", 12637),
    ("URU", 12700),
    ("CPV", 12921),
]

COLUMNS = ["team_id", "travel_distance_km"]


def load() -> pd.DataFrame:
    df = pd.DataFrame(DISTANCES, columns=COLUMNS)
    assert len(df) == 48
    assert df["team_id"].is_unique
    return df


if __name__ == "__main__":
    df = load()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(RAW_DIR / "travel.csv", index=False)
    print(f"Wrote {len(df)} teams to {RAW_DIR / 'travel.csv'}")
    print(df.sort_values("travel_distance_km").head(5))
    print(df.sort_values("travel_distance_km").tail(5))
