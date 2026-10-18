"""Bounded public source receipts for Gate B; not legal or quote acceptance."""

from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
import hashlib
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from packages.adapters.providers import search
from packages.adapters.network import fetch
from services.api.store import DomainError


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hidden = 0
        self.title = False
        self.titles = []
        self.words = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.hidden += 1
        if tag == "title":
            self.title = True

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.hidden = max(0, self.hidden - 1)
        if tag == "title":
            self.title = False

    def handle_data(self, value):
        if not self.hidden:
            self.words.append(value)
            if self.title:
                self.titles.append(value)


def run():
    root = Path(".local/live-source-receipts")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    checks = []
    scopes = [
        ("ID-SG", "green coffee beans", "ID", "beacukai.go.id", "SG", "customs.gov.sg"),
        (
            "CN-SG",
            "manufactured components",
            "CN",
            "customs.gov.cn",
            "SG",
            "customs.gov.sg",
        ),
        ("KE-DE", "dried mango", "KE", "kra.go.ke", "DE", "zoll.de"),
    ]
    targets = []
    for lane, product, origin, origin_domain, destination, destination_domain in scopes:
        targets.extend(
            [
                (
                    lane,
                    product,
                    "official_export",
                    origin,
                    origin_domain,
                    "export requirements",
                ),
                (
                    lane,
                    product,
                    "official_import",
                    destination,
                    destination_domain,
                    "import requirements",
                ),
            ]
        )
    targets.extend(
        [
            (
                "ID-SG",
                "coffee",
                "finance",
                "ID",
                "indonesiaeximbank.go.id",
                "export working capital financing",
            ),
            (
                "ID-SG",
                "coffee",
                "market_reference",
                "SG",
                "intracen.org",
                "coffee market price trade",
            ),
            (
                "ID-SG",
                "coffee",
                "logistics_reference",
                None,
                "maersk.com",
                "Indonesia Singapore shipping",
            ),
        ]
    )
    # Nine public queries, at most two candidate fetches each: under declared
    # 12-query / 20-page / 40-action caps. No private deal data is sent.
    for lane, product, category, jurisdiction, domain, terms in targets:
        row = {
            "lane": lane,
            "product_terms": product,
            "category": category,
            "jurisdiction": jurisdiction,
            "candidate_domain": domain,
        }
        try:
            result = search(f"{product} {terms} site:{domain}", 2)
            row["search_receipt"] = {k: v for k, v in result.items() if k != "data"}
            candidates = [
                v
                for v in result["data"]
                if urlsplit(v["url"]).hostname == domain
                or (urlsplit(v["url"]).hostname or "").endswith("." + domain)
            ]
            row["fetch_attempts"] = []
            for candidate in candidates[:2]:
                try:
                    source = fetch(candidate["url"])
                except DomainError as error:
                    row["fetch_attempts"].append(
                        {"url": candidate["url"], "code": error.code}
                    )
                    continue
                raw = source["content"]
                path = root / (hashlib.sha256(raw).hexdigest() + ".source")
                path.write_bytes(raw)
                path.chmod(0o600)
                row["source_receipt"] = {
                    k: v for k, v in source.items() if k != "content"
                }
                row["source_bytes"] = len(raw)
                if source["media_type"] in {"text/html", "text/plain"}:
                    parser = Text()
                    parser.feed(raw.decode("utf-8", errors="replace"))
                    text = " ".join(parser.words).casefold()
                    row["parsed_observation"] = {
                        "title": " ".join(parser.titles).strip()[:300],
                        "matched_product_terms": [
                            word for word in product.split() if word.casefold() in text
                        ],
                        "source_is_executable_quote": False,
                        "reviewed_rule_applicability": False,
                    }
                else:
                    row["parsed_observation"] = None
                row["status"] = "retrieved_requires_scope_review"
                break
            else:
                row["status"] = "blocked_no_fetchable_registered_source"
        except DomainError as error:
            row.update(status="blocked", code=error.code)
        checks.append(row)
        print(
            json.dumps({k: row[k] for k in ["lane", "category", "status"]}), flush=True
        )
    report = {
        "scope": "public_source_retrieval_partial_gate_b",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "coverage_acceptance": False,
        "limits": {"max_queries": 9, "max_candidate_pages": 18, "max_actions": 27},
        "limitations": [
            "Registry domain membership and HTTP success do not establish product-specific legal applicability.",
            "Charges, finance eligibility/pricing, comparable market prices and executable logistics quotes remain unknown until reviewed.",
            "CN manufactured components lack a precise product classification; scopes remain provisional.",
            "Finance, market and logistics receipts are scoped to ID-SG; remaining lanes are unaccepted.",
            "Configured model acceptance is checked separately; no synthetic evidence is substituted.",
        ],
        "checks": checks,
    }
    path = Path(".local/live-source-probes.json")
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    path.chmod(0o600)
    # This partial retrieval probe deliberately cannot signal full acceptance.
    return 2


if __name__ == "__main__":
    raise SystemExit(run())
