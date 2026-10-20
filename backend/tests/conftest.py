"""Shared fixtures. Fixture PDFs are generated with PyMuPDF at test time (see tests/fixtures/README.md)."""

import os

import pymupdf
import pytest

SAMPLE_TEXT = (
    "Jane Doe\njane@example.com  +91 98765 43210\nPune, India\n\n"
    "Senior Machine Learning Engineer\n"
    "Experience\nACME Corp — ML Engineer, Jan 2021 – Present\n"
    "Built and deployed NLP models with Python, PyTorch and FastAPI on AWS.\n"
    "Led a team of 4 engineers.\n\n"
    "Skills: Python, PyTorch, FastAPI, NLP, SQL, Docker\n"
    "Education: B.Tech Computer Science, Pune University 2016-2020\n"
)


def make_pdf(pages: int = 1, text: str = SAMPLE_TEXT, password: str | None = None) -> bytes:
    doc = pymupdf.open()
    for i in range(pages):
        page = doc.new_page()
        page.insert_text((72, 72), f"{text}\nPage {i + 1}", fontsize=10)
    if password:
        data = doc.tobytes(
            encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw=password, user_pw=password
        )
    else:
        data = doc.tobytes()
    doc.close()
    return data


def make_image_only_pdf() -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    page.draw_rect(pymupdf.Rect(50, 50, 300, 300), color=(0, 0, 0), fill=(0.5, 0.5, 0.5))
    data = doc.tobytes()
    doc.close()
    return data


@pytest.fixture
def pdf_bytes() -> bytes:
    return make_pdf()


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    # Keep unit tests independent of any local .env
    monkeypatch.setenv("GEMINI_API_KEY", "")
    os.environ.setdefault("ENV", "test")
