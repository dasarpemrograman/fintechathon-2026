from datetime import datetime, timezone
from unittest.mock import patch
import gzip, hashlib, json, unittest
import httpx
from packages.adapters import providers
from services.api.store import DomainError


class ProviderAdapterTests(unittest.TestCase):
    def test_gemini_prepaid_error_explains_free_tier_without_leaking_body(self):
        for wrapped in [False, True]:
            with self.subTest(array_response=wrapped):
                error = {
                    "error": {
                        "code": 402,
                        "status": "RESOURCE_EXHAUSTED",
                        "message": "Your prepayment credits are depleted. private-provider-detail",
                    }
                }
                response = httpx.Response(
                    402,
                    json=[error] if wrapped else error,
                    request=httpx.Request(
                        "POST",
                        "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
                    ),
                )
                with self.assertRaises(DomainError) as caught:
                    providers.checked_json("configured-model", response, "MODEL")
                self.assertEqual(caught.exception.code, "MODEL_PAYMENT_REQUIRED")
                self.assertIn("Free Tier", caught.exception.reason)
                self.assertNotIn(
                    "private-provider-detail",
                    json.dumps(caught.exception.provider_receipt),
                )

    def call_search(self, status, body, headers=None, compressed=False):
        real_client = httpx.Client

        def handle(request):
            self.assertEqual(request.url.host, "api.search.brave.com")
            self.assertEqual(
                request.headers["X-Subscription-Token"], "fixture-only-key"
            )
            if compressed:
                raw = gzip.compress(json.dumps(body, separators=(",", ":")).encode())
                return httpx.Response(
                    status,
                    content=raw,
                    headers={
                        **(headers or {}),
                        "Content-Encoding": "gzip",
                        "Content-Length": str(len(raw)),
                    },
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
            (402, "unavailable"),
            (403, "auth_required"),
            (429, "rate_limited"),
            (503, "unavailable"),
        ]:
            with self.assertRaises(DomainError) as caught:
                self.call_search(
                    status, {"error": "fixture-only-error"}, {"Retry-After": "3"}
                )
            receipt = caught.exception.provider_receipt
            if status == 402:
                self.assertEqual(caught.exception.code, "SEARCH_PAYMENT_REQUIRED")
            self.assertEqual(receipt["status"], expected)
            self.assertIsNone(receipt["data_mode"])
            self.assertNotIn("fixture-only-key", json.dumps(receipt))
            self.assertEqual(receipt["retry_after"], 3)

    def test_gzip_search_retains_results_receipt_and_decoded_hash(self):
        body = {"web": {"results": [{"url": "https://example.org", "title": "Source"}]}}
        plain = self.call_search(200, body, {"x-request-id": "gzip-fixture"})
        compressed = self.call_search(
            200, body, {"x-request-id": "gzip-fixture"}, compressed=True
        )
        for key in ["data", "response_hash", "request_id", "status", "data_mode"]:
            self.assertEqual(compressed[key], plain[key])

    def test_gzip_response_limit_applies_to_decoded_size(self):
        raw = gzip.compress(b" " * (2 * 1024 * 1024 + 1))
        with httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200, content=raw, headers={"Content-Encoding": "gzip"}
                )
            )
        ) as client:
            with self.assertRaises(DomainError) as caught:
                providers.bounded_response(
                    client, "brave", "GET", "https://example.org"
                )
        self.assertEqual(caught.exception.code, "PROVIDER_SIZE_LIMIT")

    def test_gzip_model_response_preserves_valid_task_output(self):
        selected = {"sections": ["overview"], "metric_keys": [], "evidence_ids": []}
        raw = json.dumps(
            {"choices": [{"message": {"content": json.dumps(selected)}}]}
        ).encode()
        real_client = httpx.Client
        with (
            patch.dict(
                "os.environ",
                {
                    "ALLEXPORT_MODEL_BASE_URL": "https://model.example.org/v1",
                    "ALLEXPORT_MODEL_API_KEY": "fixture-only-key",
                    "ALLEXPORT_MODEL_ID": "fixture-only-model",
                },
            ),
            patch.object(providers, "public_url"),
            patch.object(
                providers.httpx,
                "Client",
                side_effect=lambda **kw: real_client(
                    transport=httpx.MockTransport(
                        lambda request: httpx.Response(
                            200,
                            content=gzip.compress(raw),
                            headers={"Content-Encoding": "gzip"},
                        )
                    )
                ),
            ),
        ):
            result = providers.model_task("select_explanation_sections", {})
        self.assertEqual(result["data"], selected)
        self.assertEqual(result["response_hash"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(result["data_mode"], "live")

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
