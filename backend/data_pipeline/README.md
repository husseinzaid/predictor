# Data Pipeline

One-off / periodically-rerun scripts that build `backend/data/teams.json`
(the 48-team 2026 World Cup dataset) and `backend/data/factors.json`. These
are **not** called by the live API — they're run manually (or via a future
cron) to refresh the dataset, producing the same JSON shape the mock data
already uses (see `API_CONTRACT.md`).

## Scripts

| Script | Factor(s) | Source | Status |
|---|---|---|---|
| `fetch_team_list.py` | base 48-team roster, groups, confederations | static, hand-curated from official 2026 draw | done |
| `fetch_elo.py` | `elo` | [eloratings.net](https://eloratings.net/) — scrape the public ratings table | done |
| `fetch_fifa_ranking.py` | `fifa_rank` | Wikipedia "Top 20" table (~19/48 teams); rest estimated from Elo via linear fit (see `build_team_table.py`) | done |
| `fetch_wc_history.py` | `tournament_experience` | static curated table (titles/appearances/best finish) | done |
| `fetch_gdp.py` | `gdp` | World Bank API (`NY.GDP.PCAP.CD`, all 48 in one batched request) | done |
| `fetch_clubelo.py` | (league strength input) | [api.clubelo.com](http://api.clubelo.com) CSV API — per-country top-division Elo average | done |
| `fetch_squad_ratings.py` | `squad_quality`, `league_strength` | Kaggle dataset `justdhia/ea-sports-fc-26-player-ratings`, top-26 players per nationality; leagues joined with `fetch_clubelo` averages | done (requires `~/.kaggle/kaggle.json`) |
| `fetch_odds.py` | `betting_odds` | the-odds-api.com `soccer_fifa_world_cup_winner` outrights market | done (requires `ODDS_API_KEY` in `backend/.env`) |
| `build_team_table.py` | — | joins all of the above on FIFA country code, min-max normalizes each factor to 0-1, writes `backend/data/teams.json` | done — all 8 factors are now real data |

## Conventions

- Each `fetch_*.py` writes a raw snapshot to `backend/data/raw/<name>.csv`
  and exposes a `load() -> pd.DataFrame` function keyed by a 3-letter FIFA
  country code column named `team_id`.
- `build_team_table.py` is the only script that writes
  `backend/data/teams.json` (and `factors.json`). It merges all `fetch_*`
  outputs on `team_id`, applies min-max normalization per factor across the
  48 teams, and fills the `factors` / `raw` structure from API_CONTRACT.md.
- If a source is unavailable for a given team, fall back to the
  confederation average rather than dropping the team.
