@echo off
echo ============================================
echo   NIJ - Nucleo de Inteligencia Juridica
echo   Setup Automatico
echo ============================================
echo.

:: Verificar Docker
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Docker nao encontrado. Instale o Docker Desktop:
    echo        https://www.docker.com/products/docker-desktop/
    pause
    exit /b 1
)

docker compose version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Docker Compose nao encontrado.
    pause
    exit /b 1
)

echo [OK] Docker encontrado.
echo.

:: Criar .env se nao existir
if not exist .env (
    echo [INFO] Criando arquivo .env a partir do .env.example...
    copy .env.example .env >nul
    echo [OK] Arquivo .env criado. Edite se necessario.
) else (
    echo [OK] Arquivo .env ja existe.
)
echo.

:: Subir containers
echo [INFO] Construindo e iniciando containers...
echo        Isso pode levar alguns minutos na primeira vez.
echo.
docker compose up -d --build

if %errorlevel% neq 0 (
    echo.
    echo [ERRO] Falha ao iniciar containers. Verifique os logs:
    echo        docker compose logs
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Setup concluido com sucesso!
echo ============================================
echo.
echo   Acesse: http://localhost
echo.
echo   Login:
echo     Usuario: admin
echo     Senha:   Admin@NIJ2026
echo.
echo   API Docs: http://localhost/api/docs/
echo.
echo   Para parar:  docker compose down
echo   Para logs:   docker compose logs -f
echo ============================================
pause
