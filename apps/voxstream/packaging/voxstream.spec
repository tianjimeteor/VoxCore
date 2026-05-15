# PyInstaller spec for VoxStream — used by both `build.ps1` and CI.
# Produces a `--onedir` bundle: dist/voxstream/voxstream(.exe) + overlay/.
#
# Usage:
#     pyinstaller apps/voxstream/packaging/voxstream.spec
#
# Notes:
# * `--onedir` over `--onefile`: 5x faster cold-start, easier debugging.
# * Static `overlay/` is bundled via `datas` and shipped alongside the binary.
# * pyaudiowpatch is Windows-only and lazy-imported by capture.py.

from __future__ import annotations

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(os.environ.get("VOXSTREAM_ROOT", ".")).resolve()
APP = ROOT / "apps" / "voxstream"

block_cipher = None

hidden = []
hidden += collect_submodules("voxstream")
hidden += collect_submodules("voxcore")
hidden += collect_submodules("uvicorn")
hidden += collect_submodules("anyio")

datas = [
    (str(APP / "overlay"), "overlay"),
]

a = Analysis(
    [str(APP / "voxstream" / "__main__.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib"],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="voxstream",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="voxstream",
)
