# PyInstaller spec for VoxNote — produces a windowed `--onedir` desktop bundle.
#
# Usage (from repo root):
#     pyinstaller apps/voxnote/packaging/voxnote.spec
#
# Outputs:
#     dist/voxnote/voxnote(.exe)   + ui/ + voxcore/* runtime
#
# Notes:
# * `--onedir`: 5x faster cold start than onefile; user-facing UX is identical
#   because we wrap it with Inno Setup (Windows) / DMG (macOS) / AppImage (Linux).
# * `console=False`: pure desktop window via PyWebView, no terminal flash.
# * faster-whisper / pyaudiowpatch / docx are optional — collect_submodules will
#   silently skip what's not installed.

from __future__ import annotations

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(os.environ.get("VOXNOTE_ROOT", ".")).resolve()
APP = ROOT / "apps" / "voxnote"

block_cipher = None


def _safe_collect(name: str) -> list[str]:
    try:
        return collect_submodules(name)
    except Exception:
        return []


hidden: list[str] = []
hidden += collect_submodules("voxnote")
hidden += collect_submodules("voxcore")
hidden += collect_submodules("webview")
hidden += _safe_collect("faster_whisper")
hidden += _safe_collect("ctranslate2")
hidden += _safe_collect("pyaudiowpatch")
hidden += _safe_collect("sounddevice")
hidden += _safe_collect("docx")

datas = [
    (str(APP / "ui"), "ui"),
]

icon_path = APP / "packaging" / "icon.ico"

a = Analysis(
    [str(APP / "voxnote" / "__main__.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "PyQt5", "PyQt6", "PySide2", "PySide6"],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="voxnote",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_path) if icon_path.exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="voxnote",
)
