FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PADDLEX_HOME=/app/.paddlex

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
      libglib2.0-0 \
      libnss3 \
      libatk1.0-0 \
      libatk-bridge2.0-0 \
      libcups2 \
      libdrm2 \
      libxkbcommon0 \
      libxcomposite1 \
      libxdamage1 \
      libxfixes3 \
      libxrandr2 \
      libgbm1 \
      libasound2 \
      libpangocairo-1.0-0 \
      libpango-1.0-0 \
      libcairo2 \
      libxshmfence1 \
      libxrender1 \
      ca-certificates \
      ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# CV/Obyektivka PDF: Playwright Chromium build vaqtida (so'rovda "playwright install" 8–15s bermasligi uchun)
RUN playwright install chromium

COPY . /app

# Ensure PaddleX model cache directory exists inside image
RUN mkdir -p /app/.paddlex

# OCR: warm up PaddleOCR models at build time to avoid first-request downloads/timeouts.
# This makes OCR_PADDLE_TABLE_GRID usable within <5s at runtime.
RUN python /app/scripts/warmup_paddle.py || true

# Default command is overridden in docker-compose.yml
CMD ["python", "-c", "print('Use docker-compose services')"]

