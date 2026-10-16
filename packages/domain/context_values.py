"""Registry validation supplements the canonical wire shapes."""

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import pycountry
from services.api.store import DomainError

CURRENCIES = {
    "currency",
    "reporting_currency",
    "base_currency",
    "quote_currency",
    "fx_base_currency",
}
COUNTRIES = {
    "seller_domicile",
    "dispatch_country",
    "destination_country",
    "origin_country",
    "jurisdiction",
}


def validate(value, path=""):
    if isinstance(value, list):
        for index, item in enumerate(value):
            validate(item, path + "/" + str(index))
    elif isinstance(value, dict):
        for key, item in value.items():
            field = path + "/" + key
            if item is not None and key in {"timezone", "owner_timezone"}:
                try:
                    ZoneInfo(item)
                except (ZoneInfoNotFoundError, ValueError):
                    raise DomainError(
                        "INVALID_TIMEZONE", "Use a known IANA timezone.", field=field
                    )
            if (
                item is not None
                and key in CURRENCIES
                and pycountry.currencies.get(alpha_3=item) is None
            ):
                raise DomainError(
                    "INVALID_CURRENCY", "Use a known ISO currency code.", field=field
                )
            if (
                item is not None
                and key in COUNTRIES
                and pycountry.countries.get(alpha_2=item) is None
            ):
                raise DomainError(
                    "INVALID_COUNTRY", "Use a known ISO country code.", field=field
                )
            if key in {"jurisdictions", "fx_quote_currencies"}:
                for index, code in enumerate(item):
                    known = (
                        pycountry.countries.get(alpha_2=code)
                        if key == "jurisdictions"
                        else pycountry.currencies.get(alpha_3=code)
                    )
                    if known is None:
                        raise DomainError(
                            "INVALID_CONTEXT_CODE",
                            "Use a known jurisdiction/currency code.",
                            field=field + "/" + str(index),
                        )
            validate(item, field)
