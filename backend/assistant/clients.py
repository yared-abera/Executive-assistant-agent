"""Lazy external API clients — safe to import without env vars set."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from google import genai


class ConfigurationError(RuntimeError):
    """Raised when a required API credential is missing."""


@lru_cache(maxsize=1)
def get_gemini_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or api_key.startswith("your_"):
        raise ConfigurationError(
            "GEMINI_API_KEY is missing. Create a free key at https://ai.google.dev "
            "and set GEMINI_API_KEY in .env"
        )
    return genai.Client(api_key=api_key)


@lru_cache(maxsize=1)
def get_supabase_client() -> Any:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key or "your-project" in url:
        raise ConfigurationError(
            "SUPABASE_URL / SUPABASE_KEY are missing or still placeholders. "
            "Create a free Supabase project and update .env"
        )
    from supabase import create_client

    return create_client(url, key)


def gemini_configured() -> bool:
    key = os.environ.get("GEMINI_API_KEY", "")
    return bool(key) and not key.startswith("your_")


def supabase_configured() -> bool:
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_KEY", "")
    return bool(url and key) and "your-project" not in url


def google_calendar_configured() -> bool:
    return all(
        os.environ.get(name)
        for name in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN")
    )


def calendar_mode() -> str:
    """mock | google | auto — controls whether Google Calendar is attempted."""
    mode = (os.environ.get("CALENDAR_MODE") or "auto").strip().lower()
    if mode not in ("mock", "google", "auto"):
        return "auto"
    return mode


def use_google_calendar() -> bool:
    """True when Google Calendar API calls should be attempted."""
    if calendar_mode() == "mock":
        return False
    return google_calendar_configured()


def resend_configured() -> bool:
    key = os.environ.get("RESEND_API_KEY", "")
    return bool(key) and key.startswith("re_")


# Back-compat alias used by older call sites / docs
def email_configured() -> bool:
    return resend_configured()
