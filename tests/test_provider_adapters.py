from datetime import datetime, timezone
from unittest.mock import patch
import hashlib, json, unittest
import httpx
from packages.adapters import providers
from services.api.store import DomainError


class ProviderAdapterTests(unittest.TestCase):
    def call_search(self, status, body, headers=None):
        real_client = httpx.Client

        def handle(request):
            self.assertEqual(request.url.host, "api.search.brave.com")
            self.assertEqual(
                request.headers["X-Subscription-Token"], "fixture-only-key"
            )
            return httpx.Response(status, json=body, headers=headers)

        with (
            patch.dict("os.environ", {"BRAVE_SEARCH_API_KEY": "fixture-only-key"}),
            patch.object(
                providers.httpx,
                "Client",
                side_effect=lambda **kw: real_client(
                    transport=httpx.MockTransport(handle)
                ),
            ),
        ):
            return providers.search("public goods ID export", 3)

    def test_success_partial_auth_rate_limit_and_outage_receipts(self):
        success = self.call_search(
            200,
            {
                "web": {
                    "results": [
                        {
                            "url": "https://public.example.test",
                            "title": "Public",
                            "description": "Snippet",
                        }
                    ]
                }
            },
            {"x-request-id": "provider-fixture-request"},
        )
        self.assertEqual(success["status"], "success")
        self.assertEqual(success["data_mode"], "live")
        self.assertEqual(success["request_id"], "provider-fixture-request")
        self.assertEqual(
            self.call_search(200, {"web": {"results": []}})["status"], "partial"
        )
        for status, expected in [
            (401, "auth_required"),
            (403, "auth_required"),
            (429, "rate_limited"),
            (503, "unavailable"),
        ]:
            with self.assertRaises(DomainError) as caught:
                self.call_search(
                    status, {"error": "fixture-only-error"}, {"Retry-After": "3"}
                )
            receipt = caught.exception.provider_receipt
            self.assertEqual(receipt["status"], expected)
            self.assertIsNone(receipt["data_mode"])
            self.assertNotIn("fixture-only-key", json.dumps(receipt))
            self.assertEqual(receipt["retry_after"], 3)

    def test_reference_fx_preserves_decimal_precision_and_partial_pairs(self):
        raw = b'[{"date":"2026-10-15","base":"USD","quote":"EUR","rate":0.12345678901234567890123456789,"providers":[{"key":"ECB"}]}]'
        response = {
            "content": raw,
            "hash": hashlib.sha256(raw).hexdigest(),
            "provider_request_id": "fx-fixture",
            "fetched_at": "2026-10-16T12:00:00Z",
        }
        with patch.object(providers, "fetch", return_value=response):
            result = providers.fx_rates("USD", ["EUR", "IDR"])
        self.assertEqual(result["data"][0]["rate"], "0.12345678901234567890123456789")
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["data"][0]["providers"], ["ECB"])
        self.assertEqual(result["response_hash"], response["hash"])

    def test_bad_fx_shape_never_becomes_a_zero_or_invented_rate(self):
        response = {
            "content": b'[{"date":"2026-10-15","base":"USD","quote":"EUR","rate":0}]',
            "hash": "a" * 64,
            "provider_request_id": None,
            "fetched_at": "2026-10-16T12:00:00Z",
        }
        with (
            patch.object(providers, "fetch", return_value=response),
            self.assertRaises(DomainError) as caught,
        ):
            providers.fx_rates("USD", ["EUR"])
        self.assertEqual(
            caught.exception.provider_receipt["status"], "invalid_response"
        )

    def test_synthetic_and_cached_receipts_keep_their_own_modes(self):
        for mode in ["synthetic_demo", "cached"]:
            self.assertEqual(
                providers.receipt("fixture", [], mode=mode)["data_mode"], mode
            )
