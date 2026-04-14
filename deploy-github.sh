#!/bin/bash
# NIJ Platform - Deploy para GitHub

echo "=== NIJ Platform → GitHub ==="
echo ""
echo "1. Crie um repositório privado no GitHub:"
echo "   https://github.com/new"
echo "   Nome: nij-platform"
echo ""
echo "2. Copie a URL do seu repositório (ex: https://github.com/seu-user/nij-platform.git)"
echo ""
echo "3. Execute os comandos abaixo no terminal:"
echo ""
echo "   ===== COPIAR A PARTIR DAQUI ====="
echo ""

# Mostra os comandos
REPO_URL="https://github.com/SEU_USUARIO/nij-platform.git"

echo "git init"
echo "git add ."
echo 'git commit -m "NIJ Platform - Initial commit"'
echo "git branch -M main"
echo "git remote add origin $REPO_URL"
echo "git push -u origin main"

echo ""
echo "   ===== ATÉ AQUI ====="
echo ""
echo "4. Depois, no Render:"
echo "   - New → Docker"
echo "   - Nome: nij-backend"
echo "   - Repo: $REPO_URL"
echo "   - Dockerfile: Dockerfile.render"
echo "   - Root Directory: nij-platform"