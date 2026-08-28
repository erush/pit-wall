from __future__ import annotations

import os
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIST = REPO_ROOT / "dist"


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip().rstrip("/") for item in value.split(",") if item.strip()]


def cors_origins() -> list[str]:
    origins = _split_csv(os.getenv("PITWALL_CORS_ORIGINS"))
    render_origin = os.getenv("RENDER_EXTERNAL_URL")
    if render_origin:
        origins.append(render_origin.rstrip("/"))
    if origins:
        return sorted(set(origins))
    return [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]


def cors_allow_credentials() -> bool:
    return os.getenv("PITWALL_CORS_ALLOW_CREDENTIALS", "false").lower() == "true"
