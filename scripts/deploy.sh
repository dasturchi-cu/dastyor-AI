#!/bin/bash
# ═══════════════════════════════════════════════════════════════
#  DASTYOR AI — Update & Restart Script
#  Yangi kod chiqsa: bash /opt/dastyor-ai/scripts/deploy.sh
# ═══════════════════════════════════════════════════════════════
set -e

APP_DIR="/opt/dastyor-ai"
DATA_DIR="/opt/dastyor-ai/data"
CONTAINER_NAME="dastyor-ai"
APP_PORT="8000"

echo "► Yangi kod yuklanmoqda..."
cd "$APP_DIR"
git pull origin main

echo "► Yangi Docker image build..."
docker build -t "$CONTAINER_NAME" . 2>&1 | tail -3

echo "► Eski container to'xtatilmoqda..."
docker stop "$CONTAINER_NAME" 2>/dev/null || true
docker rm "$CONTAINER_NAME" 2>/dev/null || true

echo "► Yangi container ishga tushirilmoqda..."
docker run -d \
    --name "$CONTAINER_NAME" \
    --restart unless-stopped \
    -p "${APP_PORT}:${APP_PORT}" \
    -v "${DATA_DIR}:/data" \
    --env-file "${APP_DIR}/.env" \
    "$CONTAINER_NAME"

sleep 5
echo "✅ Deploy tugadi!"
docker ps | grep "$CONTAINER_NAME"
