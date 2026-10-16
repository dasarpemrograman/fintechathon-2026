from unittest.mock import patch
import socket, unittest
import httpx
from packages.adapters.network import fetch, public_url
from services.api.store import DomainError


class RetrievalTests(unittest.TestCase):
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
