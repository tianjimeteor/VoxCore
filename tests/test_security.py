"""Security invariants — these tests exist to prevent regressions."""
from __future__ import annotations

import importlib

import pytest


@pytest.mark.parametrize(
    "insecure",
    ["", "REPLACE_ME_OR_REFUSE_TO_START", "your-secret-key-change-in-production", "changeme"],
)
def test_insecure_jwt_rejected(monkeypatch: pytest.MonkeyPatch, insecure: str) -> None:
    """VoxCore must refuse to boot with a placeholder JWT secret."""
    monkeypatch.setenv("JWT_SECRET_KEY", insecure)
    import voxcore.config as cfg

    importlib.reload(cfg)
    with pytest.raises(Exception, match="JWT_SECRET_KEY"):
        cfg.Settings()


def test_short_jwt_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "too-short")
    import voxcore.config as cfg

    importlib.reload(cfg)
    with pytest.raises(Exception, match="at least 32 characters"):
        cfg.Settings()


def test_allowed_origins_defaults_to_localhost() -> None:
    from voxcore.config import get_settings

    # Settings is cached; the session-wide env has a secure key but default origins.
    s = get_settings()
    assert all("localhost" in o or "127.0.0.1" in o for o in s.allowed_origins_list)
