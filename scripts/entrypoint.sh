#!/bin/sh
set -e

PORT="${PORT:-8000}"
export PORT

python -c "from config.paths import ensure_data_dirs; ensure_data_dirs()"
python -c "from config.validate import validate_or_exit; validate_or_exit()"

exec uvicorn api_webhook:app --host 0.0.0.0 --port "$PORT"

