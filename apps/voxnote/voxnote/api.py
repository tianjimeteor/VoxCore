"""JS Bridge surface — the object PyWebView exposes to ``window.pywebview.api``.

All methods are *synchronous* from the JS side; we kick async work onto the
shared asyncio loop running in a background thread.
"""
from __future__ import annotations

import asyncio
import logging
import os
import platform
from dataclasses import asdict
from pathlib import Path
from typing import Any

from . import __version__
from .exporter import export
from .pipeline import Pipeline
from .storage import Storage

logger = logging.getLogger("voxnote.api")


def _default_db_path() -> Path:
    if platform.system() == "Windows":
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "voxnote" / "voxnote.db"
    if platform.system() == "Darwin":
        return Path.home() / "Library" / "Application Support" / "voxnote" / "voxnote.db"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "voxnote" / "voxnote.db"


def _default_export_dir() -> Path:
    return Path.home() / "Documents" / "VoxNote"


class BridgeAPI:
    """Methods on this class become ``window.pywebview.api.*`` in JS."""

    def __init__(
        self,
        *,
        loop: asyncio.AbstractEventLoop,
        storage: Storage,
        asr_name: str = "echo",
        llm_name: str = "echo",
    ) -> None:
        self._loop = loop
        self._storage = storage
        self._asr_name = asr_name
        self._llm_name = llm_name
        self._pipeline: Pipeline | None = None

    # -- meta ---------------------------------------------------------------

    def info(self) -> dict[str, Any]:
        return {
            "version": __version__,
            "asr": self._asr_name,
            "llm": self._llm_name,
            "platform": platform.system(),
            "db_path": str(self._storage.db_path),
        }

    def settings(self) -> dict[str, Any]:
        return {"asr": self._asr_name, "llm": self._llm_name}

    def update_settings(self, asr: str | None = None, llm: str | None = None) -> dict[str, Any]:
        if asr:
            self._asr_name = asr
        if llm:
            self._llm_name = llm
        return self.settings()

    # -- recording ----------------------------------------------------------

    def start_recording(self, title: str = "Untitled session") -> dict[str, Any]:
        if self._pipeline and self._pipeline.session_id:
            return {"ok": False, "error": "already recording", "session_id": self._pipeline.session_id}
        self._pipeline = Pipeline(
            storage=self._storage,
            asr_name=self._asr_name,
            llm_name=self._llm_name,
        )
        try:
            session_id = self._submit(self._pipeline.start(title=title))
        except Exception as err:  # noqa: BLE001
            self._pipeline = None
            return {"ok": False, "error": str(err)}
        return {"ok": True, "session_id": session_id}

    def stop_recording(self) -> dict[str, Any]:
        if not self._pipeline:
            return {"ok": False, "error": "not recording"}
        sid = self._pipeline.session_id
        try:
            summary = self._submit(self._pipeline.stop())
        except Exception as err:  # noqa: BLE001
            return {"ok": False, "error": str(err), "session_id": sid}
        finally:
            self._pipeline = None
        return {
            "ok": True,
            "session_id": sid,
            "summary": _summary_to_dict(summary) if summary else None,
        }

    def is_recording(self) -> bool:
        return bool(self._pipeline and self._pipeline.session_id)

    def live_captions(self) -> list[dict[str, Any]]:
        if not self._pipeline:
            return []
        return [
            {"text": c.text, "final": c.final, "speaker": c.speaker, "ts": c.timestamp_ms}
            for c in self._pipeline.captions_snapshot()
        ]

    def live_summary(self) -> dict[str, Any] | None:
        if not self._pipeline:
            return None
        s = self._pipeline.latest_summary
        return _summary_to_dict(s) if s else None

    # -- history ------------------------------------------------------------

    def list_sessions(self, limit: int = 100) -> list[dict[str, Any]]:
        return [asdict(s) for s in self._storage.list_sessions(limit=limit)]

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        s = self._storage.get_session(session_id)
        if not s:
            return None
        out = asdict(s)
        out["segments"] = [asdict(seg) for seg in self._storage.list_segments(session_id)]
        sm = self._storage.get_latest_summary(session_id)
        out["summary"] = _summary_to_dict(sm) if sm else None
        return out

    def rename_session(self, session_id: str, title: str) -> dict[str, Any]:
        self._storage.rename_session(session_id, title)
        return {"ok": True}

    def delete_session(self, session_id: str) -> dict[str, Any]:
        self._storage.delete_session(session_id)
        return {"ok": True}

    def search(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        return self._storage.search(query, limit=limit)

    # -- export -------------------------------------------------------------

    def export(self, session_id: str, fmt: str = "md", out_dir: str | None = None) -> dict[str, Any]:
        target_dir = Path(out_dir) if out_dir else _default_export_dir()
        try:
            path = export(self._storage, session_id, fmt, target_dir)
        except Exception as err:  # noqa: BLE001
            return {"ok": False, "error": str(err)}
        return {"ok": True, "path": str(path)}

    def open_export_dir(self) -> dict[str, Any]:
        target = _default_export_dir()
        target.mkdir(parents=True, exist_ok=True)
        try:
            if platform.system() == "Windows":
                os.startfile(str(target))  # type: ignore[attr-defined]
            elif platform.system() == "Darwin":
                os.system(f'open "{target}"')
            else:
                os.system(f'xdg-open "{target}" >/dev/null 2>&1')
        except Exception as err:  # noqa: BLE001
            return {"ok": False, "error": str(err)}
        return {"ok": True, "path": str(target)}

    # -- helpers ------------------------------------------------------------

    def _submit(self, coro):
        """Run a coroutine on the shared loop and wait for the result."""
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result()


def _summary_to_dict(s) -> dict[str, Any]:
    return {
        "kind": s.kind,
        "generated_at": s.generated_at,
        "summary_md": s.summary_md,
        "todos": list(s.todos),
    }
