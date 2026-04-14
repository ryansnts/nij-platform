import os
import sys


def get_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


BASE_DIR = get_base_dir()

if getattr(sys, "frozen", False):
    backend_dir = os.path.join(sys._MEIPASS, "backend")
else:
    backend_dir = os.path.join(BASE_DIR, "backend")

sys.path.insert(0, backend_dir)
os.chdir(backend_dir)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings_standalone")

print("=" * 50)
print("NIJ - Sistema de Analise Financeira")
print("=" * 50)
print()

from django.core.management import execute_from_command_line

print("[1/4] Verificando banco de dados...")
execute_from_command_line(["manage.py", "migrate", "--run-syncdb"])

print("\n[2/4] Criando usuario admin...")
try:
    execute_from_command_line(["manage.py", "seed_admin"])
except:
    pass

print("\n[3/4] Coletando arquivos staticos...")
execute_from_command_line(["manage.py", "collectstatic", "--noinput"])

print("\n[4/4] Iniciando servidor...")
print("\nAcesse: http://localhost:8000")
print("Login: admin / Admin@NIJ2026")
print()

execute_from_command_line(["manage.py", "runserver", "0.0.0.0:8000"])
