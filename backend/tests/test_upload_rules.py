import hashlib

from app.services.upload import IncomingFile, sanitize_filename, validate_files
from tests.conftest import make_pdf

MB = 1024 * 1024


def run(files, free_slots=500, existing=None, max_files=20):
    existing = existing or {}
    return validate_files(
        files,
        max_files=max_files,
        max_file_bytes=MB,
        max_pages=2,
        free_slots=free_slots,
        find_existing=lambda h: existing.get(h),
    )


def reasons(outcome):
    return {r.filename: r.reason for r in outcome.rejected}


def test_valid_pdf_accepted():
    out = run([IncomingFile("a.pdf", make_pdf())])
    assert len(out.valid) == 1 and not out.rejected


def test_not_a_pdf_renamed():
    out = run([IncomingFile("fake.pdf", b"PK\x03\x04 this is a zip")])
    assert reasons(out) == {"fake.pdf": "not_a_pdf"}


def test_wrong_extension():
    out = run([IncomingFile("a.txt", make_pdf())])
    assert reasons(out) == {"a.txt": "not_a_pdf"}


def test_file_too_large():
    out = run([IncomingFile("big.pdf", b"", oversize=True), IncomingFile("big2.pdf", b"%PDF" + b"0" * (MB + 1))])
    assert reasons(out) == {"big.pdf": "file_too_large", "big2.pdf": "file_too_large"}


def test_corrupted():
    out = run([IncomingFile("bad.pdf", b"%PDF-1.7 garbage garbage")])
    assert reasons(out) == {"bad.pdf": "corrupted_pdf"}


def test_password_protected():
    out = run([IncomingFile("p.pdf", make_pdf(password="secret"))])
    assert reasons(out) == {"p.pdf": "password_protected"}


def test_too_many_pages():
    out = run([IncomingFile("three.pdf", make_pdf(pages=3))])
    assert reasons(out) == {"three.pdf": "too_many_pages"}


def test_duplicate_in_library():
    data = make_pdf()
    h = hashlib.sha256(data).hexdigest()
    out = run([IncomingFile("a.pdf", data)], existing={h: "existing-id"})
    assert out.rejected[0].reason == "duplicate"
    assert out.rejected[0].existing_resume_id == "existing-id"


def test_duplicate_within_request():
    data = make_pdf()
    out = run([IncomingFile("a.pdf", data), IncomingFile("b.pdf", data)])
    assert len(out.valid) == 1
    assert out.rejected[0].reason == "duplicate" and out.rejected[0].existing_resume_id is None


def test_too_many_files():
    files = [IncomingFile(f"f{i}.pdf", make_pdf(text=f"Resume number {i} " * 20)) for i in range(4)]
    out = run(files, max_files=2)
    assert len(out.valid) == 2
    assert [r.reason for r in out.rejected] == ["too_many_files", "too_many_files"]


def test_library_full_accepts_in_order_and_keeps_specific_reasons():
    files = [
        IncomingFile("ok1.pdf", make_pdf(text="first resume " * 30)),
        IncomingFile("bad.pdf", b"not a pdf"),
        IncomingFile("ok2.pdf", make_pdf(text="second resume " * 30)),
        IncomingFile("ok3.pdf", make_pdf(text="third resume " * 30)),
    ]
    out = run(files, free_slots=2)
    assert [v.filename for v in out.valid] == ["ok1.pdf", "ok2.pdf"]
    assert reasons(out) == {"bad.pdf": "not_a_pdf", "ok3.pdf": "library_full"}


def test_sanitize_filename():
    assert sanitize_filename("C:\\Users\\x\\my resume.pdf") == "my resume.pdf"
    assert sanitize_filename("../../etc/passwd.pdf") == "passwd.pdf"
    assert len(sanitize_filename("a" * 300 + ".pdf")) == 200
