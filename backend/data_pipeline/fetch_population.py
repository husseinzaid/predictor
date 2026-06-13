"""National population per team's country (the 'fun' population factor).

Source: World Bank API, indicator SP.POP.TOTL (total population), most
recent value available (mrnev=1). Free, no key required. All 48 countries
are fetched in a single batched request using their ISO3 codes.

If a country has no data (shouldn't happen for sovereign states), fall
back to the confederation average.

Writes: backend/data/raw/population.csv with columns [team_id, population]
"""

from pathlib import Path

import pandas as pd
import requests

from . import fetch_team_list

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
WORLD_BANK_URL = "https://api.worldbank.org/v2/country/{codes}/indicator/SP.POP.TOTL"


def load() -> pd.DataFrame:
    teams = fetch_team_list.load()[["team_id", "confederation", "iso3"]]

    codes = ";".join(teams["iso3"].tolist())
    resp = requests.get(
        WORLD_BANK_URL.format(codes=codes),
        params={"format": "json", "mrnev": "1", "per_page": "200"},
        timeout=30,
    )
    resp.raise_for_status()
    _meta, entries = resp.json()

    population = pd.DataFrame(
        [{"iso3": e["countryiso3code"], "population": e["value"]} for e in entries if e["value"] is not None]
    )

    merged = teams.merge(population, on="iso3", how="left")

    missing = merged["population"].isna()
    if missing.any():
        conf_avg = merged.groupby("confederation")["population"].transform("mean")
        merged.loc[missing, "population"] = conf_avg[missing]

    return merged[["team_id", "population"]]


if __name__ == "__main__":
    df = load()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(RAW_DIR / "population.csv", index=False)
    print(f"Wrote {len(df)} teams to {RAW_DIR / 'population.csv'}")
    print(df.sort_values("population", ascending=False).head(10))
