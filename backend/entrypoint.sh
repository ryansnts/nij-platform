#!/bin/sh
set -e

if [ -n "$DATABASE_URL" ]; then
  echo "[NIJ] Usando DATABASE_URL do Render..."
  # Extrai host da URL: postgresql://user:pass@host:port/db
  # Exemplo: postgresql://nij_db_user:senha@dpg-xxx.a.onrender.com:5432/nij_db
  DB_HOST=$(echo $DATABASE_URL | sed -E 's|.*://.*@||' | cut -d':' -f1)
  DB_USER=$(echo $DATABASE_URL | sed -E 's|.*://||' | cut -d':' -f1)
  DB_PASS=$(echo $DATABASE_URL | sed -E 's|.*://[^:]+:||' | cut -d'@' -f1)
  DB_NAME=$(echo $DATABASE_URL | rev | cut -d'/' -f1 | rev)
  DB_PORT=$(echo $DATABASE_URL | grep -oP ':\d+/' | sed 's|/||' || echo "5432")
else
  DB_HOST=db
  DB_USER=${POSTGRES_USER:-nij_user}
  DB_PASS=${POSTGRES_PASSWORD:-nij_pass}
  DB_NAME=${POSTGRES_DB:-nij_db}
  DB_PORT=5432
fi

echo "[NIJ] Host: $DB_HOST, Port: $DB_PORT, User: $DB_USER, DB: $DB_NAME"

echo "[NIJ] Aguardando PostgreSQL..."
for i in $(seq 1 60); do
  if pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -q 2>/dev/null; then
    echo "[NIJ] PostgreSQL pronto!"
    break
  fi
  echo "[NIJ] Tentativa $i/60..."
  sleep 2
done

echo "[NIJ] Aplicando migrations..."
python manage.py migrate --noinput

echo "[NIJ] Criando admin inicial..."
python manage.py seed_admin || true

echo "[NIJ] Coletando arquivos estaticos..."
python manage.py collectstatic --noinput --clear

echo "[NIJ] Iniciando servidor..."
exec "$@"