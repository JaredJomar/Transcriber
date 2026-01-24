# -*- mode: python ; coding: utf-8 -*-
import os
import sys
import glob
from pathlib import Path

block_cipher = None

# Get spec file directory for absolute paths - use getcwd since we run from project dir
spec_dir = os.getcwd()

# Use absolute paths for icon and hook
icon_path = os.path.join(spec_dir, 'icons', 'app_icon_256x256.ico')
hook_torch_path = os.path.join(spec_dir, 'hook-torch.py')

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

# Add PyTorch DLLs and dependencies
extra_datas = []
try:
    import torch
    import numpy
    torch_dir = Path(torch.__file__).parent
    
    # Include ALL torch DLLs - including subdirectories
    torch_lib_dir = torch_dir / 'lib'
    if torch_lib_dir.exists():
        # Add DLLs to binaries (including nested directories)
        for dll_file in torch_lib_dir.rglob('*.dll'):
            rel_dir = dll_file.relative_to(torch_lib_dir).parent
            dest = 'torch/lib' if rel_dir == Path('.') else str(Path('torch/lib') / rel_dir)
            extra_binaries.append((str(dll_file), dest))
        
        # Add PYD files
        for pyd_file in torch_lib_dir.rglob('*.pyd'):
            rel_dir = pyd_file.relative_to(torch_lib_dir).parent
            dest = 'torch/lib' if rel_dir == Path('.') else str(Path('torch/lib') / rel_dir)
            extra_binaries.append((str(pyd_file), dest))
    
    # Include torch/bin directory
    torch_bin_dir = torch_dir / 'bin'
    if torch_bin_dir.exists():
        for dll_file in torch_bin_dir.rglob('*.dll'):
            extra_binaries.append((str(dll_file), 'torch/bin'))
    
    # Include numpy DLLs
    numpy_dir = Path(numpy.__file__).parent
    numpy_libs = numpy_dir / '.libs'
    if numpy_libs.exists():
        for dll_file in numpy_libs.glob('*.dll'):
            extra_binaries.append((str(dll_file), 'numpy/.libs'))
    
    # Add Microsoft Visual C++ Redistributable DLLs
    vcruntime_patterns = ['msvcp*.dll', 'vcruntime*.dll', 'concrt*.dll', 'vcomp*.dll']
    for search_dir in _search_dirs:
        if not os.path.isdir(search_dir):
            continue
        for pattern in vcruntime_patterns:
            for dll in glob.glob(os.path.join(search_dir, pattern)):
                extra_binaries.append((dll, '.'))
    
    # Also check conda environment for VC runtime
    if hasattr(sys, 'base_prefix'):
        conda_lib = os.path.join(sys.base_prefix, 'Library', 'bin')
        if os.path.exists(conda_lib):
            for pattern in vcruntime_patterns:
                for dll in glob.glob(os.path.join(conda_lib, pattern)):
                    extra_binaries.append((dll, '.'))
    
    print(f"Found {len([b for b in extra_binaries if 'torch' in str(b[0]).lower()])} torch binary files")
    print(f"Found {len([b for b in extra_binaries if 'numpy' in str(b[0]).lower()])} numpy binary files")
    print(f"Found {len([b for b in extra_binaries if any(x in str(b[0]).lower() for x in ['msvcp', 'vcruntime'])])} VC runtime files")
except ImportError as e:
    print(f"Warning: Import error during spec file processing: {e}")

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=extra_binaries,
    datas=[
        ('app', 'app'),
        ('transcriber', 'transcriber'),
    ] + extra_datas,
    hiddenimports=[
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtWidgets',
        'PyQt6.QtGui',
        'whisper',
        'torch',
        'torch._C',
        'torch._six',
        'torch.nn',
        'torch.nn.functional',
        'torch.jit',
        'torch.autograd',
        'torch.utils',
        'torch.utils.data',
        'torchaudio',
        'torchaudio.backend',
        'torchaudio.backend.soundfile_backend',
        'torchvision',
        'yt_dlp',
        'pyexpat',
        'xml.parsers.expat',
        'certifi',
        'ssl',
        '_ssl',
        'numpy',
        'numpy.core',
        'numpy.core._multiarray_umath',
        'numpy.random',
        'scipy',
        'scipy.signal',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[hook_torch_path],
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
    [],
    exclude_binaries=True,
    name='Transcriber',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Transcriber',
)
