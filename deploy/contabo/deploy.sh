#!/usr/bin/env bash
# Pull main and rebuild DASTYOR AI. Run by auto-deploy.sh or by hand.
set -euo pipefail
cd "$(dirname "$0")/../.."
git fetch --quiet origin main
git reset --hard --quiet origin/main
cd deploy/contabo
docker compose --env-file .env up -d --build
docker image prune -f >/dev/null
echo "deployed $(git rev-parse --short HEAD)"
