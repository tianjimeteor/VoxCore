#!/usr/bin/env bash
# Wrap PyInstaller output into a Linux AppImage.
# Requires appimagetool (download once: https://github.com/AppImage/AppImageKit/releases).
# Run AFTER build.sh has populated dist/voxnote/.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$ROOT"

if ! command -v appimagetool >/dev/null 2>&1; then
    echo "[voxnote] appimagetool not found in PATH — see https://github.com/AppImage/AppImageKit/releases." >&2
    exit 1
fi

if [[ ! -d "dist/voxnote" ]]; then
    echo "[voxnote] dist/voxnote/ not found — run packaging/build.sh first." >&2
    exit 1
fi

VERSION=$(python -c "import apps.voxnote.voxnote as m; print(m.__version__)")
ARCH="$(uname -m)"
APPDIR="dist/_appdir"
OUT="dist/voxnote-${VERSION}-linux-${ARCH}.AppImage"

rm -rf "$APPDIR" "$OUT"
mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/share/applications" "$APPDIR/usr/share/icons/hicolor/256x256/apps"

cp -R dist/voxnote/. "$APPDIR/usr/bin/"

# AppRun entry point
cat > "$APPDIR/AppRun" <<'EOF'
#!/usr/bin/env bash
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/bin/voxnote" "$@"
EOF
chmod +x "$APPDIR/AppRun"

# Desktop file
cat > "$APPDIR/voxnote.desktop" <<EOF
[Desktop Entry]
Name=VoxNote
Comment=Privacy-first voice meeting notebook
Exec=voxnote
Icon=voxnote
Type=Application
Categories=Office;AudioVideo;
StartupNotify=true
EOF
cp "$APPDIR/voxnote.desktop" "$APPDIR/usr/share/applications/voxnote.desktop"

# Placeholder icon (1x1 transparent PNG) — replace with real artwork later.
ICON_DST="$APPDIR/voxnote.png"
if [[ -f "apps/voxnote/packaging/icon.png" ]]; then
    cp "apps/voxnote/packaging/icon.png" "$ICON_DST"
else
    python -c "import base64,sys; sys.stdout.buffer.write(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNgAAIAAAUAAen63NgAAAAASUVORK5CYII='))" > "$ICON_DST"
fi
cp "$ICON_DST" "$APPDIR/usr/share/icons/hicolor/256x256/apps/voxnote.png"

ARCH="$ARCH" appimagetool "$APPDIR" "$OUT"
rm -rf "$APPDIR"
echo "[voxnote] AppImage ready: $OUT"
