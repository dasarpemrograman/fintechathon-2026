"""Pinned HTTPS through inherited proxies, with the original TLS hostname."""

from urllib.request import getproxies, proxy_bypass

import httpcore
import httpx


class HostnameStream(httpcore.NetworkStream):
    def __init__(self, stream, address, hostname, proxy_tls_hostname=None):
        self.stream, self.address, self.hostname = stream, address, hostname
        self.proxy_tls_hostname = proxy_tls_hostname

    def read(self, max_bytes, timeout=None):
        return self.stream.read(max_bytes, timeout)

    def write(self, buffer, timeout=None):
        return self.stream.write(buffer, timeout)

    def close(self):
        return self.stream.close()

    def get_extra_info(self, info):
        return self.stream.get_extra_info(info)

    def start_tls(self, ssl_context, server_hostname=None, timeout=None):
        # HTTP Core's CONNECT tunnel ignores the request's sni_hostname extension.
        # Verify an HTTPS proxy against its own name first; inside the tunnel,
        # replace only the validated destination IP with the source hostname.
        hostname = self.proxy_tls_hostname or (
            self.hostname if server_hostname == self.address else server_hostname
        )
        stream = self.stream.start_tls(ssl_context, hostname, timeout)
        return HostnameStream(stream, self.address, self.hostname)


class HostnameBackend(httpcore.NetworkBackend):
    def __init__(self, address, hostname, backend=None, proxy_tls_hostname=None):
        self.address, self.hostname = address, hostname
        self.backend = backend or httpcore.SyncBackend()
        self.proxy_tls_hostname = proxy_tls_hostname

    def connect_tcp(
        self, host, port, timeout=None, local_address=None, socket_options=None
    ):
        stream = self.backend.connect_tcp(
            host, port, timeout, local_address, socket_options
        )
        return HostnameStream(
            stream, self.address, self.hostname, self.proxy_tls_hostname
        )

    def connect_unix_socket(self, path, timeout=None, socket_options=None):
        stream = self.backend.connect_unix_socket(path, timeout, socket_options)
        return HostnameStream(stream, self.address, self.hostname)

    def sleep(self, seconds):
        return self.backend.sleep(seconds)


class PinnedTransport(httpx.HTTPTransport):
    def __init__(self, address, hostname, *, backend=None):
        proxies = getproxies()
        proxy_url = (
            None if proxy_bypass(hostname) else proxies.get("https", proxies.get("all"))
        )
        options = {
            "ssl_context": httpx.create_ssl_context(trust_env=True),
            "network_backend": HostnameBackend(address, hostname, backend),
        }
        # Retain HTTPX's request/stream/exception bridge with a custom HTTP Core
        # pool. These dependencies are pinned and the CONNECT path is tested.
        if proxy_url:
            proxy = httpx.Proxy(proxy_url)
            if proxy.url.scheme not in {"http", "https"}:
                raise httpx.UnsupportedProtocol(
                    "Public retrieval requires an HTTP(S) proxy."
                )
            if proxy.url.scheme == "https":
                options["network_backend"] = HostnameBackend(
                    address,
                    hostname,
                    backend,
                    proxy_tls_hostname=proxy.url.host,
                )
            self._pool = httpcore.HTTPProxy(
                str(proxy.url),
                proxy_auth=proxy.auth,
                proxy_headers=proxy.headers.raw,
                proxy_ssl_context=(
                    proxy.ssl_context or httpx.create_ssl_context(trust_env=True)
                    if proxy.url.scheme == "https"
                    else None
                ),
                **options,
            )
        else:
            self._pool = httpcore.ConnectionPool(**options)
