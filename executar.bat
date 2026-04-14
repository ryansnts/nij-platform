@echo off
chcp 65001 >nul
title NIJ - Sistema de Analise Financeira

echo.
echo ================================================
echo NIJ - Sistema de Analise Financeira (Standalone)
echo ================================================
echo.

cd /d "%~dp0"

if not exist backend\venv (
    echo [1/5] Criando ambiente virtual...
    python -m venv backend\venv
    call backend\venv\Scripts\pip install -r backend\requirements.txt
)

echo.
echo [2/5] Ativando ambiente virtual...
call backend\venv\Scripts\activate.bat

echo.
echo [3/5] Verificando banco de dados...
python backend\manage.py migrate --run-syncdb

echo.
echo [4/5] Criando usuario admin...
python backend\manage.py seed_admin

echo.
echo [5/5] Iniciando servidor...
echo.
echo Acesse: http://localhost:8000
echo Login: admin / Admin@NIJ2026
echo.

python backend\manage.py runserver 0.0.0.0:8000

pause