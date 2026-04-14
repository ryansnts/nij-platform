import os
import sys
import subprocess
import webbrowser
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

os.chdir(os.path.join(BASE_DIR, "backend"))

print("=" * 50)
print("NIJ - Sistema de Análise Financeira")
print("=" * 50)
print()

print("[1/4] Verificando banco de dados...")
from django.core.management import execute_from_command_line

execute_from_command_line(["manage.py", "migrate", "--run-syncdb"])

print("\n[2/4] Criando usuário admin...")
try:
    execute_from_command_line(["manage.py", "seed_admin"])
except:
    pass

print("\n[3/4] Coletando arquivos estáticos...")
execute_from_command_line(["manage.py", "collectstatic", "--noinput"])

print("\n[4/4] Iniciando servidor...")
execute_from_command_line(["manage.py", "runserver", "0.0.0.0:8000"])

print("\nAcesse: http://localhost:8000")
print("Login: admin / Admin@NIJ2026")
