"""Cache key includes tenant, parser/model version and demo/real scope."""

import sqlalchemy as sa
from migrations.schema_v6 import extractions
from services.api.store import digest, DomainError
import importlib.metadata, json, subprocess
from services.api.settings import ROOT

try:
    ocr_version = (
        subprocess.check_output(
            ["tesseract", "--version"], text=True, stderr=subprocess.DEVNULL, timeout=2
        )
        .splitlines()[0]
        .replace(" ", "-")
    )
except (OSError, subprocess.SubprocessError):
    ocr_version = "ocr-unavailable"
model_commit = json.loads((ROOT / "fixtures/demo/ocr-assets.lock.json").read_text())[
    "commit"
]
VERSION = (
    "extract-2;pypdf-"
    + importlib.metadata.version("pypdf")
    + ";pillow-"
    + importlib.metadata.version("pillow")
    + ";"
    + ocr_version
    + ";tessdata-"
    + model_commit
)


def lookup(conn, tenant, content_hash, scope):
    row = (
        conn.execute(
            sa.select(extractions).where(
                extractions.c.tenant_id == tenant,
                extractions.c.content_hash == content_hash,
                extractions.c.parser_version == VERSION,
                extractions.c.scope == scope,
            )
        )
        .mappings()
        .first()
    )
    if row and digest(row["pages"]) != row["result_hash"]:
        raise DomainError(
            "EXTRACTION_CACHE_INTEGRITY", "Cached extraction integrity failed."
        )
    return row


def remember(conn, tenant, content_hash, scope, pages):
    conn.execute(
        extractions.insert().values(
            tenant_id=tenant,
            content_hash=content_hash,
            parser_version=VERSION,
            scope=scope,
            pages=pages,
            page_count=len(pages),
            result_hash=digest(pages),
        )
    )
