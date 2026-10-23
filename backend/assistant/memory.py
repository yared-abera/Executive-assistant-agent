"""Long-term executive preference memory via Gemini embeddings + Supabase pgvector."""

from __future__ import annotations

import logging
from typing import List

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


def retrieve_relevant_preferences(query: str, limit: int = 3) -> str:
    """Retrieves relevant rules based on semantic similarity."""
    if not supabase_configured():
        return DEFAULT_FALLBACK

    try:
        query_vector = embed_text(query)
        supabase = get_supabase_client()
        rpc_response = supabase.rpc(
            "match_preferences",
            {"query_embedding": query_vector, "match_count": limit},
        ).execute()
        matches = [row["content"] for row in (rpc_response.data or [])]
        return "\n".join(matches) if matches else "No special preferences found."
    except Exception:
        logger.exception("Preference retrieval failed; using fallback rules")
        return DEFAULT_FALLBACK
