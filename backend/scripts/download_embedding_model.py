"""Download the embedding model weights into EMBEDDING_CACHE_DIR (run at Render build time)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastembed import TextEmbedding  # noqa: E402

from app.config import get_settings  # noqa: E402


def main() -> None:
    s = get_settings()
    model = TextEmbedding(model_name=s.EMBEDDING_MODEL, cache_dir=s.EMBEDDING_CACHE_DIR)
    vec = next(iter(model.embed(["warm up"])))
    print(f"Downloaded {s.EMBEDDING_MODEL} to {s.EMBEDDING_CACHE_DIR} (dim={len(vec)})")


if __name__ == "__main__":
    main()
