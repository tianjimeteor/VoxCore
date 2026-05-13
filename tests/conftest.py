"""Shared pytest fixtures.

We use a per-session in-memory SQLite database and a test JWT secret set via
env var in conftest BEFORE any VoxCore module is imported.
"""
from __future__ import annotations

import os

os.environ.setdefault(
    "JWT_SECRET_KEY", "test-only-do-not-use-in-production-xxxxxxxx0123456789"
)
os.environ.setdefault("DATABASE_URL", "sqlite:///./voxcore-test.db")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from voxcore import VoxCore  # noqa: E402
from voxcore.database import Base, engine  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _setup_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


@pytest.fixture
def app() -> VoxCore:
    return VoxCore(asr="echo", llm="echo")


@pytest.fixture
def client(app: VoxCore) -> TestClient:
    return TestClient(app.asgi())
