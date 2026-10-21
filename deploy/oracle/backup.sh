#!/bin/sh
# Backup do Postgres desta VM. Agenda no cron da Oracle, fora do container.
set -eu
cd "$(dirname "$0")"
mkdir -p backups
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
docker compose exec -T db pg_dump -U stories stories | gzip > "backups/stories-${stamp}.sql.gz"
find backups -name 'stories-*.sql.gz' -mtime +14 -delete
