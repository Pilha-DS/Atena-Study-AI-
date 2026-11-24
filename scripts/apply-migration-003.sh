#!/usr/bin/env bash
# Aplica a migration 003 (recria schema Course.category + study_topics + exercícios/provas).
# ATENÇÃO: destrutiva nas tabelas de estudo; app_settings permanece.
set -euo pipefail
cd "$(dirname "$0")/.."

echo ">> Aplicando alembic upgrade head no container api..."
docker compose exec -T api alembic upgrade head
docker compose exec -T api alembic current
echo ">> Colunas de courses:"
docker compose exec -T db psql -U "${POSTGRES_USER:-atena}" -d "${POSTGRES_DB:-atena_study}" -c '\d courses'
echo ">> Reiniciando api..."
docker compose restart api
echo "OK. Tente criar o curso com IA de novo."
