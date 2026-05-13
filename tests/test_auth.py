"""Auth happy paths and enumeration resistance."""
from __future__ import annotations

import uuid

from fastapi.testclient import TestClient


def _u() -> str:
    return "u" + uuid.uuid4().hex[:10]


def test_register_and_login(client: TestClient) -> None:
    username = _u()
    r = client.post(
        "/auth/register", json={"username": username, "password": "strongpass123"}
    )
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]
    assert token

    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["username"] == username


def test_short_password_rejected(client: TestClient) -> None:
    r = client.post("/auth/register", json={"username": _u(), "password": "short"})
    # Pydantic enforces min_length=10 at schema level.
    assert r.status_code == 422


def test_login_unknown_and_wrong_password_indistinguishable(client: TestClient) -> None:
    username = _u()
    client.post(
        "/auth/register", json={"username": username, "password": "strongpass123"}
    )

    wrong = client.post(
        "/auth/login", json={"username": username, "password": "wrongpassword"}
    )
    unknown = client.post(
        "/auth/login", json={"username": "never-existed-xxx", "password": "whatever12"}
    )
    assert wrong.status_code == 401
    assert unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "healthy"}
