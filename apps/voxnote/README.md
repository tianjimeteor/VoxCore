# VoxNote

> Privacy-first **voice meeting notebook** — record, transcribe, summarize,
> and search your meetings entirely on-device.

VoxNote is a desktop app built on top of [VoxCore](../../README.md). It
hooks into VoxCore's ASR + LLM pipelines to give you a Notion-style notebook
where every entry is a real recording with searchable transcripts and
auto-generated summaries.

## Why VoxNote?

* 🎤 **Press one button** — start recording and watch live captions appear.
* ✨ **Incremental summaries** every 30 s — never lose track during long calls.
* ✅ **Action items extracted** automatically from your speech ("we will…",
  "需要…", "TODO:", "Action item:").
* 🔍 **Full-text search** across every meeting (SQLite FTS5).
* 📝 **Export** to Markdown / DOCX / SRT.
* 🔒 **100% local** — bring your own ASR (faster-whisper) and LLM (Ollama,
  llama.cpp) and nothing ever leaves your machine.

## Install

### Pre-built downloads (recommended for end users)

Once a `voxnote-vX.Y.Z` tag is published, GitHub Releases ship:

* `voxnote-X.Y.Z-windows-x64-setup.exe` — Inno Setup installer (Start menu shortcut + uninstaller).
* `voxnote-X.Y.Z-windows-x64.zip` — portable, just unzip and run.
* `voxnote-X.Y.Z-macos-arm64.dmg` — drag-and-drop into Applications.
* `voxnote-X.Y.Z-linux-x86_64.AppImage` — `chmod +x ./*.AppImage && ./voxnote-…AppImage`.

### From source

```bash
# install voxcore + voxnote in editable mode
pip install -e .
pip install -e "apps/voxnote[local]"     # adds faster-whisper + sounddevice

# launch the desktop window
python -m voxnote
```

The app stores recordings + the SQLite database under your OS data dir:

| OS | Path |
|---|---|
| Windows | `%LOCALAPPDATA%\voxnote\voxnote.db` |
| macOS | `~/Library/Application Support/voxnote/voxnote.db` |
| Linux | `$XDG_DATA_HOME/voxnote/voxnote.db` (or `~/.local/share/voxnote/`) |

## Build the desktop bundle yourself

```powershell
# Windows: produces zip + (if Inno Setup is installed) setup.exe
powershell -ExecutionPolicy Bypass -File apps/voxnote/packaging/build.ps1
```

```bash
# macOS / Linux: portable tarball
bash apps/voxnote/packaging/build.sh

# Optional installer wrappers
bash apps/voxnote/packaging/build-dmg.sh        # macOS, requires `create-dmg`
bash apps/voxnote/packaging/build-appimage.sh   # Linux, requires `appimagetool`
```

Outputs land in `dist/`. See [packaging/ICON.md](packaging/ICON.md) for icons.

## Architecture

```
+---------------------+        +--------------------+        +-------------------+
|  PyWebView Window   |  JS    |   BridgeAPI        |  asyncio  |   Pipeline       |
|  (Vue 3 UI)         | <----> |   (api.py)         | <-------> |  (pipeline.py)   |
|  ui/index.html      |  bridge|   js_api object    |  threadsafe|  ASR + LLM tasks |
+---------------------+        +--------------------+        +-------------------+
                                                                 |
                                                                 v
                                                  +---------------------------+
                                                  |  Storage (storage.py)     |
                                                  |  SQLite + WAL + FTS5      |
                                                  +---------------------------+
```

* **Vue 3 over CDN** — no build tool, ship `ui/` directly.
* **PyWebView** runs the UI on the OS-native webview; no Electron, no Chromium.
* **VoxCore adapters** are pulled via `voxcore.adapters.asr.get_asr_adapter()`,
  so any ASR / LLM backend plugged into VoxCore (echo, faster-whisper, OpenAI,
  Ollama, …) works here too.
* **`whisper-local`** adapter is auto-registered when the package is installed
  with the `[local]` extra.

## Test

```bash
pytest apps/voxnote/tests
```

Tests cover storage CRUD + FTS, exporter (md/srt) round-trips, and pattern-
based TODO extraction.

## License

Apache-2.0 (same as VoxCore).
