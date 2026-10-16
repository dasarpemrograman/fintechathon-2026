"""Private content-addressed storage. Access is authorized by document records."""

import hashlib, os
from pathlib import Path
from services.api.settings import settings
from services.api.store import DomainError

MEDIA = {"text/plain", "application/pdf", "image/png", "image/jpeg"}


def store_bytes(content, media_type):
    if not content or len(content) > settings.max_upload_bytes:
        raise DomainError(
            "UPLOAD_SIZE", "Upload must contain 1 byte through 10 MiB.", 413
        )
    if media_type not in MEDIA:
        raise DomainError(
            "UNSUPPORTED_MEDIA", "Allowed types: text, PDF, PNG, JPEG.", 415
        )
    if media_type == "application/pdf" and not content.startswith(b"%PDF-"):
        raise DomainError(
            "MEDIA_MISMATCH", "File signature does not match PDF media type.", 415
        )
    if media_type == "image/png" and not content.startswith(b"\x89PNG\r\n\x1a\n"):
        raise DomainError("MEDIA_MISMATCH", "File signature does not match PNG.", 415)
    if media_type == "image/jpeg" and not content.startswith(b"\xff\xd8"):
        raise DomainError("MEDIA_MISMATCH", "File signature does not match JPEG.", 415)
    if media_type == "text/plain":
        try:
            content.decode("utf-8")
        except UnicodeDecodeError:
            raise DomainError("TEXT_ENCODING", "Text uploads must use UTF-8.", 415)
    digest = hashlib.sha256(content).hexdigest()
    settings.storage.mkdir(parents=True, exist_ok=True)
    path = settings.storage / digest
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
    except FileExistsError:
        if path.read_bytes() != content:
            raise DomainError(
                "CONTENT_COLLISION",
                "Stored content failed integrity verification.",
                500,
            )
    return digest


def read_bytes(content_hash):
    if len(content_hash) != 64 or any(
        c not in "0123456789abcdef" for c in content_hash
    ):
        raise DomainError("INVALID_HASH", "Invalid content identity.", 404)
    path = settings.storage / content_hash
    if not path.is_file():
        raise DomainError("FILE_UNAVAILABLE", "Original file is unavailable.", 404)
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != content_hash:
        raise DomainError(
            "CONTENT_CORRUPT", "Original file failed integrity verification.", 500
        )
    return content
