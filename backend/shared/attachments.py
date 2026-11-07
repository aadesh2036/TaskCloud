"""Attachment storage. S3 with pre-signed URLs on AWS, a folder in local dev.

Both backends return a {url, fields} upload shape, so the frontend code is identical.
"""

import mimetypes
import os
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

from shared.store import default_data_dir

URL_EXPIRY_SECONDS = 300
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

# D-017: only these open in the browser. HTML and SVG are left out on purpose, because
# they can run scripts.
_INLINE_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
    "text/plain",
}


def display_settings(key: str) -> tuple[str, str]:
    """Return (content type, content disposition) for serving a stored file."""
    filename = key.rsplit("/", 1)[-1]
    guessed, _ = mimetypes.guess_type(filename)
    if guessed in _INLINE_TYPES:
        return guessed, f'inline; filename="{filename}"'
    return "application/octet-stream", f'attachment; filename="{filename}"'


class S3Attachments:
    def __init__(self, bucket: str):
        import boto3
        from botocore.config import Config

        self._bucket = bucket
        # s3v4 and the regional virtual-hosted URL matter here. The global endpoint can
        # answer a browser POST with a redirect, which fails the CORS check.
        self._s3 = boto3.client(
            "s3",
            region_name=os.environ.get("AWS_REGION", "ap-south-1"),
            config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
        )

    def presign_upload(self, key: str) -> dict:
        post = self._s3.generate_presigned_post(
            Bucket=self._bucket,
            Key=key,
            # The size limit lives in the signed policy, so a browser cannot bypass it.
            Conditions=[["content-length-range", 1, MAX_UPLOAD_BYTES]],
            ExpiresIn=URL_EXPIRY_SECONDS,
        )
        return {"url": post["url"], "fields": post["fields"]}

    def presign_download(self, key: str) -> str:
        content_type, disposition = display_settings(key)
        return self._s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self._bucket,
                "Key": key,
                "ResponseContentType": content_type,
                "ResponseContentDisposition": disposition,
            },
            ExpiresIn=URL_EXPIRY_SECONDS,
        )

    def delete(self, key: str) -> None:
        self._s3.delete_object(Bucket=self._bucket, Key=key)


class LocalAttachments:
    """Stores files under local/.data/uploads. URLs point at the local dev server."""

    def __init__(self, root: Path, base_url: str):
        self._root = root
        self._base_url = base_url.rstrip("/")

    def presign_upload(self, key: str) -> dict:
        return {"url": f"{self._base_url}/local/upload", "fields": {"key": key}}

    def presign_download(self, key: str) -> str:
        return f"{self._base_url}/local/files/{quote(key)}"

    def delete(self, key: str) -> None:
        (self._root / key).unlink(missing_ok=True)


@lru_cache(maxsize=1)
def get_attachments() -> S3Attachments | LocalAttachments:
    if os.environ.get("TASKCLOUD_STORE", "dynamodb") == "local":
        base_url = os.environ.get("TASKCLOUD_LOCAL_BASE_URL", "http://localhost:8787")
        return LocalAttachments(default_data_dir() / "uploads", base_url)
    return S3Attachments(os.environ["ATTACHMENTS_BUCKET"])
