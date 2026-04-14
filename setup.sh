#!/bin/bash
echo "============================================"
echo "  NIJ - Núcleo de Inteligência Jurídica"
echo "  Setup Automático"
echo "============================================"
echo ""

# Verificar Docker
if ! command -v docker &> /dev/null; then
    echo "[ERRO] Docker não encontrado. Instale: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo "[ERRO] Docker Compose não encontrado."
    exit 1
fi

echo "[OK] Docker encontrado."
echo ""

# Criar .env se não existir
if [ ! -f .env ]; then
    echo "[INFO] Criando arquivo .env a partir do .env.example..."
    cp .env.example .env
    echo "[OK] Arquivo .env criado."
else
    echo "[OK] Arquivo .env já existe."
fi
echo ""

# Subir containers
echo "[INFO] Construindo e iniciando containers..."
echo "       Isso pode levar alguns minutos na primeira vez."
echo ""
docker compose up -d --build

if [ $? -ne 0 ]; then
    echo ""
    echo "[ERRO] Falha ao iniciar containers."
    exit 1
fi

echo ""
echo "============================================"
echo "  Setup concluído com sucesso!"
echo "============================================"
echo ""
echo "  Acesse: http://localhost"
echo ""
echo "  Login:"
echo "    Usuário: admin"
echo "    Senha:   Admin@NIJ2026"
echo ""
echo "  API Docs: http://localhost/api/docs/"
echo ""
echo "  Para parar:  docker compose down"
echo "  Para logs:   docker compose logs -f"
echo "============================================"
