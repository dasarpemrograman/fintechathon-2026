"""Bounded public HTTPS retrieval, retaining inherited proxies and TLS trust."""

from datetime import datetime, timezone
import hashlib, ipaddress, socket, time
from urllib.parse import urlsplit, urljoin, urlunsplit
from contextlib import ExitStack
import httpx
from services.api.store import DomainError
from packages.adapters.pinned_transport import PinnedTransport


def destination(url):
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError:
        raise DomainError("FETCH_URL_BLOCKED", "Malformed source URL.")
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or port not in (None, 443)
    ):
        raise DomainError(
            "FETCH_URL_BLOCKED",
            "Only public HTTPS source URLs without credentials are permitted.",
        )
    try:
        addresses = {
            item[4][0]
            for item in socket.getaddrinfo(
                parsed.hostname, 443, type=socket.SOCK_STREAM
            )
        }
    except socket.gaierror:
        raise DomainError(
            "SOURCE_DNS_UNAVAILABLE", "Source hostname could not be resolved.", 503
        )
    if not addresses or any(
        not ipaddress.ip_address(address).is_global for address in addresses
    ):
        raise DomainError(
            "FETCH_ADDRESS_BLOCKED",
            "Private, loopback, link-local and reserved addresses are blocked.",
        )
    # Local Docker/WSL often has public IPv6 DNS answers without an IPv6 route.
    # Every answer above is still validated; prefer IPv4 when both are offered.
    address = min(addresses, key=lambda value: (ipaddress.ip_address(value).version != 4, value))
    host = "[" + address + "]" if ":" in address else address
    return parsed, urlunsplit(("https", host, parsed.path or "/", parsed.query, ""))


def public_url(url):
    destination(url)
    return url


def fetch(url, *, max_bytes=2 * 1024 * 1024):
    current = url
    deadline = time.monotonic() + 25
    try:
        with ExitStack() as clients:
            for redirect in range(5):
                parsed, pinned = destination(current)
                transport = PinnedTransport(urlsplit(pinned).hostname, parsed.hostname)
                client = clients.enter_context(
                    httpx.Client(
                        timeout=12,
                        follow_redirects=False,
                        trust_env=True,
                        transport=transport,
                    )
                )
                # Connect to the validated address, preserving HTTP Host and TLS SNI/certificate
                # verification. The inherited proxy still mediates the connection.
                with client.stream(
                    "GET",
                    pinned,
                    headers={
                        "User-Agent": "ALLExport-evidence/0.1",
                        "Host": parsed.hostname,
                    },
                    extensions={"sni_hostname": parsed.hostname},
                ) as response:
                    if time.monotonic() > deadline:
                        raise DomainError(
                            "SOURCE_TIME_LIMIT",
                            "Public retrieval exceeded the wall-time budget.",
                            503,
                        )
                    if response.status_code in (301, 302, 303, 307, 308):
                        current = urljoin(current, response.headers.get("location", ""))
                        continue
                    if response.status_code in (401, 403):
                        raise DomainError(
                            "SOURCE_AUTH_REQUIRED",
                            "The source is unavailable or requires access.",
                            503,
                        )
                    if response.status_code == 429:
                        raise DomainError(
                            "SOURCE_RATE_LIMITED", "The source is rate limited.", 503
                        )
                    if response.status_code != 200:
                        raise DomainError(
                            "SOURCE_UNAVAILABLE",
                            "The source did not return usable content.",
                            503,
                        )
                    media = response.headers.get("content-type", "").split(";")[0]
                    if media not in {
                        "text/html",
                        "text/plain",
                        "application/json",
                        "application/pdf",
                        "application/octet-stream",
                    }:
                        raise DomainError(
                            "SOURCE_TYPE_BLOCKED",
                            "Unsupported public source type.",
                            503,
                        )
                    content = bytearray()
                    for part in response.iter_bytes():
                        content.extend(part)
                        if len(content) > max_bytes:
                            raise DomainError(
                                "SOURCE_SIZE_LIMIT",
                                "Fetched source exceeds the configured limit.",
                                503,
                            )
                        if time.monotonic() > deadline:
                            raise DomainError(
                                "SOURCE_TIME_LIMIT",
                                "Public retrieval exceeded the wall-time budget.",
                                503,
                            )
                    if media == "application/octet-stream":
                        if not content.startswith(b"%PDF-"):
                            raise DomainError(
                                "SOURCE_TYPE_BLOCKED",
                                "Untyped public sources must contain a PDF signature.",
                                503,
                            )
                        media = "application/pdf"
                    return {
                        "url": current,
                        "content": bytes(content),
                        "media_type": media,
                        "hash": hashlib.sha256(content).hexdigest(),
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                        "provider_request_id": response.headers.get("x-request-id"),
                    }
    except httpx.TimeoutException:
        raise DomainError("SOURCE_TIME_LIMIT", "Public retrieval timed out.", 503)
    except httpx.HTTPError:
        raise DomainError(
            "SOURCE_NETWORK_UNAVAILABLE",
            "Public retrieval could not complete with the configured network and trust policy.",
            503,
        )
    raise DomainError(
        "SOURCE_REDIRECT_LIMIT", "Source exceeded the redirect limit.", 503
    )
