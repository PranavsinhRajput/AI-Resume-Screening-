from app.services.skills import normalize_skill, normalize_skills


def test_aliases():
    assert normalize_skill("ML") == "machine learning"
    assert normalize_skill("React.js") == "react"
    assert normalize_skill("k8s") == "kubernetes"
    assert normalize_skill("Postgres") == "postgresql"
    assert normalize_skill("AWS") == "aws"


def test_whitespace_and_trailing_punctuation():
    assert normalize_skill("  Machine   Learning. ") == "machine learning"
    assert normalize_skill("python,") == "python"


def test_dedupe_preserves_order_and_drops_bad():
    out = normalize_skills(["Python", "py", "", "React", "reactjs", "x" * 61, "SQL"])
    assert out == ["python", "react", "sql"]


def test_symmetry_resume_vs_query():
    resume = normalize_skills(["NodeJS", "Sklearn", "C Sharp"])
    query = normalize_skills(["node", "scikit-learn", "c#"])
    assert set(query) <= set(resume)
