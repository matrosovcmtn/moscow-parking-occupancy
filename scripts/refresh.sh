#!/usr/bin/env bash
#
# Weekly dataset refresh: runs on the ParkOut server, exports the latest
# month + the previous month from TimescaleDB, commits any changes, and
# pushes to GitHub. Intended to be invoked by cron.
#
# Required environment (typically from /etc/parkout/dataset.env):
#   DATABASE_URL     PostgreSQL connection URL to parking_db (read-only user OK)
#   REPO_DIR         Absolute path to a local clone of this repository
#   GIT_AUTHOR_NAME  Name to attribute commits to (e.g. "Parkout Dataset Bot")
#   GIT_AUTHOR_EMAIL Email to attribute commits to
#
# Example cron entry (every Monday at 04:00 UTC):
#   0 4 * * 1 /usr/bin/env bash /opt/parkout/dataset/scripts/refresh.sh \
#       >> /var/log/parkout-dataset-refresh.log 2>&1

set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL not set}"
: "${REPO_DIR:?REPO_DIR not set}"
: "${GIT_AUTHOR_NAME:=Parkout Dataset Bot}"
: "${GIT_AUTHOR_EMAIL:=dataset-bot@parkout.ru}"

cd "$REPO_DIR"

echo "[$(date -u +%FT%TZ)] starting refresh in $REPO_DIR"

# Determine the two months we want to (re)export:
# - current month (partial, overwritten each run)
# - previous month (in case backfill or late-arriving data shifts the file)
NOW_YEAR=$(date -u +%Y)
NOW_MONTH=$(date -u +%m)
SINCE=$(date -u -d "${NOW_YEAR}-${NOW_MONTH}-01 -1 month" +%F 2>/dev/null \
        || date -u -v-1m +%Y-%m-01)
# UNTIL = first day of next month, to cleanly include this entire month
UNTIL=$(date -u -d "${NOW_YEAR}-${NOW_MONTH}-01 +1 month" +%F 2>/dev/null \
        || date -u -v+1m +%Y-%m-01)

echo "  exporting range $SINCE → $UNTIL"

python3 scripts/export_from_db.py \
    --db-url "$DATABASE_URL" \
    --output-dir "$REPO_DIR/data" \
    --since "$SINCE" \
    --until "$UNTIL" \
    --skip-spots

# Re-export parking_spots only once per week — they almost never change,
# but a refresh on Mondays keeps us honest about adds/removes.
python3 scripts/export_from_db.py \
    --db-url "$DATABASE_URL" \
    --output-dir "$REPO_DIR/data" \
    --since "$SINCE" \
    --until "$SINCE"   # zero-month range — only spots get written

# Commit and push if anything changed
git add data/

if git diff --cached --quiet; then
    echo "  no data changes to commit"
    exit 0
fi

TS=$(date -u +%F)
GIT_AUTHOR_NAME="$GIT_AUTHOR_NAME" \
GIT_AUTHOR_EMAIL="$GIT_AUTHOR_EMAIL" \
GIT_COMMITTER_NAME="$GIT_AUTHOR_NAME" \
GIT_COMMITTER_EMAIL="$GIT_AUTHOR_EMAIL" \
    git commit -m "data: weekly refresh ${TS}"

git push origin "$(git rev-parse --abbrev-ref HEAD)"

echo "[$(date -u +%FT%TZ)] done"
