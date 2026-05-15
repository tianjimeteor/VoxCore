# VoxStream

[![License](https://img.shields.io/badge/license-Apache%202.0-0A7C74?style=flat-square)](../../LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)](../../pyproject.toml)
[![VoxCore](https://img.shields.io/badge/powered%20by-VoxCore-5E60CE?style=flat-square)](../..)

> Drop-in **OBS Browser Source** for real-time captions. Powered by [VoxCore](../..). Apache-2.0.

**Use case** — you stream / lecture / record meetings and want live subtitles burned over the scene without paying $10/month for a SaaS captioner.

```
You speak  →  VoxStream  →  WebSocket  →  OBS Browser Source  →  Captions on stream
```

## Quick start

### Option A — download the bundle (no Python)

Grab `voxstream-0.1.0-windows-x64.zip` (or macOS / Linux) from the [Releases page](https://github.com/tianjimeteor/VoxCore/releases), unzip, then:

```
voxstream.exe run
```

In OBS: **+ Add → Browser → URL: `http://localhost:7860/overlay?theme=streaming`** → Width 1920, Height 1080, transparent.

### Option B — pip

```bash
pip install voxstream                  # base
pip install "voxstream[windows]"       # adds WASAPI loopback (recommended)
voxstream run
```

### Option C — try in your browser (no install)

[Open the Hugging Face Space](https://huggingface.co/spaces/) — speak, see captions.

## Themes

| Theme       | Best for                       | URL parameter        |
|-------------|--------------------------------|----------------------|
| `streaming` | Twitch / B-station, neon glow  | `?theme=streaming`   |
| `classroom` | Lectures, white background     | `?theme=classroom`   |
| `meeting`   | Zoom / Teams recordings        | `?theme=meeting`     |
| `minimal`   | Minimal, transparent text-only | `?theme=minimal`     |

Other params: `&max_lines=3`, `&linger=6000` (ms), `&debug=1` (test rendering with no server).

## Audio backends

| OS       | Default                     | System audio capture                        |
|----------|-----------------------------|---------------------------------------------|
| Windows  | WASAPI loopback (recommended) | Captures system speakers + mic mix         |
| macOS    | Default input mic           | Install [BlackHole](https://existential.audio/blackhole/) for system audio |
| Linux    | Default input               | Use a PulseAudio `monitor` source           |

Probe what's available:
```bash
voxstream check
```

## Switch ASR engine

```bash
voxstream run --asr xunfei              # iFlytek streaming ASR
voxstream run --asr whisper             # local whisper (when adapter is installed)
voxstream run --translate zh            # cross-lingual mode (LLM-translated captions)
```

Adapters live in [`voxcore.adapters.asr`](../../voxcore/adapters/asr/). Adding a new one is ~30 LoC; see [docs/adapters.md](../../docs/adapters.md).

## Build the bundle yourself

```powershell
# Windows
powershell -ExecutionPolicy Bypass -File apps/voxstream/packaging/build.ps1
```

```bash
# macOS / Linux
bash apps/voxstream/packaging/build.sh
```

Output lands in `dist/voxstream-<version>-<platform>.<zip|tar.gz>`.

## License

Apache-2.0. See [LICENSE](../../LICENSE).
