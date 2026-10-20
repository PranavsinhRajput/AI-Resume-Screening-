"""Supabase Storage access. Object paths are always `{owner_id}/{resume_id}.pdf` (DI-4)."""

from supabase import Client


def object_path(owner_id: str, resume_id: str) -> str:
    return f"{owner_id}/{resume_id}.pdf"


def _assert_owned(owner_id: str, path: str) -> None:
    if not path.startswith(f"{owner_id}/"):
        raise PermissionError("Storage path does not belong to owner")


def upload_pdf(client: Client, bucket: str, owner_id: str, resume_id: str, data: bytes) -> str:
    path = object_path(owner_id, resume_id)
    client.storage.from_(bucket).upload(
        path, data, {"content-type": "application/pdf", "upsert": "false"}
    )
    return path


def download_pdf(client: Client, bucket: str, owner_id: str, path: str) -> bytes:
    _assert_owned(owner_id, path)
    return client.storage.from_(bucket).download(path)


def delete_object(client: Client, bucket: str, owner_id: str, path: str) -> None:
    _assert_owned(owner_id, path)
    client.storage.from_(bucket).remove([path])


def signed_url(client: Client, bucket: str, owner_id: str, path: str, ttl_seconds: int) -> str:
    _assert_owned(owner_id, path)
    res = client.storage.from_(bucket).create_signed_url(path, ttl_seconds)
    url = None
    if isinstance(res, dict):
        url = res.get("signedURL") or res.get("signedUrl") or res.get("signed_url")
    else:
        url = getattr(res, "signed_url", None) or getattr(res, "signedURL", None)
    if not url:
        raise RuntimeError("Could not create signed URL")
    return url
