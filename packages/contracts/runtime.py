"""The runtime consumes the canonical schemas; it owns no competing wire model."""

from functools import lru_cache
from scripts.validate_contract import load_contract, instance_validator, check, resolve

DOCUMENT = load_contract()
OPERATIONS = {
    op["operationId"]: (path, method, op)
    for path, item in DOCUMENT["paths"].items()
    for method, op in item.items()
}


@lru_cache(maxsize=None)
def validator(operation, direction, status="200", media="application/json"):
    op = OPERATIONS[operation][2]
    body = resolve(
        DOCUMENT,
        op["requestBody"] if direction == "request" else op["responses"][status],
    )
    schema = body["content"][media]["schema"]
    return instance_validator(DOCUMENT, schema)


def validate_request(operation, value, media="application/json"):
    op = OPERATIONS[operation][2]
    if "requestBody" in op:
        validator(operation, "request", media=media).validate(value)


def validate_response(operation, status, value):
    validator(operation, "response", str(status)).validate(value)
