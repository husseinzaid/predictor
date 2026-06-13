"""Total GDP per team's country (the 'fun' economic-power factor).

Source: World Bank API, indicator NY.GDP.MKTP.CD (GDP, current US$), most
recent value available (mrnev=1). Free, no key required. All 48 countries
are fetched in a single batched request using their ISO3 codes.

Note: this is *total* GDP, not GDP per capita -- per-capita wealth doesn't
correlate with population size, but total GDP does (roughly), which is what
makes it an interesting companion to the `population` factor.

If a country has no data (shouldn't happen for sovereign states, but
covers edge cases), fall back to the confederation average.

Writes: backend/data/raw/gdp.csv with columns [team_id, gdp_total_usd]
"""

from pathlib import Path

import pandas as pd
import requests

from . import fetch_team_list

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
WORLD_BANK_URL = "https://api.worldbank.org/v2/country/{codes}/indicator/NY.GDP.MKTP.CD"


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

    gdp = pd.DataFrame(
        [{"iso3": e["countryiso3code"], "gdp_total_usd": e["value"]} for e in entries if e["value"] is not None]
    )

    merged = teams.merge(gdp, on="iso3", how="left")

    missing = merged["gdp_total_usd"].isna()
    if missing.any():
        conf_avg = merged.groupby("confederation")["gdp_total_usd"].transform("mean")
        merged.loc[missing, "gdp_total_usd"] = conf_avg[missing]

    return merged[["team_id", "gdp_total_usd"]]


if __name__ == "__main__":
    df = load()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(RAW_DIR / "gdp.csv", index=False)
    print(f"Wrote {len(df)} teams to {RAW_DIR / 'gdp.csv'}")
    print(df.sort_values("gdp_total_usd", ascending=False).head(10))
