#!/usr/bin/env bash
# Cron (root), every 2 minutes: deploy when origin/main has a new commit.
#   */2 * * * * bash /opt/dastyor-ai/deploy/contabo/auto-deploy.sh
# A commit whose image fails to build never goes live — the running one stays.
set -uo pipefail
cd "$(dirname "$0")/../.."
LOG=/var/log/dastyor-auto-deploy.log

exec 9>/tmp/dastyor-auto-deploy.lock
flock -n 9 || exit 0

git fetch --quiet origin main || exit 0
[ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ] && exit 0

{
  echo "== $(date '+%F %T') $(git rev-parse --short HEAD) -> $(git rev-parse --short origin/main)"
  if bash deploy/contabo/deploy.sh; then
    echo "OK"
  else
    echo "FAILED — the previous version keeps running"
  fi
} >>"$LOG" 2>&1
tail -n 400 "$LOG" >"$LOG.tmp" && mv "$LOG.tmp" "$LOG"
