"""Load PatchPilot settings without printing secret values."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    ai_provider: str
    gemini_model: str
    gemini_api_key: str | None
    gemini_request_timeout_ms: int
    test_timeout_seconds: int


def _positive_int(name: str, default: int, *, maximum: int) -> int:
    value = os.getenv(name, str(default))
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a whole number") from exc
    if parsed < 1 or parsed > maximum:
        raise ValueError(f"{name} must be between 1 and {maximum}")
    return parsed


def load_settings() -> Settings:
    """Load .env values while preserving existing process environment values."""
    load_dotenv()
    provider = os.getenv("AI_PROVIDER", "gemini").strip().lower()
    if provider != "gemini":
        raise ValueError("AI_PROVIDER must be 'gemini'")
    model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()
    if not model:
        raise ValueError("GEMINI_MODEL must not be empty")
    key = os.getenv("GEMINI_API_KEY", "").strip() or None
    return Settings(
        ai_provider=provider,
        gemini_model=model,
        gemini_api_key=key,
        gemini_request_timeout_ms=_positive_int(
            "GEMINI_REQUEST_TIMEOUT_MS", 90_000, maximum=300_000
        ),
        test_timeout_seconds=_positive_int(
            "TEST_TIMEOUT_SECONDS", 10, maximum=120
        ),
    )
