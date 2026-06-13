"""Heat-adaptation factor: squad club-league climate vs. 2026 World Cup
host-city game temperatures (the 'fun' heat-adaptation factor).

For each team, averages (over the same top-26 EA FC squad selection as
fetch_squad_ratings.py) the June-July average temperature of the country
where each player's club league is based. Players in leagues not covered by
`LEAGUE_TO_ISO3` (continental club competitions like Libertadores/
Sudamericana, smaller domestic leagues, ...) fall back to the player's own
nationality's country -- a reasonable default since most domestic leagues
are played by mostly-domestic squads.

Source for country climate: World Bank Climate Change Knowledge Portal
(CCKP), CMIP6 1995-2014 historical climatology, monthly mean near-surface
air temperature ("tas"). Free, no key. June + July values are averaged into
a single "summer" figure per country.
https://cckpapi.worldbank.org/cckp/v1/cmip6-x0.25_climatology_tas_climatology_monthly_1995-2014_median_historical_ensemble_all_mean/{ISO3,...}

Host-city game temperatures (`HOST_VENUE_JUNE_JULY_C`) are hand-curated
June/July averages for the 16 2026 World Cup venues, based on reporting
about World Cup 2026 heat (Vancouver/Mexico City ~18C at the cool end,
Monterrey/Miami/Houston/Dallas ~29-30C at the hot end). `WC_AVG_GAME_TEMP_C`
is the simple average across all 16 venues.

`heat_disadvantage_c = max(0, WC_AVG_GAME_TEMP_C - squad_climate_c)` -- only
penalizes squads used to *cooler* conditions than the tournament; squads
already used to similar-or-hotter conditions score 0 (no disadvantage).

Writes: backend/data/raw/climate.csv with columns
[team_id, squad_climate_c, heat_disadvantage_c]
"""

from pathlib import Path

import pandas as pd
import requests

from . import fetch_team_list
from .fetch_squad_ratings import NATIONALITY_MAP, SQUAD_SIZE, _download_players

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

CCKP_URL = (
    "https://cckpapi.worldbank.org/cckp/v1/"
    "cmip6-x0.25_climatology_tas_climatology_monthly_1995-2014_median_historical_ensemble_all_mean/"
    "{codes}"
)

# EA FC `leagueName` -> ISO3 of the country that league is played in, for
# climate lookups. Broader than fetch_squad_ratings.LEAGUE_TO_COUNTRY (which
# is restricted to clubelo-tracked leagues for the league_strength factor).
LEAGUE_TO_ISO3 = {
    "Premier League": "GBR", "EFL Championship": "GBR", "EFL League One": "GBR", "EFL League Two": "GBR",
    "LALIGA EA SPORTS": "ESP", "LALIGA HYPERMOTION": "ESP",
    "Bundesliga": "DEU", "Bundesliga 2": "DEU", "3. Liga": "DEU",
    "Serie A Enilive": "ITA", "Serie BKT": "ITA",
    "Ligue 1 McDonald's": "FRA", "Ligue 2 BKT": "FRA",
    "Liga Portugal": "PRT",
    "1A Pro League": "BEL",
    "3F Superliga": "DNK",
    "Eredivisie": "NLD",
    "Eliteserien": "NOR",
    "Trendyol Süper Lig": "TUR",
    "PKO BP Ekstraklasa": "POL",
    "Allsvenskan": "SWE",
    "Scottish Prem": "GBR",
    "Ö. Bundesliga": "AUT",
    "Brack Super League": "CHE",
    "Liga Hrvatska": "HRV",
    "Ukrayina Liha": "UKR",
    "Magyar Liga": "HUN",
    "Česká Liga": "CZE",
    "Hellas Liga": "GRC",
    "SUPERLIGA": "ROU",
    "LPF": "ARG",
    "MLS": "USA",
    "CSL": "CHN",
    "K League 1": "KOR",
    "ROSHN Saudi League": "SAU",
    "A-League": "AUS",
    "ISL": "IND",
    "SSE Airtricity PD": "IRL",
}

# Hand-curated June/July average temperatures (Celsius) for the 16 2026
# World Cup host-city venues.
HOST_VENUE_JUNE_JULY_C = {
    "Atlanta": 26,
    "Boston/Foxborough": 21,
    "Dallas/Arlington": 29,
    "Houston": 29,
    "Kansas City": 25,
    "Los Angeles/Inglewood": 21,
    "Miami Gardens": 29,
    "New York/East Rutherford": 24,
    "Philadelphia": 25,
    "San Francisco Bay/Santa Clara": 18,
    "Seattle": 21,
    "Toronto": 22,
    "Vancouver": 18,
    "Mexico City": 18,
    "Guadalajara": 22,
    "Monterrey": 30,
}

WC_AVG_GAME_TEMP_C = sum(HOST_VENUE_JUNE_JULY_C.values()) / len(HOST_VENUE_JUNE_JULY_C)


def load() -> pd.DataFrame:
    teams = fetch_team_list.load()[["team_id", "confederation", "iso3"]]
    players = _download_players()

    codes = sorted(set(teams["iso3"]) | set(LEAGUE_TO_ISO3.values()))
    resp = requests.get(CCKP_URL.format(codes=",".join(codes)), params={"_format": "json"}, timeout=30)
    resp.raise_for_status()
    climate = resp.json()["data"]

    def summer_temp(iso3: str):
        country = climate.get(iso3)
        if country is None:
            return None
        return (country["1995-06"] + country["1995-07"]) / 2

    iso3_by_team = dict(zip(teams["team_id"], teams["iso3"]))

    rows = []
    for team_id, nationality in NATIONALITY_MAP.items():
        team_iso3 = iso3_by_team[team_id]
        if nationality is None:
            rows.append({"team_id": team_id, "squad_climate_c": None})
            continue

        squad = players[players["nationality"] == nationality].nlargest(SQUAD_SIZE, "overallRating")
        temps = []
        for league in squad["leagueName"]:
            league_iso3 = LEAGUE_TO_ISO3.get(league, team_iso3)
            temp = summer_temp(league_iso3)
            if temp is not None:
                temps.append(temp)

        squad_climate_c = sum(temps) / len(temps) if temps else summer_temp(team_iso3)
        rows.append({"team_id": team_id, "squad_climate_c": squad_climate_c})

    df = pd.DataFrame(rows).merge(teams[["team_id", "confederation"]], on="team_id", how="left")

    missing = df["squad_climate_c"].isna()
    if missing.any():
        conf_avg = df.groupby("confederation")["squad_climate_c"].transform("mean")
        df.loc[missing, "squad_climate_c"] = conf_avg[missing]

    df["heat_disadvantage_c"] = (WC_AVG_GAME_TEMP_C - df["squad_climate_c"]).clip(lower=0)

    return df[["team_id", "squad_climate_c", "heat_disadvantage_c"]]


if __name__ == "__main__":
    df = load()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(RAW_DIR / "climate.csv", index=False)
    print(f"Wrote {len(df)} teams to {RAW_DIR / 'climate.csv'}")
    print(f"WC_AVG_GAME_TEMP_C = {WC_AVG_GAME_TEMP_C:.2f}")
    print(df.sort_values("heat_disadvantage_c").head(5))
    print(df.sort_values("heat_disadvantage_c").tail(5))
