from app.schemas.extraction import ResumeExtraction
from app.services.chunking import MAX_CHUNKS, build_chunks, scrub_pii, window_words


def _extraction(**kw) -> ResumeExtraction:
    base = {
        "candidate_name": "Jane Doe",
        "email": "jane@example.com",
        "phone": "+91 98765 43210",
        "links": {"linkedin": "https://linkedin.com/in/jane"},
        "headline": "ML Engineer",
        "summary": "Machine learning engineer focused on NLP systems in production.",
        "skills": ["Python"],
        "experiences": [
            {
                "company": "ACME",
                "title": "ML Engineer",
                "employment_type": "full_time",
                "start_date": "2021-01",
                "end_date": None,
                "is_current": True,
                "description": "Built and deployed NLP models with PyTorch on AWS.",
            }
        ],
        "projects": [{"name": "Chatbot", "description": "Built a retrieval chatbot", "technologies": ["LangChain"]}],
        "education": [{"institution": "Pune University", "degree": "B.Tech", "field_of_study": "CS"}],
        "certifications": ["AWS Certified Machine Learning Specialty"],
    }
    base.update(kw)
    return ResumeExtraction.model_validate(base)


def test_structured_chunks_have_no_pii():
    chunks = build_chunks(_extraction(), ["python"], "")
    joined = " ".join(c["content"] for c in chunks)
    assert "Jane Doe" not in joined
    assert "jane@example.com" not in joined
    assert "98765" not in joined
    assert "linkedin.com" not in joined
    sections = {c["section"] for c in chunks}
    assert {"summary", "experience", "project", "education", "certification"} <= sections


def test_raw_windows_strip_pii():
    raw = "Contact jane@example.com or +91 98765 43210 visit https://jane.dev " + "word " * 30
    chunks = build_chunks(_extraction(), ["python"], raw)
    raw_chunks = [c for c in chunks if c["section"] == "raw"]
    assert raw_chunks
    text = " ".join(c["content"] for c in raw_chunks)
    assert "@" not in text and "98765" not in text and "https" not in text


def test_scrub_pii():
    assert "@" not in scrub_pii("mail me at a.b@c.io now")


def test_window_size_and_overlap():
    words = [f"w{i}" for i in range(600)]
    windows = window_words(" ".join(words), size=250, overlap=40)
    assert all(len(w.split()) <= 250 for w in windows)
    first, second = windows[0].split(), windows[1].split()
    assert first[-40:] == second[:40]
    assert windows[-1].split()[-1] == "w599"


def test_max_chunk_count():
    raw = " ".join(f"w{i}" for i in range(20000))
    chunks = build_chunks(_extraction(), ["python"], raw)
    assert len(chunks) <= MAX_CHUNKS
    assert chunks[0]["section"] != "raw"  # structured kept first
    assert [c["chunk_index"] for c in chunks] == list(range(len(chunks)))
