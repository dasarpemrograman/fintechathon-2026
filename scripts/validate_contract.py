"""Validate the canonical OpenAPI file and its media-type examples offline."""

import argparse
from pathlib import Path
import sys
from typing import NamedTuple
from urllib.parse import unquote

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from openapi_spec_validator import validate
from referencing import Registry
from referencing.exceptions import NoSuchResource

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "api" / "openapi.yaml"
METHODS = {"get", "post", "patch", "put", "delete", "head", "options", "trace"}


class ValidationCounts(NamedTuple):
    operations: int
    request_examples: int
    response_examples: int


class UniqueKeyLoader(yaml.SafeLoader):
    """Reject keys that would otherwise silently overwrite routes or schemas."""


def unique_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ValueError(
                f"Duplicate YAML key: {key!r} at line {key_node.start_mark.line + 1}"
            )
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping
)


def load_contract(path=CONTRACT):
    return yaml.load(Path(path).read_text(encoding="utf-8"), Loader=UniqueKeyLoader)


def pointer(document, target):
    if not isinstance(target, str) or not target.startswith("#/"):
        raise ValueError(f"Only local contract references allowed: {target!r}")
    resolved = document
    try:
        for token in unquote(target[2:]).split("/"):
            token = token.replace("~1", "/").replace("~0", "~")
            resolved = (
                resolved[int(token)] if isinstance(resolved, list) else resolved[token]
            )
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise ValueError(f"Unresolved local reference: {target}") from exc
    return resolved


def resolve(document, value):
    """Resolve a reference-object chain; recursive schema children stay intact."""
    seen = set()
    while isinstance(value, dict) and "$ref" in value:
        target = value["$ref"]
        if target in seen:
            raise ValueError(f"Cyclic reference chain: {target}")
        seen.add(target)
        value = pointer(document, target)
    return value


def no_remote_resource(uri):
    raise NoSuchResource(ref=uri)


def instance_validator(document, schema):
    # Keep the whole document as reference root, including schemas outside components.
    # The preflight scan rejects external references before jsonschema can retrieve them.
    root = {**document, "allOf": [schema]}
    return Draft202012Validator(
        root,
        format_checker=FormatChecker(),
        registry=Registry(retrieve=no_remote_resource),
    )


def schema_validator(document, name):
    return instance_validator(document, {"$ref": f"#/components/schemas/{name}"})


def walk(value, location="#"):
    if isinstance(value, dict):
        yield location, value
        for key, child in value.items():
            escaped = str(key).replace("~", "~0").replace("/", "~1")
            yield from walk(child, f"{location}/{escaped}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk(child, f"{location}/{index}")


def validate_examples(document, body, location):
    count = 0
    body = resolve(document, body)
    for media_type, media in body.get("content", {}).items():
        examples = []
        if "example" in media:
            examples.append(("example", media["example"]))
        for name, original in media.get("examples", {}).items():
            label = f"{location} {media_type} example {name}"
            try:
                example = resolve(document, original)
                if "externalValue" in example:
                    raise ValueError(
                        "External example values are unsupported; embed value locally"
                    )
                if "value" not in example:
                    raise ValueError("Example must contain a local value")
                examples.append((name, example["value"]))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{label}: {exc}") from exc
        for name, value in examples:
            label = f"{location} {media_type} example {name}"
            if "schema" not in media:
                raise ValueError(f"{label}: example has no applicable schema")
            try:
                instance_validator(document, media["schema"]).validate(value)
            except Exception as exc:
                raise ValueError(f"{label}: {exc}") from exc
            count += 1
    return count


def check(document):
    # Check references before any validator runs, so broken/external references
    # never result in a remote fetch. Resolve pure chains to diagnose cycles.
    for location, node in walk(document):
        if "$dynamicRef" in node:
            raise ValueError(
                f"{location}: $dynamicRef is unsupported; use local $ref components"
            )
        if "$ref" in node:
            try:
                resolve(document, node)
            except ValueError as exc:
                raise ValueError(f"{location}: {exc}") from exc
    for name, schema in document["components"]["schemas"].items():
        try:
            Draft202012Validator.check_schema(schema)
        except Exception as exc:
            raise ValueError(f"#/components/schemas/{name}: {exc}") from exc
    operations = request_examples = response_examples = 0
    for path, path_item in document["paths"].items():
        for method, operation in resolve(document, path_item).items():
            if method not in METHODS:
                continue
            operations += 1
            label = (
                f"{method.upper()} {path} ({operation.get('operationId', 'unnamed')})"
            )
            if "requestBody" in operation:
                request_examples += validate_examples(
                    document, operation["requestBody"], f"{label} request"
                )
            for status, response in operation["responses"].items():
                response_examples += validate_examples(
                    document, response, f"{label} response {status}"
                )
    validate(document)
    return ValidationCounts(operations, request_examples, response_examples)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract", nargs="?", type=Path, default=CONTRACT)
    args = parser.parse_args(argv)
    try:
        counts = check(load_contract(args.contract))
    except Exception as exc:
        print(f"Contract validation failed: {exc}", file=sys.stderr)
        return 1
    print(
        f"OpenAPI valid: {counts.operations} operations; "
        f"{counts.request_examples} request examples; "
        f"{counts.response_examples} response examples validated."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
