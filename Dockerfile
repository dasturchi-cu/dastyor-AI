FROM node:20-slim AS webapp-css

WORKDIR /build
COPY package.json ./
COPY tailwind.config.js ./
COPY webapp/css/cv.input.css ./webapp/css/
COPY webapp/cv.html ./webapp/
RUN npm install && npm run build:css

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    DATA_DIR=/data \
    ENABLE_DEMO_PDF_API=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
      libpangocairo-1.0-0 \
      libpango-1.0-0 \
      libcairo2 \
      libgdk-pixbuf-2.0-0 \
      libffi-dev \
      shared-mime-info \
      ffmpeg \
      ca-certificates \
      libreoffice-writer \
      libreoffice-java-common \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt /app/requirements.txt
ARG PIP_CACHE_BUST=1
RUN pip install --no-cache-dir -r /app/requirements.txt \
    && python -m playwright install --with-deps chromium

COPY . /app
COPY --from=webapp-css /build/webapp/css/cv.css /app/webapp/css/cv.css

RUN mkdir -p /data/uploads/receipts /data/uploads/generated /data/tmp \
    && chmod +x /app/scripts/entrypoint.sh

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8000')+'/ping', timeout=3)"

CMD ["/app/scripts/entrypoint.sh"]
