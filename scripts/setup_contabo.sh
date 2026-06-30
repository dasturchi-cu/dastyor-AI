#!/bin/bash
# ═══════════════════════════════════════════════════════════════
#  DASTYOR AI — Contabo VPS Full Setup Script
#  Ubuntu 24.04 | dastyorai.duckdns.org | 84.46.243.149
#  Ishlatish: bash setup_contabo.sh
# ═══════════════════════════════════════════════════════════════
set -e

# ── SOZLAMALAR ──────────────────────────────────────────────────
DOMAIN="dastyorai.duckdns.org"
DUCKDNS_TOKEN="b94913b6-6b45-44e6-839e-fccaa0d37807"
CONTABO_IP="84.46.243.149"
APP_DIR="/opt/dastyor-ai"
DATA_DIR="/opt/dastyor-ai/data"
GITHUB_REPO="https://github.com/dasturchi-cu/dastyor-AI.git"
CERTBOT_EMAIL="dasturchi742@gmail.com"
CONTAINER_NAME="dastyor-ai"
APP_PORT="8000"

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║     DASTYOR AI — Contabo Setup Boshlandi     ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# ── 1. DuckDNS IP YANGILASH ─────────────────────────────────────
echo "► [1/10] DuckDNS IP yangilanmoqda: $CONTABO_IP → $DOMAIN"
RESULT=$(curl -s "https://www.duckdns.org/update?domains=dastyorai&token=${DUCKDNS_TOKEN}&ip=${CONTABO_IP}")
if [ "$RESULT" = "OK" ]; then
    echo "  ✅ DuckDNS muvaffaqiyatli yangilandi"
else
    echo "  ⚠️  DuckDNS javob: $RESULT (davom etilmoqda)"
fi
sleep 3

# ── 2. TIZIM YANGILASH ──────────────────────────────────────────
echo ""
echo "► [2/10] Tizim yangilanmoqda..."
apt-get update -y -q
apt-get upgrade -y -q
apt-get install -y -q git curl wget nano ufw nginx certbot python3-certbot-nginx

# ── 3. FIREWALL ─────────────────────────────────────────────────
echo ""
echo "► [3/10] Firewall sozlanmoqda..."
ufw --force enable
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
echo "  ✅ UFW: 22, 80, 443 ochildi"

# ── 4. DOCKER O'RNATISH ─────────────────────────────────────────
echo ""
echo "► [4/10] Docker o'rnatilmoqda..."
if command -v docker &> /dev/null; then
    echo "  ✅ Docker allaqachon o'rnatilgan: $(docker --version)"
else
    curl -fsSL https://get.docker.com | sh -s -- -y
    systemctl enable docker
    systemctl start docker
    echo "  ✅ Docker o'rnatildi: $(docker --version)"
fi

# ── 5. PAPKALAR YARATISH ────────────────────────────────────────
echo ""
echo "► [5/10] Papkalar yaratilmoqda..."
mkdir -p "$DATA_DIR/uploads/receipts"
mkdir -p "$DATA_DIR/uploads/generated"
mkdir -p "$DATA_DIR/tmp"
chmod -R 755 "$DATA_DIR"
echo "  ✅ $DATA_DIR papkalari yaratildi"

# ── 6. REPO CLONE/PULL ──────────────────────────────────────────
echo ""
echo "► [6/10] Kod yuklanmoqda..."
if [ -d "$APP_DIR/.git" ]; then
    echo "  → Mavjud repo yangilanmoqda..."
    cd "$APP_DIR" && git pull origin main
else
    echo "  → GitHub'dan clone qilinmoqda..."
    git clone "$GITHUB_REPO" "$APP_DIR"
fi
echo "  ✅ Kod tayyor: $APP_DIR"

# ── 7. .ENV TEKSHIRISH ──────────────────────────────────────────
echo ""
echo "► [7/10] .env fayli tekshirilmoqda..."
if [ ! -f "$APP_DIR/.env" ]; then
    echo ""
    echo "  ❌ XATO: $APP_DIR/.env fayli topilmadi!"
    echo ""
    echo "  Quyidagi buyruqni ishlatib .env ni ko'chiring:"
    echo "  scp .env root@${CONTABO_IP}:${APP_DIR}/.env"
    echo ""
    echo "  Keyin skriptni qayta ishga tushiring:"
    echo "  bash $APP_DIR/scripts/setup_contabo.sh"
    exit 1
fi
echo "  ✅ .env fayli topildi"

# ── 8. DOCKER IMAGE BUILD ───────────────────────────────────────
echo ""
echo "► [8/10] Docker image build qilinmoqda (5-15 daqiqa)..."
cd "$APP_DIR"
docker build -t "$CONTAINER_NAME" . 2>&1 | tail -5
echo "  ✅ Docker image tayyor"

# Eski containerni to'xtatish
docker stop "$CONTAINER_NAME" 2>/dev/null || true
docker rm "$CONTAINER_NAME" 2>/dev/null || true

# Containerni ishga tushirish
docker run -d \
    --name "$CONTAINER_NAME" \
    --restart unless-stopped \
    -p "${APP_PORT}:${APP_PORT}" \
    -v "${DATA_DIR}:/data" \
    --env-file "${APP_DIR}/.env" \
    "$CONTAINER_NAME"

echo "  ✅ Container ishga tushdi"
sleep 5

# ── 9. NGINX SOZLASH ────────────────────────────────────────────
echo ""
echo "► [9/10] Nginx sozlanmoqda..."

cat > /etc/nginx/sites-available/dastyor-ai << EOF
server {
    listen 80;
    server_name ${DOMAIN};

    # Health check va UptimeRobot uchun
    location /ping {
        proxy_pass http://127.0.0.1:${APP_PORT}/ping;
        proxy_set_header Host \$host;
        access_log off;
    }

    location / {
        proxy_pass http://127.0.0.1:${APP_PORT};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection keep-alive;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
        client_max_body_size 20M;
    }
}
EOF

ln -sf /etc/nginx/sites-available/dastyor-ai /etc/nginx/sites-enabled/dastyor-ai
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
echo "  ✅ Nginx sozlandi"

# SSL SERTIFIKAT
echo ""
echo "  → SSL sertifikat olinmoqda..."
certbot --nginx -d "$DOMAIN" \
    --non-interactive \
    --agree-tos \
    --email "$CERTBOT_EMAIL" \
    --redirect 2>&1 | tail -5

# Certbot auto-renew
systemctl enable certbot.timer 2>/dev/null || true
echo "  ✅ SSL sertifikat o'rnatildi (auto-renew yoqildi)"

# ── 10. SYSTEMD SERVICE (docker auto-restart) ───────────────────
echo ""
echo "► [10/10] Auto-restart sozlanmoqda..."

cat > /etc/systemd/system/dastyor-ai.service << EOF
[Unit]
Description=Dastyor AI Bot
Requires=docker.service
After=docker.service network-online.target

[Service]
Restart=always
RestartSec=10
ExecStart=/usr/bin/docker start -a ${CONTAINER_NAME}
ExecStop=/usr/bin/docker stop ${CONTAINER_NAME}

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable dastyor-ai
echo "  ✅ Systemd service yoqildi"

# ── NATIJA ──────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║                  ✅ SETUP TUGADI!                        ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  🌐 URL:     https://${DOMAIN}          ║"
echo "║  🏥 Health:  https://${DOMAIN}/health   ║"
echo "║  🏓 Ping:    https://${DOMAIN}/ping     ║"
echo "║  📁 Data:    ${DATA_DIR}                   ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "  Bot loglari ko'rish:"
echo "  docker logs -f ${CONTAINER_NAME}"
echo ""
echo "  Bot holati:"
echo "  docker ps"
echo ""
