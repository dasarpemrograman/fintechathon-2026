"""Public query planning: directions and public terms, never private documents."""

import json, re
from urllib.parse import urlsplit
from services.api.settings import ROOT
from services.api.store import DomainError, issue

REGISTRY = json.loads((ROOT / "config/source-registry-v1.json").read_text())
WORDS = {
    "en": {
        "export": "export requirements customs",
        "import": "import requirements customs",
    },
    "id": {
        "export": "persyaratan ekspor bea cukai",
        "import": "persyaratan impor bea cukai",
    },
    "zh": {"export": "出口 要求 海关", "import": "进口 要求 海关"},
    "de": {
        "export": "Ausfuhr Anforderungen Zoll",
        "import": "Einfuhr Anforderungen Zoll",
    },
}


def plan(parent, body, parties=None):
    terms = body.get("approved_public_terms", [])
    if not terms:
        raise DomainError(
            "PUBLIC_QUERY_REVIEW_REQUIRED",
            "Review public goods/jurisdiction query terms before live discovery.",
        )
    text = " ".join(terms).strip()
    if not text:
        raise DomainError(
            "PUBLIC_QUERY_REVIEW_REQUIRED",
            "Enter nonempty reviewed public product terms.",
        )
    private = [
        name
        for party in parties or parent.get("parties", [])
        for name in [party.get("legal_name"), party.get("display_name")]
        if name
    ]
    if (
        re.search(
            r"(?i)\b(iban|swift|bank account|rekening|account number|private contract)\b",
            text,
        )
        or re.search(r"\b[A-Z]{2}[0-9]{2}[A-Z0-9]{12,30}\b", text)
        or any(
            name.casefold() in text.casefold()
            if any(ord(char) > 127 for char in name)
            else re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", text, re.I)
            for name in private
        )
    ):
        raise DomainError(
            "PRIVATE_QUERY_BLOCKED",
            "Queries cannot include party identities, bank details or private contract content.",
        )
    origin = parent.get("dispatch_country")
    destination = parent.get("destination_country")
    exporter = parent.get("seller_domicile")
    queries = []
    warnings = []

    def query(category, jurisdiction, direction, words, domains=None):
        domain = (domains or [None])[0]
        queries.append(
            {
                "category": category,
                "jurisdiction": jurisdiction,
                "direction": direction,
                "query": " ".join(
                    [text, jurisdiction or "", words]
                    + (["site:" + domain] if domain else [])
                ),
                "registry_version": REGISTRY["version"],
            }
        )

    for category in body["categories"]:
        if category == "fx":
            continue
        if category == "requirements":
            for country, direction in [(origin, "export"), (destination, "import")]:
                if not country:
                    warnings.append(
                        issue(
                            "JURISDICTION_MISSING",
                            "Confirm dispatch and destination jurisdictions for applicable rules.",
                        )
                    )
                    continue
                authority = REGISTRY["authorities"].get(country)
                if not authority or not authority["customs"]:
                    warnings.append(
                        issue(
                            "AUTHORITY_COVERAGE_UNCONFIRMED",
                            "No reviewed authority entry is declared for "
                            + country
                            + "; research results require jurisdiction-specific review.",
                        )
                    )
                language = authority["language"] if authority else "en"
                query(
                    category,
                    country,
                    direction,
                    WORDS.get(language, WORDS["en"])[direction],
                    authority["customs"] if authority else None,
                )
        elif category == "finance":
            authority = REGISTRY["authorities"].get(exporter, {})
            if not exporter:
                warnings.append(
                    issue(
                        "EXPORTER_JURISDICTION_MISSING",
                        "Confirm legal exporter jurisdiction before financing research.",
                    )
                )
                continue
            query(
                category,
                exporter,
                "exporter_eligibility",
                "export working capital eligibility pricing required documents",
                authority.get("finance"),
            )
        elif category == "market_price":
            query(
                category,
                destination,
                "destination_wholesale",
                "wholesale quotation grade intended use minimum order quantity",
            )
        elif category == "freight":
            query(
                category,
                destination,
                "route_logistics",
                "freight quotation "
                + (origin or "[dispatch required]")
                + " destination charges included coverage",
            )
        else:
            query(category, destination, "reference", category)
    return queries, warnings


def source_owner(url):
    host = (urlsplit(url).hostname or "").casefold().removeprefix("www.")
    for authority in REGISTRY["authorities"].values():
        for domain in authority.get("customs", []) + authority.get("finance", []):
            if host == domain or host.endswith("." + domain):
                return domain
    return host
