"""VoxNote desktop entry point.

Spawns a dedicated asyncio loop in a background thread so the JS bridge can
``run_coroutine_threadsafe`` while PyWebView owns the main thread.

Usage:
    voxnote                       # opens the desktop window
    voxnote --asr whisper-local   # offline mode
    voxnote --headless            # CLI tools without window (for tests / scripts)
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import threading
from pathlib import Path

from . import __version__
from .api import BridgeAPI, _default_db_path
from .storage import Storage

logger = logging.getLogger("voxnote.main")
_HERE = Path(__file__).resolve().parent
_UI_DIR = (_HERE.parent / "ui").resolve()


def _spawn_loop() -> tuple[asyncio.AbstractEventLoop, threading.Thread]:
    loop = asyncio.new_event_loop()

    def _run() -> None:
        asyncio.set_event_loop(loop)
        loop.run_forever()

    th = threading.Thread(target=_run, daemon=True, name="voxnote-asyncio")
    th.start()
    return loop, th


def _launch_window(api: BridgeAPI) -> None:
    try:
        import webview  # type: ignore
    except ImportError as err:
        raise RuntimeError(
            "pywebview not installed. `pip install voxnote` (the wheel pulls it in)."
        ) from err

    index = _UI_DIR / "index.html"
    if not index.is_file():
        raise RuntimeError(f"UI assets missing: expected {index}")
    webview.create_window(
        title=f"VoxNote {__version__}",
        url=str(index),
        js_api=api,
        width=1280,
        height=820,
        min_size=(900, 600),
        text_select=True,
    )
    webview.start(debug=False)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="voxnote", description="VoxNote desktop meeting notes.")
    p.add_argument("--version", action="version", version=f"voxnote {__version__}")
    p.add_argument("--asr", default="echo", help="ASR adapter name. Try 'whisper-local' for offline.")
    p.add_argument("--llm", default="echo", help="LLM adapter name. Try 'openai_compatible' with API key set.")
    p.add_argument("--db", default=None, help=f"SQLite path (default: {_default_db_path()})")
    p.add_argument("--headless", action="store_true", help="Initialize storage but skip the window.")
    return p


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

    db_path = Path(args.db) if args.db else _default_db_path()
    storage = Storage(db_path)
    loop, _ = _spawn_loop()
    api = BridgeAPI(loop=loop, storage=storage, asr_name=args.asr, llm_name=args.llm)

    if args.headless:
        print(f"VoxNote {__version__}: storage={db_path} asr={args.asr} llm={args.llm}")
        return 0

    try:
        _launch_window(api)
    finally:
        loop.call_soon_threadsafe(loop.stop)
        storage.close()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
