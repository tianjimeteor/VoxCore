"""WebSocket auth + text round-trip against the echo LLM."""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect


def test_ws_requires_token(client: TestClient) -> None:
    # Server must close the WS handshake when no token is provided.
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws") as ws:
            ws.receive_text()


def test_ws_echo_round_trip(app, client: TestClient) -> None:
    # Wire the LLM to stream chunks back over the WebSocket; without this,
    # VoxCore is intentionally hands-off and won't emit anything after the
    # transcript echo. This matches what an integrating app would write.
    @app.on_transcript
    async def _stream_back(text, ctx):
        if app.llm is None:
            return
        async for chunk in app.llm.complete(text):
            await ctx.websocket.send_json({"type": "chunk", "text": chunk})

    username = "ws" + uuid.uuid4().hex[:8]
    r = client.post(
        "/auth/register", json={"username": username, "password": "strongpass123"}
    )
    token = r.json()["access_token"]

    with client.websocket_connect(f"/ws?token={token}") as ws:
        ws.send_json({"type": "text", "text": "hello world"})

        # Expect a transcript echo then at least one chunk.
        first = ws.receive_json()
        assert first["type"] == "transcript"
        assert first["text"] == "hello world"

        got_chunk = False
        for _ in range(20):
            msg = ws.receive_json()
            if msg["type"] == "chunk":
                got_chunk = True
                break
        assert got_chunk
