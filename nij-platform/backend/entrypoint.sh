#!/bin/sh
set -e

echo "[NIJ] Aguardando PostgreSQL..."
until pg_isready -h db -U "$POSTGRES_USER" -d "$POSTGRES_DB" -q; do
  sleep 2
done
echo "[NIJ] PostgreSQL pronto."

echo "[NIJ] Aplicando migrations..."
python manage.py migrate --noinput

echo "[NIJ] Criando admin inicial..."
python manage.py seed_admin || true

echo "[NIJ] Coletando arquivos estaticos..."
python manage.py collectstatic --noinput --clear

echo "[NIJ] Iniciando servidor..."
exec "$@"
