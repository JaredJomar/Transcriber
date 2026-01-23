# -*- mode: python ; coding: utf-8 -*-
import os
import sys
import glob
from pathlib import Path

block_cipher = None

# Use Windows-style path for icon (if exists)
icon_path = 'icons\\app_icon.ico' if os.path.exists('icons\\app_icon.ico') else None

# Try to include expat and OpenSSL DLLs explicitly
extra_binaries = []
_search_dirs = [
    os.path.join(sys.base_prefix, 'DLLs'),
    os.path.join(sys.base_prefix, 'Library', 'bin'),
    sys.base_prefix,
]
_expat_patterns = (
    'libexpat.dll',
    'expat.dll',
    'libexpat-*.dll',
    'libexpat*.dll',
)
_openssl_patterns = (
    'libssl-*.dll',
    'libcrypto-*.dll',
    'libssl*.dll',
    'libcrypto*.dll',
    'openssl*.dll',
)
for d in _search_dirs:
    if not os.path.isdir(d):
        continue
    for pat in (*_expat_patterns, *_openssl_patterns):
        for dll in glob.glob(os.path.join(d, pat)):
            extra_binaries.append((dll, '.'))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=extra_binaries,
    datas=[
        ('app', 'app'),
        ('transcriber', 'transcriber'),
        ('helpers.py', '.'),
    ],
    hiddenimports=[
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtWidgets',
        'PyQt6.QtGui',
        'whisper',
        'torch',
        'torchaudio',
        'torchvision',
        'yt_dlp',
        'pyexpat',
        'xml.parsers.expat',
        'certifi',
        'ssl',
        '_ssl',
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
    name='Transcriber',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
)
