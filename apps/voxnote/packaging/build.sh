#!/usr/bin/env bash
# Build VoxNote desktop bundle on macOS / Linux (portable .tar.gz only).
# Use build-dmg.sh or build-appimage.sh on top to produce native installers.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
export VOXNOTE_ROOT="$ROOT"
cd "$ROOT"

python -m pip install --upgrade pip
pip install -e .
pip install -e "apps/voxnote[build]"
pyinstaller --noconfirm "apps/voxnote/packaging/voxnote.spec"

OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"
case "$OS" in
  darwin) PLAT="macos-${ARCH}" ;;
  linux)  PLAT="linux-${ARCH}" ;;
  *)      PLAT="${OS}-${ARCH}" ;;
esac

VERSION=$(python -c "import apps.voxnote.voxnote as m; print(m.__version__)")
OUT="dist/voxnote-${VERSION}-${PLAT}.tar.gz"
rm -f "$OUT"
tar -czf "$OUT" -C dist voxnote
echo "[voxnote] portable bundle: $OUT"
