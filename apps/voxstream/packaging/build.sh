#!/usr/bin/env bash
# Build VoxStream desktop bundle on macOS / Linux.
# Usage: bash apps/voxstream/packaging/build.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
export VOXSTREAM_ROOT="$ROOT"
cd "$ROOT"

python -m pip install --upgrade pip
pip install -e .
pip install -e "apps/voxstream[build]"
pyinstaller --noconfirm "apps/voxstream/packaging/voxstream.spec"

OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"
case "$OS" in
  darwin) PLAT="macos-${ARCH}" ;;
  linux)  PLAT="linux-${ARCH}" ;;
  *)      PLAT="${OS}-${ARCH}" ;;
esac

VERSION=$(python -c "import apps.voxstream.voxstream as m; print(m.__version__)")
OUT="dist/voxstream-${VERSION}-${PLAT}.tar.gz"
rm -f "$OUT"
tar -czf "$OUT" -C dist voxstream
echo "[voxstream] bundle ready: $OUT"
