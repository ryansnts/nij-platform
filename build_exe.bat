@echo off
chcp 65001 >nul
title NIJ - Build Executavel

echo.
echo ================================================
echo NIJ - Compilando Executavel
echo ================================================
echo.

cd /d "%~dp0"

if not exist backend\venv (
    echo [1/6] Criando ambiente virtual...
    python -m venv backend\venv
    call backend\venv\Scripts\pip install -r backend\requirements.txt
)

echo.
echo [2/6] Ativando ambiente virtual...
call backend\venv\Scripts\activate.bat

echo.
echo [3/6] Instalando PyInstaller...
pip install pyinstaller

echo.
echo [4/6] Verificando banco de dados...
python backend\manage.py migrate --run-syncdb 2>nul

echo.
echo [5/6] Criando usuario admin...
python backend\manage.py seed_admin 2>nul

echo.
echo [6/6] Compilando executavel...
pyinstaller nij.spec --clean

echo.
echo ================================================
echo CONCLUIDO!
echo Executavel: dist\NIJ_Sistema.exe
echo ================================================
echo.

pause