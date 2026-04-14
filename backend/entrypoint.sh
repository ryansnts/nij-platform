#!/bin/sh
set -e

if [ -n "$DATABASE_URL" ]; then
  echo "[NIJ] Usando DATABASE_URL do Render..."
  DB_HOST=$(echo $DATABASE_URL | sed -E 's|.*@||' | sed -E 's|:.*||')
  DB_USER=$(echo $DATABASE_URL | sed -E 's|.*://||' | cut -d':' -f1)
  DB_PASS=$(echo $DATABASE_URL | sed -E 's|.*://[^:]+:||' | cut -d'@' -f1)
  DB_NAME=$(echo $DATABASE_URL | sed -E 's|.*/||')
else
  DB_HOST=db
  DB_USER=$POSTGRES_USER
  DB_PASS=$POSTGRES_PASSWORD
  DB_NAME=$POSTGRES_DB
fi

echo "[NIJ] Aguardando PostgreSQL em $DB_HOST..."
until pg_isready -h $DB_HOST -U "$DB_USER" -d "$DB_NAME" -q; do
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