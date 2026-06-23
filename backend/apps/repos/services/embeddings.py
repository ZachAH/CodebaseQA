"""Embedding generation — pluggable provider.

Default is "local": fastembed runs the model on-device (ONNX, CPU), so there's
no API, no key, and nothing that can ever require a payment method. Set
EMBED_PROVIDER=voyage to use Voyage's code-specialized model instead (needs a
Voyage key + card on file).

Note: the local model downloads once (~130 MB) on first use, so the first
indexing run pauses while it fetches; every run after that is fast.
"""
from __future__ import annotations

from functools import lru_cache

from django.conf import settings


# --- Local provider (fastembed) ---


@lru_cache(maxsize=1)
def _local_model():
    from fastembed import TextEmbedding

    return TextEmbedding(model_name=settings.LOCAL_EMBED_MODEL)


def _embed_local(texts: list[str]) -> list[list[float]]:
    # fastembed batches internally and yields one numpy vector per input.
    return [vector.tolist() for vector in _local_model().embed(texts)]


# --- Voyage provider ---


@lru_cache(maxsize=1)
def _voyage_client():
    import voyageai

    if not settings.VOYAGE_API_KEY:
        raise RuntimeError(
            "VOYAGE_API_KEY is not set. Add it to backend/.env, or set "
            "EMBED_PROVIDER=local to embed on-device with no key."
        )
    return voyageai.Client(api_key=settings.VOYAGE_API_KEY)


def _embed_voyage(texts: list[str], input_type: str) -> list[list[float]]:
    client = _voyage_client()
    vectors: list[list[float]] = []
    for start in range(0, len(texts), 64):
        batch = texts[start : start + 64]
        result = client.embed(
            batch, model=settings.VOYAGE_EMBED_MODEL, input_type=input_type
        )
        vectors.extend(result.embeddings)
    return vectors


# --- Public API ---


def embed_documents(texts: list[str]) -> list[list[float]]:
    """Embed code chunks for storage."""
    if settings.EMBED_PROVIDER == "voyage":
        return _embed_voyage(texts, "document")
    return _embed_local(texts)


def embed_query(text: str) -> list[float]:
    """Embed a user question for retrieval."""
    if settings.EMBED_PROVIDER == "voyage":
        return _embed_voyage([text], "query")[0]
    return _embed_local([text])[0]
