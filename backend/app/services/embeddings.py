"""Embeddings: BAAI/bge-small-en-v1.5 via fastembed (ONNX, CPU). One lazy singleton per process."""

import threading
from typing import Protocol

import numpy as np

from app.config import get_settings

QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
BATCH_SIZE = 16


class Embedder(Protocol):
    def embed_passages(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


def _l2_normalize(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vectors / norms


class FastEmbedEmbedder:
    """Blocking (CPU-bound) — call from a thread."""

    def __init__(self, model_name: str, cache_dir: str, dim: int) -> None:
        from fastembed import TextEmbedding

        self._model = TextEmbedding(model_name=model_name, cache_dir=cache_dir)
        self._dim = dim
        self._lock = threading.Lock()  # ONNX session is shared; serialize to bound memory

    def _embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        with self._lock:
            vectors = np.array(list(self._model.embed(texts, batch_size=BATCH_SIZE)), dtype=np.float32)
        vectors = _l2_normalize(vectors)
        if vectors.shape[1] != self._dim:
            raise ValueError(f"Embedding dim {vectors.shape[1]} != configured {self._dim}")
        return vectors.tolist()

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for i in range(0, len(texts), BATCH_SIZE):
            out.extend(self._embed(texts[i : i + BATCH_SIZE]))
        return out

    def embed_query(self, text: str) -> list[float]:
        return self._embed([QUERY_PREFIX + text])[0]


_instance: Embedder | None = None
_instance_lock = threading.Lock()


def get_default_embedder() -> Embedder:
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                s = get_settings()
                _instance = FastEmbedEmbedder(s.EMBEDDING_MODEL, s.EMBEDDING_CACHE_DIR, s.EMBEDDING_DIM)
    return _instance


def set_default_embedder(embedder: Embedder | None) -> None:
    """Test hook: inject a fake embedder."""
    global _instance
    _instance = embedder
