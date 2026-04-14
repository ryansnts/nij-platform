# -*- mode: python ; coding: utf-8 -*-
import os
import sys

block_cipher = None
BASE_DIR = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    ['run.py'],
    pathex=[BASE_DIR],
    binaries=[
        # Inclui diretórios como binary (datas)
    ],
    datas=[
        ('backend\\core', 'backend\\core'),
        ('backend\\apps', 'backend\\apps'),
        ('backend\\manage.py', 'backend'),
        ('backend\\requirements.txt', 'backend'),
    ],
    hiddenimports=[
        'django', 'django.conf', 'django.core', 'django.db', 'django.forms',
        'django.http', 'django.template', 'django.views', 'django.utils',
        'rest_framework', 'rest_framework_simplejwt',
        'django_cors_headers', 'django_environ', 'environ',
        'PIL', 'PIL.Image', 'pdfplumber', 'pytesseract',
        'pdfminer', 'pdfminer.six', 'pypdfium2',
        'celery', 'celery.app', 'celery.task',
        'apps', 'apps.authentication', 'apps.documents', 'apps.analysis', 'apps.audit',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'PyQt5'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='NIJ_Sistema',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
)