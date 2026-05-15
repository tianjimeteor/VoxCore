"""Smoke tests for VoxStream — exercise the FastAPI app without real audio."""
from __future__ import annotations

import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from voxstream.server import CaptionBroadcaster, create_app


def test_health_endpoint() -> None:
    app = create_app(asr="echo")
    with TestClient(app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["asr"] == "echo"


def test_overlay_index_served() -> None:
    app = create_app(asr="echo")
    with TestClient(app) as client:
        resp = client.get("/overlay")
        assert resp.status_code == 200
        assert "VoxStream caption overlay" in resp.text


def test_overlay_static_assets() -> None:
    app = create_app(asr="echo")
    with TestClient(app) as client:
        for asset in ("style.css", "caption.js"):
            resp = client.get(f"/overlay/{asset}")
            assert resp.status_code == 200, asset
            assert resp.text  # non-empty


def test_overlay_path_traversal_blocked() -> None:
    app = create_app(asr="echo")
    with TestClient(app) as client:
        resp = client.get("/overlay/..%2F..%2Fpyproject.toml")
        assert resp.status_code in (403, 404)


def test_websocket_broadcast() -> None:
    app = create_app(asr="echo")
    with TestClient(app) as client:
        with client.websocket_connect("/ws/caption") as ws:
            payload = {"text": "hello", "final": True, "lang": "auto"}
            asyncio.run(app.state.bus.broadcast(payload))
            received = json.loads(ws.receive_text())
            assert received["text"] == "hello"
            assert received["final"] is True


@pytest.mark.parametrize("asr", ["echo"])
def test_create_app_with_translate(asr: str) -> None:
    # Translation enabled — should construct without error.
    app = create_app(asr=asr, translate_to="zh", llm_for_translate="echo")
    with TestClient(app) as client:
        body = client.get("/health").json()
        assert body["translate_to"] == "zh"


def test_broadcaster_drops_dead_clients() -> None:
    bus = CaptionBroadcaster()

    class _DeadWS:
        async def send_text(self, _msg: str) -> None:  # noqa: D401
            raise RuntimeError("closed")

    async def _run() -> None:
        async with bus._lock:
            bus._clients.add(_DeadWS())  # type: ignore[arg-type]
        await bus.broadcast({"text": "x", "final": True})
        async with bus._lock:
            assert len(bus._clients) == 0

    asyncio.run(_run())
