FROM node:20-slim AS webapp-css

WORKDIR /build
COPY package.json ./
COPY tailwind.config.js ./
COPY webapp/css/cv.input.css ./webapp/css/
COPY webapp/cv.html ./webapp/
RUN npm install && npm run build:css

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

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
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app
COPY --from=webapp-css /build/webapp/css/cv.css /app/webapp/css/cv.css

RUN mkdir -p /app/data/uploads/receipts /app/data/uploads/generated /app/temp

EXPOSE 8000

CMD ["uvicorn", "api_webhook:app", "--host", "0.0.0.0", "--port", "8000"]
