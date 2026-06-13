"""World Cup history: titles, appearances, best finish per team.

Hand-curated from Wikipedia's "World Cup record" tables, covering the 21
tournaments held 1930-2022 (the 2026 edition is upcoming, so it is not
counted). Small and stable enough to not need scraping.

For teams whose federation predates a split (Czechia <- Czechoslovakia,
DR Congo <- Zaire), the predecessor's record is carried over since it
reflects the same football pedigree/experience.

`best_finish` is an integer code, lower = better:
  1 = Winner, 2 = Runner-up, 3 = Third place, 4 = Fourth place,
  5 = Quarterfinals, 6 = Round of 16, 7 = Group stage, 8 = Never qualified

Writes: backend/data/raw/wc_history.csv with columns
[team_id, world_cup_titles, world_cup_appearances, best_finish]
"""

from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

# (team_id, world_cup_titles, world_cup_appearances, best_finish)
RECORDS = [
    ("MEX", 0, 17, 5),
    ("RSA", 0, 3, 7),
    ("KOR", 0, 11, 4),
    ("CZE", 0, 9, 2),
    ("CAN", 0, 2, 7),
    ("BIH", 0, 1, 7),
    ("QAT", 0, 1, 7),
    ("SUI", 0, 12, 5),
    ("BRA", 5, 22, 1),
    ("MAR", 0, 6, 4),
    ("HAI", 0, 1, 7),
    ("SCO", 0, 8, 7),
    ("USA", 0, 11, 3),
    ("PAR", 0, 8, 5),
    ("AUS", 0, 6, 6),
    ("TUR", 0, 3, 3),
    ("GER", 4, 20, 1),
    ("CUW", 0, 0, 8),
    ("CIV", 0, 3, 7),
    ("ECU", 0, 4, 6),
    ("NED", 0, 11, 2),
    ("JPN", 0, 7, 6),
    ("SWE", 0, 12, 2),
    ("TUN", 0, 6, 7),
    ("BEL", 0, 14, 3),
    ("EGY", 0, 3, 7),
    ("IRN", 0, 6, 7),
    ("NZL", 0, 2, 7),
    ("ESP", 1, 16, 1),
    ("CPV", 0, 0, 8),
    ("KSA", 0, 6, 6),
    ("URU", 2, 14, 1),
    ("FRA", 2, 16, 1),
    ("SEN", 0, 3, 5),
    ("IRQ", 0, 1, 7),
    ("NOR", 0, 3, 6),
    ("ARG", 3, 18, 1),
    ("ALG", 0, 4, 6),
    ("AUT", 0, 8, 3),
    ("JOR", 0, 0, 8),
    ("POR", 0, 8, 3),
    ("COD", 0, 1, 7),
    ("UZB", 0, 0, 8),
    ("COL", 0, 6, 5),
    ("ENG", 1, 16, 1),
    ("CRO", 0, 6, 2),
    ("GHA", 0, 4, 5),
    ("PAN", 0, 1, 7),
]

COLUMNS = ["team_id", "world_cup_titles", "world_cup_appearances", "best_finish"]


def load() -> pd.DataFrame:
    df = pd.DataFrame(RECORDS, columns=COLUMNS)
    assert len(df) == 48
    assert df["team_id"].is_unique
    return df


if __name__ == "__main__":
    df = load()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(RAW_DIR / "wc_history.csv", index=False)
    print(f"Wrote {len(df)} teams to {RAW_DIR / 'wc_history.csv'}")
