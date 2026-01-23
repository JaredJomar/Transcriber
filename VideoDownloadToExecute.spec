import os
import sys
import glob
from pathlib import Path

block_cipher = None

# Use Windows-style path for icon
icon_path = 'icons\\app_icon.ico'

# Try to include expat and OpenSSL DLLs explicitly (helps avoid pyexpat/_ssl load errors)
extra_binaries = []
_search_dirs = [
    os.path.join(sys.base_prefix, 'DLLs'),                # vanilla Python
    os.path.join(sys.base_prefix, 'Library', 'bin'),      # conda/Anaconda
    sys.base_prefix,                                      # fallback
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
            # (source, destfolder)
            extra_binaries.append((dll, '.'))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=extra_binaries,
    datas=[
        ('settings.json', '.'),
        ('icons', 'icons'),
        ('img', 'img'),
        ('src/constants.py', 'src'),
        ('src/download_thread.py', 'src'),
        ('src/helpers.py', 'src'),
        ('src/main_window.py', 'src'),
        ('src/settings_window.py', 'src'),
        ('src/__init__.py', 'src'),
    ],
    hiddenimports=[
        'PyQt5',
        'yt_dlp',
        # Ensure XML parser binary is bundled
        'pyexpat',
        'xml.parsers.expat',
        # SSL CA bundle support for API calls
        'certifi',
        # Ensure stdlib ssl and its extension are collected
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
    name='VideoDownload',
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
