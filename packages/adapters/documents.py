"""Bounded extraction returns candidates, never accepted facts or instructions."""

from pathlib import Path
from tempfile import TemporaryDirectory
import os, re, resource, subprocess, sys, json
from services.api.settings import ROOT
from services.api.store import DomainError


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (768 * 1024 * 1024, 768 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_CPU, (25, 25))
    resource.setrlimit(resource.RLIMIT_FSIZE, (8 * 1024 * 1024, 8 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def extract(content, media_type):
    with TemporaryDirectory() as directory:
        path = Path(directory) / "source"
        path.write_bytes(content)
        path.chmod(0o600)
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "LANG": "C.UTF-8",
            "PYTHONPATH": str(ROOT),
            "TESSDATA_PREFIX": os.environ.get(
                "ALLEXPORT_TESSDATA_PATH", str(ROOT / ".local/tessdata")
            ),
        }
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "packages.adapters.extract_runner",
                    str(path),
                    media_type,
                ],
                capture_output=True,
                text=True,
                cwd=ROOT,
                env=env,
                preexec_fn=limits,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            raise DomainError(
                "EXTRACTION_TIME_LIMIT",
                "Document extraction exceeded its 30-second processing limit; the original is preserved.",
            )
        try:
            value = json.loads(result.stdout)
        except ValueError:
            raise DomainError(
                "EXTRACTION_FAILED",
                "Document processor exceeded limits or returned invalid output.",
            )
        if result.returncode or "error" in value:
            raise DomainError(
                "EXTRACTION_REVIEW_REQUIRED",
                value.get("error", "Document processing failed."),
            )
        for page in value["pages"]:
            if len(page["text"]) > 200000:
                raise DomainError(
                    "TEXT_LIMIT", "Extracted page exceeds 200000 characters."
                )
        return value["pages"]


def candidates(pages, max_candidates=500):
    result = []
    for page in pages:
        text = page["text"]
        language = (
            "zh"
            if re.search(r"[\u4e00-\u9fff]", text)
            else "id"
            if re.search(r"(?i)jumlah|pembayaran|harga", text)
            else "en"
            if re.search(r"(?i)quantity|price|payment", text)
            else "und"
        )
        patterns = [
            ("amount", r"\b(USD|EUR|IDR|CNY|SGD|JPY)\s*([0-9]+(?:\.[0-9]+)?)\b"),
            ("quantity", r"\b([0-9]+(?:\.[0-9]+)?)\s*(kg|tonne|units|pieces)\b"),
            ("payment_terms", r"(?i)\bnet\s*[0-9]+\b"),
        ]
        for kind, pattern in patterns:
            for match in re.finditer(pattern, text):
                value = {
                    "text": None,
                    "decimal": None,
                    "boolean": None,
                    "unit": None,
                    "status": "unreviewed",
                    "reason": None,
                }
                if kind == "amount":
                    value.update(decimal=match.group(2), unit=match.group(1))
                elif kind == "quantity":
                    value.update(decimal=match.group(1), unit=match.group(2))
                else:
                    value.update(
                        text=match.group(0),
                        reason="Payment anchor is unresolved; no due date inferred.",
                    )
                if len(result) >= max_candidates:
                    return result
                result.append(
                    {
                        "field_path": "/extracted/" + kind,
                        "value": value,
                        "locator": page["locator"]
                        + "; chars "
                        + str(match.start())
                        + ":"
                        + str(match.end()),
                        "original_language": language,
                        "original_text": match.group(0),
                        "translated_text": None,
                    }
                )
        if re.search(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b|[¥￥]", text):
            if len(result) >= max_candidates:
                return result
            result.append(
                {
                    "field_path": "/extracted/ambiguity",
                    "value": {
                        "text": text[:2000],
                        "decimal": None,
                        "boolean": None,
                        "unit": None,
                        "status": "unreviewed",
                        "reason": "Ambiguous date/currency requires source-language review.",
                    },
                    "locator": page["locator"],
                    "original_language": language,
                    "original_text": text[:2000],
                    "translated_text": None,
                }
            )
    return result
