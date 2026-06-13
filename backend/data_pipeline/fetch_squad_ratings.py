"""Squad quality and league-strength factors from EA Sports FC 26 ratings.

Source: Kaggle dataset justdhia/ea-sports-fc-26-player-ratings
(ea_fc26_players.csv), downloaded via the Kaggle API (requires
~/.kaggle/kaggle.json).

For each of the 48 teams, the top `SQUAD_SIZE` rated players by
`nationality` approximate a World Cup squad:
  - squad_avg_rating = mean overallRating of those players (EA FC 0-99
    scale).
  - league_strength_rating = mean clubelo top-division Elo (see
    fetch_clubelo) of the leagues those players' clubs compete in, for the
    subset of players whose league maps to a clubelo country (mostly
    Europe). Teams with no mappable players (or no players at all, e.g.
    Qatar, which has no EA FC players of that nationality) fall back to
    their confederation average.

Writes: backend/data/raw/squad_ratings.csv with columns
[team_id, squad_avg_rating, league_strength_rating]
"""

import zipfile
from pathlib import Path

import pandas as pd

from . import fetch_clubelo, fetch_team_list

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
SQUAD_SIZE = 26

DATASET = "justdhia/ea-sports-fc-26-player-ratings"
DATASET_FILE = "ea_fc26_players.csv"

# EA FC `nationality` for each team_id. QAT has no players of Qatari
# nationality in this dataset, so it falls back to the AFC average.
NATIONALITY_MAP = {
    "MEX": "Mexico", "RSA": "South Africa", "KOR": "Korea Republic", "CZE": "Czech Republic",
    "CAN": "Canada", "BIH": "Bosnia and Herzegovina", "QAT": None, "SUI": "Switzerland",
    "BRA": "Brazil", "MAR": "Morocco", "HAI": "Haiti", "SCO": "Scotland",
    "USA": "United States", "PAR": "Paraguay", "AUS": "Australia", "TUR": "Turkey",
    "GER": "Germany", "CUW": "Curaçao", "CIV": "Côte d'Ivoire", "ECU": "Ecuador",
    "NED": "Holland", "JPN": "Japan", "SWE": "Sweden", "TUN": "Tunisia",
    "BEL": "Belgium", "EGY": "Egypt", "IRN": "Iran", "NZL": "New Zealand",
    "ESP": "Spain", "CPV": "Cape Verde Islands", "KSA": "Saudi Arabia", "URU": "Uruguay",
    "FRA": "France", "SEN": "Senegal", "IRQ": "Iraq", "NOR": "Norway",
    "ARG": "Argentina", "ALG": "Algeria", "AUT": "Austria", "JOR": "Jordan",
    "POR": "Portugal", "COD": "Congo DR", "UZB": "Uzbekistan", "COL": "Colombia",
    "ENG": "England", "CRO": "Croatia", "GHA": "Ghana", "PAN": "Panama",
}

# EA FC `leagueName` -> clubelo `country` code, for the leagues clubelo
# tracks (mostly European top divisions). Leagues outside this map (MLS,
# Liga MX/LPF, Brazilian leagues, Saudi league, K League, CSL, A-League,
# ...) are left unmapped and simply excluded from the league-strength
# average for that player.
LEAGUE_TO_COUNTRY = {
    "Premier League": "ENG", "EFL Championship": "ENG", "EFL League One": "ENG", "EFL League Two": "ENG",
    "LALIGA EA SPORTS": "ESP", "LALIGA HYPERMOTION": "ESP",
    "Bundesliga": "GER", "Bundesliga 2": "GER", "3. Liga": "GER",
    "Serie A Enilive": "ITA", "Serie BKT": "ITA",
    "Ligue 1 McDonald's": "FRA", "Ligue 2 BKT": "FRA",
    "Liga Portugal": "POR",
    "1A Pro League": "BEL",
    "3F Superliga": "DEN",
    "Eredivisie": "NED",
    "Eliteserien": "NOR",
    "Trendyol Süper Lig": "TUR",
    "PKO BP Ekstraklasa": "POL",
    "Allsvenskan": "SWE",
    "Scottish Prem": "SCO",
    "Ö. Bundesliga": "AUT",
    "Brack Super League": "SUI",
    "Liga Hrvatska": "CRO",
    "Ukrayina Liha": "UKR",
    "Magyar Liga": "HUN",
    "Česká Liga": "CZE",
    "Hellas Liga": "GRE",
    "SUPERLIGA": "ROM",
}


def _download_players() -> pd.DataFrame:
    csv_path = RAW_DIR / DATASET_FILE
    if not csv_path.exists():
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        import kaggle

        kaggle.api.authenticate()
        kaggle.api.dataset_download_file(DATASET, DATASET_FILE, path=str(RAW_DIR), force=False)

        zip_path = RAW_DIR / f"{DATASET_FILE}.zip"
        if zip_path.exists():
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(RAW_DIR)
            zip_path.unlink()

    return pd.read_csv(csv_path)


def load() -> pd.DataFrame:
    teams = fetch_team_list.load()[["team_id", "confederation"]]
    players = _download_players()
    league_elo = fetch_clubelo.load().set_index("country")["league_strength_elo"]

    players = players.copy()
    players["league_elo"] = players["leagueName"].map(LEAGUE_TO_COUNTRY).map(league_elo)

    rows = []
    for team_id, nationality in NATIONALITY_MAP.items():
        if nationality is None:
            rows.append({"team_id": team_id, "squad_avg_rating": None, "league_strength_rating": None})
            continue
        squad = players[players["nationality"] == nationality].nlargest(SQUAD_SIZE, "overallRating")
        rows.append({
            "team_id": team_id,
            "squad_avg_rating": squad["overallRating"].mean(),
            "league_strength_rating": squad["league_elo"].mean(),
        })

    df = pd.DataFrame(rows).merge(teams, on="team_id", how="left")

    for col in ["squad_avg_rating", "league_strength_rating"]:
        missing = df[col].isna()
        if missing.any():
            conf_avg = df.groupby("confederation")[col].transform("mean")
            df.loc[missing, col] = conf_avg[missing]

    return df[["team_id", "squad_avg_rating", "league_strength_rating"]]


if __name__ == "__main__":
    df = load()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(RAW_DIR / "squad_ratings.csv", index=False)
    print(f"Wrote {len(df)} teams to {RAW_DIR / 'squad_ratings.csv'}")
    print(df.sort_values("squad_avg_rating", ascending=False).head(10))
    print(df.sort_values("league_strength_rating", ascending=False).head(10))
