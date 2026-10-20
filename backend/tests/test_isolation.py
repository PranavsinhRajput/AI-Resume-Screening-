"""Two-user isolation test (project.md §9). Integration: needs a dedicated TEST Supabase project.

Set TEST_SUPABASE_URL and TEST_SUPABASE_SERVICE_ROLE_KEY (migration already applied). Skipped otherwise.
Uses a fake embedder and fake LLM so no Gemini key or model download is needed.
"""

import hashlib
import os
import uuid

import numpy as np
import pytest

TEST_URL = os.getenv("TEST_SUPABASE_URL")
TEST_KEY = os.getenv("TEST_SUPABASE_SERVICE_ROLE_KEY")

pytestmark = pytest.mark.skipif(not (TEST_URL and TEST_KEY), reason="TEST_SUPABASE_* not configured")


class FakeEmbedder:
    dim = 384

    def _vec(self, text: str) -> list[float]:
        seed = int(hashlib.sha256(text.lower().encode()).hexdigest()[:8], 16)
        v = np.random.default_rng(seed).standard_normal(self.dim).astype(np.float32)
        return (v / np.linalg.norm(v)).tolist()

    def embed_passages(self, texts):
        return [self._vec(t) for t in texts]

    def embed_query(self, text):
        return self._vec(text)


class FakeLLM:
    async def generate_json(self, system, user, schema, response_schema=None):
        from app.schemas.extraction import ResumeExtraction
        from app.schemas.search import ParsedQuery
        from app.services.llm import LLMUnavailable

        if schema is ResumeExtraction:
            return ResumeExtraction(
                headline="ML Engineer",
                summary="Machine learning engineer building NLP systems.",
                skills=["Python", "NLP"],
                experiences=[{"company": "ACME", "title": "ML Engineer", "start_date": "2021-01",
                              "is_current": True, "description": "Built NLP models."}],
            )
        if schema is ParsedQuery:
            return ParsedQuery(semantic_query="machine learning engineer nlp")
        raise LLMUnavailable("verify disabled in tests")


@pytest.fixture(scope="module")
def env():
    os.environ["SUPABASE_URL"] = TEST_URL or ""
    os.environ["SUPABASE_SERVICE_ROLE_KEY"] = TEST_KEY or ""
    os.environ["FRONTEND_ORIGINS"] = "http://localhost"
    from app.config import get_settings

    get_settings.cache_clear()
    from supabase import create_client

    admin = create_client(TEST_URL, TEST_KEY)
    users = {}
    for label in ("a", "b"):
        email = f"iso-{label}-{uuid.uuid4().hex[:8]}@example.test"
        password = uuid.uuid4().hex
        created = admin.auth.admin.create_user({"email": email, "password": password, "email_confirm": True})
        login_client = create_client(TEST_URL, TEST_KEY)
        session = login_client.auth.sign_in_with_password({"email": email, "password": password}).session
        # New sign-ups are pending until an admin approves them (migration 002).
        admin.table("profiles").upsert({"id": created.user.id, "email": email, "status": "approved"}).execute()
        users[label] = {"id": created.user.id, "token": session.access_token}
    yield admin, users
    for u in users.values():
        try:
            admin.auth.admin.delete_user(u["id"])
        except Exception:
            pass


@pytest.fixture(scope="module")
def client(env):
    from fastapi.testclient import TestClient

    from app.deps import get_embedder, get_llm
    from app.main import app

    app.dependency_overrides[get_embedder] = lambda: FakeEmbedder()
    app.dependency_overrides[get_llm] = lambda: FakeLLM()
    # Do not enter lifespan (no background worker); we process resumes explicitly.
    return TestClient(app)


def _h(token):
    return {"Authorization": f"Bearer {token}"}


async def _process_all(admin, owner_id):
    from app.config import get_settings
    from app.services.ingestion import process_resume

    rows = admin.table("resumes").select("*").eq("owner_id", owner_id).eq("status", "pending").execute().data
    for row in rows:
        await process_resume(row, client=admin, settings=get_settings(), llm=FakeLLM(), embedder=FakeEmbedder())


async def test_two_user_isolation(env, client):
    from tests.conftest import make_pdf

    admin, users = env
    a, b = users["a"], users["b"]
    same = make_pdf(text="Machine learning engineer NLP Python " * 20)
    b_only = make_pdf(text="Frontend developer React CSS " * 20)

    ra = client.post("/resumes", headers=_h(a["token"]), files=[("files", ("same.pdf", same, "application/pdf"))])
    assert ra.status_code == 202 and len(ra.json()["accepted"]) == 1
    a_id = ra.json()["accepted"][0]["resume_id"]

    # (5) identical file accepted for B too
    rb = client.post(
        "/resumes",
        headers=_h(b["token"]),
        files=[("files", ("same.pdf", same, "application/pdf")), ("files", ("b.pdf", b_only, "application/pdf"))],
    )
    assert rb.status_code == 202 and len(rb.json()["accepted"]) == 2, rb.json()
    b_ids = {x["resume_id"] for x in rb.json()["accepted"]}

    await _process_all(admin, a["id"])
    await _process_all(admin, b["id"])

    # (1) B cannot access A's resume
    for method, path in [
        ("get", f"/resumes/{a_id}"),
        ("get", f"/resumes/{a_id}/download-url"),
        ("post", f"/resumes/{a_id}/retry"),
        ("delete", f"/resumes/{a_id}"),
    ]:
        assert getattr(client, method)(path, headers=_h(b["token"])).status_code == 404

    listed = {r["id"] for r in client.get("/resumes", headers=_h(b["token"])).json()["items"]}
    assert a_id not in listed and listed == b_ids
    assert client.get("/resumes/stats", headers=_h(b["token"])).json()["total"] == 2
    assert client.get("/resumes/stats", headers=_h(a["token"])).json()["total"] == 1

    # (2) B's search never returns A's resume
    res = client.post("/search", headers=_h(b["token"]), json={"query": "machine learning engineer nlp"})
    assert res.status_code == 200, res.json()
    assert all(r["resume_id"] in b_ids for r in res.json()["results"])

    # (3) signed URL only for A
    url = client.get(f"/resumes/{a_id}/download-url", headers=_h(a["token"]))
    assert url.status_code == 200 and url.json()["url"]

    # (4) deleting A's resume removes its file, experiences, chunks; B untouched
    assert client.delete(f"/resumes/{a_id}", headers=_h(a["token"])).status_code == 204
    assert not admin.table("experiences").select("id").eq("resume_id", a_id).execute().data
    assert not admin.table("resume_chunks").select("id").eq("resume_id", a_id).execute().data
    a_files = admin.storage.from_("resumes").list(a["id"])
    assert not any(f.get("name") == f"{a_id}.pdf" for f in a_files)
    assert client.get("/resumes/stats", headers=_h(b["token"])).json()["total"] == 2
    b_chunks = admin.table("resume_chunks").select("id").eq("owner_id", b["id"]).execute().data
    assert b_chunks
