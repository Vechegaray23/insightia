#!/bin/sh
set -e

envsubst < /etc/promtail.yml > /tmp/promtail.yml
promtail -config.file=/tmp/promtail.yml &
exec uvicorn backend.app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1