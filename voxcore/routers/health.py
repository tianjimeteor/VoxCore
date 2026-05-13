"""Health check endpoint."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["meta"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}


@router.get("/")
def root() -> dict[str, str]:
    return {"name": "VoxCore", "docs": "/docs"}
