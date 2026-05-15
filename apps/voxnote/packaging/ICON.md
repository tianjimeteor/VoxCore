# Icon assets

Drop your real icons here:

* `icon.ico` — Windows (256×256, multi-size). Used by `voxnote.spec` and Inno Setup.
* `icon.icns` — macOS. Used by `build-dmg.sh` (optional).
* `icon.png` — Linux 256×256. Used by `build-appimage.sh`.

The build pipelines tolerate missing icons (a 1×1 placeholder is generated for
AppImage, and PyInstaller skips the icon flag if `icon.ico` is absent).

You can generate all three from a single 1024×1024 PNG using e.g. ImageMagick or
the online converter at https://realfavicongenerator.net.
