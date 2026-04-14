#!/bin/sh
set -e

if [ -n "$DATABASE_URL" ]; then
  echo "[NIJ] Usando DATABASE_URL do Render..."
  DB_HOST=$(echo $DATABASE_URL | sed -E 's|.*@([^:]+):.*|\1|')
else
  DB_HOST=db
fi

echo "[NIJ] Aguardando PostgreSQL em $DB_HOST..."
until pg_isready -h $DB_HOST -U "$POSTGRES_USER" -d "$POSTGRES_DB" -q; do
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
