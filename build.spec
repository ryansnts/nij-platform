# -*- mode: python ; coding: utf-8 -*-

import os

block_cipher = None

backend_path = os.path.join(os.getcwd(), 'backend')

a = Analysis(
    ['run_standalone.py'],
    pathex=[os.getcwd()],
    binaries=[],
    datas=[
        (os.path.join(backend_path, 'apps'), 'apps'),
        (os.path.join(backend_path, 'core'), 'core'),
        (os.path.join(backend_path, 'db.sqlite3'), '.'),
    ],
    hiddenimports=[
        'django', 'djangorestframework', 'celery', 'pdfplumber', 'pytesseract',
        'PIL', 'cv2', 'numpy', 'pandas'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)