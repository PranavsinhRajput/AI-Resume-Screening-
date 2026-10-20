"""Skill normalization, used on both resume skills (ingestion) and query required_skills (search)."""

import re

SKILL_ALIASES: dict[str, str] = {
    "ml": "machine learning",
    "dl": "deep learning",
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "reactjs": "react",
    "react.js": "react",
    "node": "node.js",
    "nodejs": "node.js",
    "expressjs": "express",
    "k8s": "kubernetes",
    "postgres": "postgresql",
    "mongo": "mongodb",
    "gcp": "google cloud",
    "nlp": "natural language processing",
    "cv": "computer vision",
    "llms": "llm",
    "genai": "generative ai",
    "sklearn": "scikit-learn",
    "tf": "tensorflow",
    "c plus plus": "c++",
    "c sharp": "c#",
}

MAX_SKILL_LEN = 60
_WS = re.compile(r"\s+")


def normalize_skill(s: str) -> str:
    s = _WS.sub(" ", (s or "").strip().lower())
    s = s.rstrip(".,;: ").strip()
    return SKILL_ALIASES.get(s, s)


def normalize_skills(skills: list[str]) -> list[str]:
    """Normalize, drop empty/over-long entries, dedupe preserving order."""
    out: list[str] = []
    seen: set[str] = set()
    for raw in skills or []:
        if not isinstance(raw, str):
            continue
        s = normalize_skill(raw)
        if not s or len(s) > MAX_SKILL_LEN or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out
