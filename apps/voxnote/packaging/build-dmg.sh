#!/usr/bin/env bash
# Wrap PyInstaller output into a macOS .dmg.
# Requires `create-dmg` (brew install create-dmg).
# Run AFTER build.sh has populated dist/voxnote/.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$ROOT"

if ! command -v create-dmg >/dev/null 2>&1; then
    echo "[voxnote] create-dmg not found — install via 'brew install create-dmg'." >&2
    exit 1
fi

if [[ ! -d "dist/voxnote" ]]; then
    echo "[voxnote] dist/voxnote/ not found — run packaging/build.sh first." >&2
    exit 1
fi

VERSION=$(python -c "import apps.voxnote.voxnote as m; print(m.__version__)")
ARCH="$(uname -m)"
APP_NAME="VoxNote.app"
STAGE="dist/_dmg-stage"
DMG="dist/voxnote-${VERSION}-macos-${ARCH}.dmg"

rm -rf "$STAGE" "$DMG"
mkdir -p "$STAGE/$APP_NAME/Contents/MacOS"
mkdir -p "$STAGE/$APP_NAME/Contents/Resources"

# Minimal Info.plist
cat > "$STAGE/$APP_NAME/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key><string>VoxNote</string>
    <key>CFBundleDisplayName</key><string>VoxNote</string>
    <key>CFBundleIdentifier</key><string>com.voxcore.voxnote</string>
    <key>CFBundleVersion</key><string>${VERSION}</string>
    <key>CFBundleShortVersionString</key><string>${VERSION}</string>
    <key>CFBundleExecutable</key><string>voxnote</string>
    <key>CFBundlePackageType</key><string>APPL</string>
    <key>NSMicrophoneUsageDescription</key>
    <string>VoxNote needs microphone access to transcribe meetings.</string>
    <key>LSMinimumSystemVersion</key><string>11.0</string>
    <key>NSHighResolutionCapable</key><true/>
</dict>
</plist>
PLIST

# Copy PyInstaller output into the .app
cp -R dist/voxnote/. "$STAGE/$APP_NAME/Contents/MacOS/"

create-dmg \
    --volname "VoxNote ${VERSION}" \
    --window-size 540 360 \
    --icon-size 96 \
    --icon "$APP_NAME" 140 180 \
    --app-drop-link 400 180 \
    "$DMG" \
    "$STAGE"

rm -rf "$STAGE"
echo "[voxnote] dmg ready: $DMG"
