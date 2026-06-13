"""Base roster for the 2026 World Cup: 48 teams, 12 groups of 4, confederations.

Hand-curated from the official December 2025 draw (groups A-L). Static —
only needs updating if the draw/groups change.

Columns: team_id (FIFA 3-letter code, used as the canonical join key
throughout the pipeline), name, confederation, group, iso2 (for flag emoji
and eloratings.net lookups), iso3 (World Bank country code), elo_code
(eloratings.net's 2-letter team code, which sometimes differs from iso2,
e.g. England=EN, Scotland=SQ).

Writes: backend/data/raw/team_list.csv
"""

from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

# (team_id, name, confederation, group, iso2, iso3, elo_code)
TEAMS = [
    ("MEX", "Mexico", "CONCACAF", "A", "MX", "MEX", "MX"),
    ("RSA", "South Africa", "CAF", "A", "ZA", "ZAF", "ZA"),
    ("KOR", "South Korea", "AFC", "A", "KR", "KOR", "KR"),
    ("CZE", "Czechia", "UEFA", "A", "CZ", "CZE", "CZ"),
    ("CAN", "Canada", "CONCACAF", "B", "CA", "CAN", "CA"),
    ("BIH", "Bosnia and Herzegovina", "UEFA", "B", "BA", "BIH", "BA"),
    ("QAT", "Qatar", "AFC", "B", "QA", "QAT", "QA"),
    ("SUI", "Switzerland", "UEFA", "B", "CH", "CHE", "CH"),
    ("BRA", "Brazil", "CONMEBOL", "C", "BR", "BRA", "BR"),
    ("MAR", "Morocco", "CAF", "C", "MA", "MAR", "MA"),
    ("HAI", "Haiti", "CONCACAF", "C", "HT", "HTI", "HT"),
    ("SCO", "Scotland", "UEFA", "C", "GB-SCT", "GBR", "SQ"),
    ("USA", "United States", "CONCACAF", "D", "US", "USA", "US"),
    ("PAR", "Paraguay", "CONMEBOL", "D", "PY", "PRY", "PY"),
    ("AUS", "Australia", "AFC", "D", "AU", "AUS", "AU"),
    ("TUR", "Türkiye", "UEFA", "D", "TR", "TUR", "TR"),
    ("GER", "Germany", "UEFA", "E", "DE", "DEU", "DE"),
    ("CUW", "Curaçao", "CONCACAF", "E", "CW", "CUW", "CW"),
    ("CIV", "Côte d'Ivoire", "CAF", "E", "CI", "CIV", "CI"),
    ("ECU", "Ecuador", "CONMEBOL", "E", "EC", "ECU", "EC"),
    ("NED", "Netherlands", "UEFA", "F", "NL", "NLD", "NL"),
    ("JPN", "Japan", "AFC", "F", "JP", "JPN", "JP"),
    ("SWE", "Sweden", "UEFA", "F", "SE", "SWE", "SE"),
    ("TUN", "Tunisia", "CAF", "F", "TN", "TUN", "TN"),
    ("BEL", "Belgium", "UEFA", "G", "BE", "BEL", "BE"),
    ("EGY", "Egypt", "CAF", "G", "EG", "EGY", "EG"),
    ("IRN", "IR Iran", "AFC", "G", "IR", "IRN", "IR"),
    ("NZL", "New Zealand", "OFC", "G", "NZ", "NZL", "NZ"),
    ("ESP", "Spain", "UEFA", "H", "ES", "ESP", "ES"),
    ("CPV", "Cabo Verde", "CAF", "H", "CV", "CPV", "CV"),
    ("KSA", "Saudi Arabia", "AFC", "H", "SA", "SAU", "SA"),
    ("URU", "Uruguay", "CONMEBOL", "H", "UY", "URY", "UY"),
    ("FRA", "France", "UEFA", "I", "FR", "FRA", "FR"),
    ("SEN", "Senegal", "CAF", "I", "SN", "SEN", "SN"),
    ("IRQ", "Iraq", "AFC", "I", "IQ", "IRQ", "IQ"),
    ("NOR", "Norway", "UEFA", "I", "NO", "NOR", "NO"),
    ("ARG", "Argentina", "CONMEBOL", "J", "AR", "ARG", "AR"),
    ("ALG", "Algeria", "CAF", "J", "DZ", "DZA", "DZ"),
    ("AUT", "Austria", "UEFA", "J", "AT", "AUT", "AT"),
    ("JOR", "Jordan", "AFC", "J", "JO", "JOR", "JO"),
    ("POR", "Portugal", "UEFA", "K", "PT", "PRT", "PT"),
    ("COD", "DR Congo", "CAF", "K", "CD", "COD", "CD"),
    ("UZB", "Uzbekistan", "AFC", "K", "UZ", "UZB", "UZ"),
    ("COL", "Colombia", "CONMEBOL", "K", "CO", "COL", "CO"),
    ("ENG", "England", "UEFA", "L", "GB-ENG", "GBR", "EN"),
    ("CRO", "Croatia", "UEFA", "L", "HR", "HRV", "HR"),
    ("GHA", "Ghana", "CAF", "L", "GH", "GHA", "GH"),
    ("PAN", "Panama", "CONCACAF", "L", "PA", "PAN", "PA"),
]

COLUMNS = ["team_id", "name", "confederation", "group", "iso2", "iso3", "elo_code"]

# Unicode tag-sequence flags for the UK's home nations (no standard ISO2 flag).
SPECIAL_FLAGS = {
    "GB-ENG": "\U0001F3F4\U000E0067\U000E0062\U000E0065\U000E006E\U000E0067\U000E007F",
    "GB-SCT": "\U0001F3F4\U000E0067\U000E0062\U000E0073\U000E0063\U000E0074\U000E007F",
}


def flag_emoji(iso2: str) -> str:
    if iso2 in SPECIAL_FLAGS:
        return SPECIAL_FLAGS[iso2]
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in iso2.upper())


def load() -> pd.DataFrame:
    df = pd.DataFrame(TEAMS, columns=COLUMNS)
    df["flag"] = df["iso2"].map(flag_emoji)
    assert len(df) == 48
    assert df["team_id"].is_unique
    return df


if __name__ == "__main__":
    df = load()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(RAW_DIR / "team_list.csv", index=False)
    print(f"Wrote {len(df)} teams to {RAW_DIR / 'team_list.csv'}")
