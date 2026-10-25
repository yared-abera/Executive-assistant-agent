"""Long-term executive preference memory via Gemini embeddings + Supabase pgvector."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import List, Optional

from google.genai import types

from .clients import (
    ConfigurationError,
    get_gemini_client,
    get_supabase_client,
    supabase_configured,
)

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIM = 768
DEFAULT_FALLBACK = (
    "Standard business hours: 9 AM - 5 PM. No meetings before 10 AM when possible. "
    "15-minute buffer between meetings."
)


def _extract_embedding_values(response) -> List[float]:
    if getattr(response, "embeddings", None):
        emb = response.embeddings[0]
        values = getattr(emb, "values", None)
        if values:
            return list(values)
    embedding = getattr(response, "embedding", None)
    if embedding is not None:
        values = getattr(embedding, "values", None)
        if values:
            return list(values)
    raise ValueError("Unexpected embedding response shape from Gemini")


def embed_text(text: str) -> List[float]:
    client = get_gemini_client()
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIM),
    )
    return _extract_embedding_values(response)


def store_preference(content: str) -> str:
    """Embeds an executive rule/preference and stores it in Supabase pgvector."""
    if not content or not content.strip():
        raise ValueError("Preference content is empty")

    try:
        embedding = embed_text(content.strip())
    except ConfigurationError as exc:
        raise ConfigurationError(str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to embed preference")
        raise RuntimeError(f"Embedding failed: {exc}") from exc

    if not supabase_configured():
        return (
            f"[Simulated store — configure SUPABASE_URL/KEY] Preference noted: '{content.strip()}'"
        )

    try:
        supabase = get_supabase_client()
        supabase.table("executive_preferences").insert(
            {"content": content.strip(), "embedding": embedding}
        ).execute()
        return f"Stored preference: '{content.strip()}'"
    except Exception as exc:
        logger.exception("Failed to store preference in Supabase")
        raise RuntimeError(f"Supabase store failed: {exc}") from exc


def _list_preference_contents(limit: int = 20) -> List[str]:
    """Direct table read — reliable when the table is small (IVFFlat needs many rows)."""
    supabase = get_supabase_client()
    listed = (
        supabase.table("executive_preferences")
        .select("content")
        .limit(limit)
        .execute()
    )
    return [row["content"] for row in (listed.data or []) if row.get("content")]


def retrieve_relevant_preferences(query: str, limit: int = 5) -> str:
    """Retrieves executive rules for the agent system prompt.

    Combines pgvector similarity with a direct table listing so rules still
    surface when the IVFFlat index returns no neighbors on a tiny dataset.
    """
    if not supabase_configured():
        return DEFAULT_FALLBACK

    try:
        supabase = get_supabase_client()
        listed = _list_preference_contents(limit=20)

        vector_hits: List[str] = []
        try:
            query_vector = embed_text(query)
            rpc_response = supabase.rpc(
                "match_preferences",
                {"query_embedding": query_vector, "match_count": limit},
            ).execute()
            vector_hits = [
                row["content"]
                for row in (rpc_response.data or [])
                if row.get("content")
            ]
        except Exception:
            logger.exception("Vector preference match failed; using listed preferences")

        merged: List[str] = []
        for content in vector_hits + listed:
            if content not in merged:
                merged.append(content)

        if not merged:
            return "No special preferences found."
        return "\n".join(merged)
    except Exception:
        logger.exception("Preference retrieval failed; using fallback rules")
        return DEFAULT_FALLBACK


_WEEKDAY_BAN_MARKERS = (
    "no meeting",
    "no meetings",
    "avoid meeting",
    "avoid meetings",
    "don't schedule",
    "do not schedule",
    "dont schedule",
    "never schedule",
    "never book",
)


def date_blocked_by_preferences(date_str: str, preferences_text: str) -> Optional[str]:
    """If preferences ban meetings on that calendar weekday, return a user-facing reason."""
    if not preferences_text or preferences_text.startswith("No special"):
        return None
    try:
        weekday = datetime.strptime(date_str, "%Y-%m-%d").strftime("%A")
    except ValueError:
        return None

    weekday_l = weekday.lower()
    for line in preferences_text.splitlines():
        line_l = line.lower()
        if weekday_l not in line_l and not re.search(rf"\b{weekday_l[:3]}\b", line_l):
            continue
        if any(marker in line_l for marker in _WEEKDAY_BAN_MARKERS):
            rule = line.strip()
            return (
                f'You set a preference: "{rule}". '
                f"{weekday} is not available for scheduling. "
                "Choose another weekday, or delete this preference in Preferences "
                f"if you want to allow {weekday}s."
            )
    return None


def list_preferences(limit: int = 50) -> List[dict]:
    """Return saved preferences as [{id, content}, ...]."""
    if not supabase_configured():
        return []
    supabase = get_supabase_client()
    listed = (
        supabase.table("executive_preferences")
        .select("id,content")
        .limit(limit)
        .execute()
    )
    items = []
    for row in listed.data or []:
        if row.get("id") is None or not row.get("content"):
            continue
        items.append({"id": int(row["id"]), "content": row["content"]})
    return items


def delete_preference(preference_id: int) -> str:
    """Delete a preference row by id."""
    if not supabase_configured():
        raise ConfigurationError(
            "SUPABASE_URL / SUPABASE_KEY are required to delete preferences."
        )
    supabase = get_supabase_client()
    result = (
        supabase.table("executive_preferences")
        .delete()
        .eq("id", preference_id)
        .execute()
    )
    deleted = result.data or []
    if not deleted:
        raise ValueError(f"Preference id={preference_id} not found")
    content = deleted[0].get("content", "")
    return f"Deleted preference: '{content}'"
