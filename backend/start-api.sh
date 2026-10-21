#!/usr/bin/env sh
# Start da API no Render: roda as migracoes e sobe o uvicorn.
# Usa "python -m" para nao depender de scripts no PATH.
set -e
python -m alembic upgrade head
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
