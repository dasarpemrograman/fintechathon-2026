from unittest.mock import patch
import socket, ssl, unittest
import httpcore
import httpx
from packages.adapters.network import fetch, public_url
from packages.adapters.pinned_transport import PinnedTransport
from services.api.store import DomainError


class RetrievalTests(unittest.TestCase):
    def test_untyped_pdf_is_recognized_but_other_binary_content_is_blocked(self):
        result = self.call(lambda request: httpx.Response(
            200, headers={"Content-Type": "application/octet-stream"}, content=b"%PDF-1.7\nsource"
        ))
        self.assertEqual(result["media_type"], "application/pdf")
        with self.assertRaises(DomainError) as error:
            self.call(lambda request: httpx.Response(
                200, headers={"Content-Type": "application/octet-stream"}, content=b"MZ binary"
            ))
        self.assertEqual(error.exception.code, "SOURCE_TYPE_BLOCKED")

    def test_dual_stack_source_prefers_public_ipv4_without_skipping_address_checks(self):
        from packages.adapters.network import destination

        answers = [
            (socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("2606:4700:4700::1111", 443, 0, 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443)),
        ]
        with patch("packages.adapters.network.socket.getaddrinfo", return_value=answers):
            _, pinned = destination("https://public.example/source")
        self.assertEqual(pinned, "https://93.184.216.34/source")
        answers.append((socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("::1", 443, 0, 0)))
        with (
            patch("packages.adapters.network.socket.getaddrinfo", return_value=answers),
            self.assertRaises(DomainError) as error,
        ):
            destination("https://public.example/source")
        self.assertEqual(error.exception.code, "FETCH_ADDRESS_BLOCKED")

    def test_real_connect_transport_keeps_pinned_ip_and_original_tls_hostname(self):
        for scheme in [None, "http", "https"]:
            with self.subTest(proxy=scheme):
                names, writes, connections = [], [], []
                buffer = [b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nok"]
                if scheme:
                    buffer.insert(0, b"HTTP/1.1 200 Connection established\r\n\r\n")

                class Stream(httpcore.MockStream):
                    def start_tls(
                        self, ssl_context, server_hostname=None, timeout=None
                    ):
                        self_test.assertTrue(ssl_context.check_hostname)
                        self_test.assertEqual(
                            ssl_context.verify_mode, ssl.CERT_REQUIRED
                        )
                        names.append(server_hostname)
                        return self

                    def write(self, data, timeout=None):
                        writes.append(data)

                class Backend(httpcore.NetworkBackend):
                    def connect_tcp(self, host, port, *args):
                        connections.append((host, port))
                        return Stream(buffer.copy())

                self_test = self
                proxies = {"https": scheme + "://proxy.example:8080"} if scheme else {}
                with (
                    patch(
                        "packages.adapters.pinned_transport.getproxies",
                        return_value=proxies,
                    ),
                    patch(
                        "packages.adapters.pinned_transport.proxy_bypass",
                        return_value=False,
                    ),
                    httpx.Client(
                        transport=PinnedTransport(
                            "93.184.216.34",
                            "public.example",
                            backend=Backend(),
                        )
                    ) as client,
                ):
                    result = client.get(
                        "https://93.184.216.34/source",
                        headers={"Host": "public.example"},
                        extensions={"sni_hostname": "public.example"},
                    )
                self.assertEqual(result.text, "ok")
                self.assertEqual(
                    names,
                    ["proxy.example", "public.example"]
                    if scheme == "https"
                    else ["public.example"],
                )
                self.assertEqual(
                    connections,
                    [("proxy.example", 8080)] if scheme else [("93.184.216.34", 443)],
                )
                sent = b"".join(writes)
                self.assertIn(b"Host: public.example", sent)
                if scheme:
                    self.assertIn(b"CONNECT 93.184.216.34:443 HTTP/1.1", sent)

    def test_proxy_transport_preserves_certificate_failures(self):
        class Stream(httpcore.MockStream):
            def start_tls(self, *args):
                raise httpcore.ConnectError("certificate verification failed")

        class Backend(httpcore.NetworkBackend):
            def connect_tcp(self, *args):
                return Stream([b"HTTP/1.1 200 Connection established\r\n\r\n"])

        with (
            patch(
                "packages.adapters.pinned_transport.getproxies",
                return_value={"https": "http://proxy.example:8080"},
            ),
            patch(
                "packages.adapters.pinned_transport.proxy_bypass", return_value=False
            ),
            httpx.Client(
                transport=PinnedTransport(
                    "93.184.216.34", "public.example", backend=Backend()
                )
            ) as client,
            self.assertRaises(httpx.ConnectError),
        ):
            client.get("https://93.184.216.34/source")

    def dns(self, host, *args, **kwargs):
        return [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                6,
                "",
                ("93.184.216.34" if host == "public.example" else "127.0.0.1", 443),
            )
        ]

    def call(self, handler, url="https://public.example/source", **kwargs):
        client = httpx.Client(transport=httpx.MockTransport(handler))
        with (
            patch("packages.adapters.network.socket.getaddrinfo", side_effect=self.dns),
            patch("packages.adapters.network.httpx.Client", return_value=client),
        ):
            return fetch(url, **kwargs)

    def test_public_address_is_pinned_with_original_tls_and_host(self):
        def handle(request):
            self.assertEqual(request.url.host, "93.184.216.34")
            self.assertEqual(request.headers["host"], "public.example")
            self.assertEqual(request.extensions["sni_hostname"], "public.example")
            return httpx.Response(
                200, headers={"Content-Type": "text/plain"}, content=b"public source"
            )

        result = self.call(handle)
        self.assertEqual(result["url"], "https://public.example/source")

    def test_private_and_redirected_private_addresses_never_receive_requests(self):
        requests = []

        def handle(request):
            requests.append(request)
            return httpx.Response(
                302, headers={"Location": "https://private.example/admin"}
            )

        with self.assertRaises(DomainError):
            self.call(handle)
        self.assertEqual(len(requests), 1)
        for host in ["127.0.0.1", "169.254.169.254", "::1", "10.0.0.1", "192.168.1.1"]:
            with patch(
                "packages.adapters.network.socket.getaddrinfo",
                return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", (host, 443))],
            ):
                with self.assertRaises(DomainError):
                    public_url("https://private.example/")

    def test_size_auth_type_rate_and_timeout_failures_are_explicit(self):
        for response, code in [
            (
                httpx.Response(
                    200, headers={"Content-Type": "text/plain"}, content=b"oversize"
                ),
                "SOURCE_SIZE_LIMIT",
            ),
            (httpx.Response(403), "SOURCE_AUTH_REQUIRED"),
            (httpx.Response(429), "SOURCE_RATE_LIMITED"),
            (
                httpx.Response(
                    200, headers={"Content-Type": "application/x-executable"}
                ),
                "SOURCE_TYPE_BLOCKED",
            ),
        ]:
            with self.subTest(code=code), self.assertRaises(DomainError) as e:
                self.call(lambda r: response, max_bytes=3)
            self.assertEqual(e.exception.code, code)

        def timeout(request):
            raise httpx.ReadTimeout("test")

        with self.assertRaises(DomainError) as e:
            self.call(timeout)
        self.assertEqual(e.exception.code, "SOURCE_TIME_LIMIT")

    def test_http_credentials_and_nonstandard_ports_are_refused(self):
        for url in [
            "http://public.example",
            "https://user:secret@public.example",
            "https://public.example:8443",
            "https://public.example:invalid",
        ]:
            with self.assertRaises(DomainError):
                public_url(url)

    def test_query_page_and_action_budgets_stop_before_work(self):
        from packages.adapters.budgets import Budget

        budget = Budget(
            {
                "max_queries": 1,
                "max_pages": 2,
                "max_actions": 2,
                "max_provider_retries": 0,
            }
        )
        budget.consume("query")
        budget.consume("page")
        with self.assertRaises(DomainError):
            budget.consume("page")
        self.assertEqual((budget.queries, budget.pages, budget.actions), (1, 1, 2))
