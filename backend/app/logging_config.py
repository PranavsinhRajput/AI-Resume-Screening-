import logging
import sys


def configure_logging(production: bool) -> None:
    """Plain structured-ish logging. Never log resume text, emails or phone numbers (DI-9)."""
    level = logging.INFO
    logging.basicConfig(
        level=level,
        stream=sys.stdout,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    # Third-party HTTP clients log full URLs/bodies at INFO/DEBUG; keep them quiet.
    for noisy in ("httpx", "httpcore", "hpack", "google_genai", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    if not production:
        logging.getLogger("app").setLevel(logging.DEBUG)
