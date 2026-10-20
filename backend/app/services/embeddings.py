"""Embeddings: gemini-embedding-001 via Google GenAI API (768-dim, MRL).

All chunks from a single resume are sent in one batched API call.
Retry logic mirrors the LLM gateway: 429 / 5xx / network errors are retried
with exponential back-off; other API errors are fatal.
"""

import logging
import threading
import time

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from app.config import get_settings

logger = logging.getLogger(__name__)

# Gemini embedding model constants
_EMBEDDING_MODEL = "gemini-embedding-001"

# Retry config (mirrors llm.py approach)
_MAX_ATTEMPTS = 4
_BACKOFF_BASE = 2.0   # seconds; doubles each retry
_BACKOFF_MAX = 30.0   # seconds cap


class EmbeddingError(Exception):
    """Raised when embeddings cannot be produced after retries."""


class Embedder:
    """Protocol-compatible interface; sync methods — call via anyio.to_thread.run_sync."""

    def embed_passages(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...


class GeminiEmbedder:
    """Batched embeddings via gemini-embedding-001.

    All texts are sent in a single API call per invocation (no per-chunk round-trips).
    Thread-safe: the underlying google-genai client is stateless per call.
    """

    def __init__(self, api_key: str, dim: int) -> None:
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required for GeminiEmbedder")
        self._client = genai.Client(api_key=api_key)
        self._dim = dim
        self._config = types.EmbedContentConfig(output_dimensionality=dim)
        self._lock = threading.Lock()  # serialize calls; Gemini client is safe but rate-limit friendly

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of passage texts. Returns one vector per text."""
        cleaned = self._clean(texts)
        if not cleaned:
            return []
        return self._embed_with_retry(cleaned)

    def embed_query(self, text: str) -> list[float]:
        """Embed a single search query."""
        cleaned = self._clean([text])
        if not cleaned:
            raise EmbeddingError("Query text is empty after cleaning.")
        return self._embed_with_retry(cleaned)[0]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _clean(texts: list[str]) -> list[str]:
        """Strip whitespace; replace blank strings with a placeholder so the
        API never receives an empty string (which causes a 400 error)."""
        result = []
        for t in texts:
            stripped = (t or "").strip()
            # Gemini rejects empty strings — use a safe no-op placeholder
            result.append(stripped if stripped else "[empty]")
        return result

    def _call_api(self, texts: list[str]) -> list[list[float]]:
        """Single API call — all texts in one batch request."""
        with self._lock:
            response = self._client.models.embed_content(
                model=_EMBEDDING_MODEL,
                contents=texts,
                config=self._config,
            )

        if not response.embeddings:
            raise EmbeddingError("Gemini returned empty embeddings list.")

        if len(response.embeddings) != len(texts):
            raise EmbeddingError(
                f"Gemini returned {len(response.embeddings)} embeddings for {len(texts)} inputs."
            )

        vectors: list[list[float]] = []
        for i, emb in enumerate(response.embeddings):
            values = list(emb.values)
            if len(values) != self._dim:
                raise EmbeddingError(
                    f"Embedding [{i}] has dim {len(values)}, expected {self._dim}."
                )
            vectors.append(values)

        return vectors

    def _embed_with_retry(self, texts: list[str]) -> list[list[float]]:
        """Call the API with exponential back-off on transient errors."""
        last_exc: Exception | None = None
        delay = _BACKOFF_BASE

        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                return self._call_api(texts)
            except genai_errors.APIError as exc:
                code = getattr(exc, "code", None) or 0
                if code == 429 or code >= 500:
                    # Transient: rate-limited or server error → retry
                    retry_after = _parse_retry_after(exc)
                    wait = max(delay, retry_after or 0.0)
                    logger.warning(
                        "Gemini embedding transient error %s (attempt %d/%d); retrying in %.1fs",
                        code, attempt, _MAX_ATTEMPTS, wait,
                    )
                    time.sleep(min(wait, _BACKOFF_MAX))
                    delay = min(delay * 2, _BACKOFF_MAX)
                    last_exc = exc
                else:
                    # Non-retryable API error (400 bad request, 403 auth, etc.)
                    logger.error("Gemini embedding non-retryable error %s: %s", code, exc)
                    raise EmbeddingError(f"Gemini embedding API error {code}") from exc
            except (ConnectionError, OSError, TimeoutError) as exc:
                logger.warning(
                    "Gemini embedding network error %s (attempt %d/%d); retrying in %.1fs",
                    type(exc).__name__, attempt, _MAX_ATTEMPTS, delay,
                )
                time.sleep(min(delay, _BACKOFF_MAX))
                delay = min(delay * 2, _BACKOFF_MAX)
                last_exc = exc

        raise EmbeddingError(
            f"Gemini embedding failed after {_MAX_ATTEMPTS} attempts"
        ) from last_exc


# ------------------------------------------------------------------
# Retry-after header parser
# ------------------------------------------------------------------

import re as _re

_RETRY_RE = _re.compile(r"retry(?:Delay|_delay)?['\"]?\s*[:=]\s*['\"]?(\d+(?:\.\d+)?)s", _re.I)


def _parse_retry_after(exc: Exception) -> float | None:
    match = _RETRY_RE.search(str(exc))
    if match:
        try:
            return min(float(match.group(1)), 60.0)
        except ValueError:
            return None
    return None


# ------------------------------------------------------------------
# Singleton
# ------------------------------------------------------------------

_instance: GeminiEmbedder | None = None
_instance_lock = threading.Lock()


def get_default_embedder() -> GeminiEmbedder:
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                s = get_settings()
                _instance = GeminiEmbedder(s.GEMINI_API_KEY, s.EMBEDDING_DIM)
                logger.info(
                    "GeminiEmbedder ready (model=%s, dim=%d)", _EMBEDDING_MODEL, s.EMBEDDING_DIM
                )
    return _instance


def set_default_embedder(embedder: GeminiEmbedder | None) -> None:
    """Test hook: inject a fake embedder."""
    global _instance
    _instance = embedder
