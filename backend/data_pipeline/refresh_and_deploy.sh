#!/bin/bash
# Refresh the live tournament factors (elo, fifa_rank, betting_odds) and, if
# anything changed, commit + push so Render redeploys with fresh data.
#
# Intended to run on a schedule (see crontab):
#   17 0,6,12,18 * * * /home/ubuntu/predictor/backend/data_pipeline/refresh_and_deploy.sh >> /home/ubuntu/predictor/backend/data_pipeline/refresh.log 2>&1
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
REPO_DIR="$(dirname "$BACKEND_DIR")"

echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) refresh_and_deploy starting ==="

cd "$BACKEND_DIR"
source .venv/bin/activate
python3 -m data_pipeline.refresh_live_factors

cd "$REPO_DIR"
if ! git diff --quiet -- backend/data/teams.json; then
    git add backend/data/teams.json
    git commit -m "Refresh live factors (elo, fifa_rank, betting_odds) - $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    git push origin master
    echo "Pushed updated teams.json."
else
    echo "No changes to teams.json, skipping commit/push."
fi
