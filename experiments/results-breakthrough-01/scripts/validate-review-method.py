#!/usr/bin/env python3
"""Validate the frozen V-arm Review Method before any Vela lifecycle call."""

import argparse
import hashlib
import json
import pathlib
import re


def strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_strict(path):
    return json.loads(path.read_bytes(), object_pairs_hook=strict_object)


def type_matches(value, expected):
    return {
        "array": isinstance(value, list),
        "null": value is None,
        "object": isinstance(value, dict),
        "string": isinstance(value, str),
    }.get(expected, False)


def validate(schema, value, location="$"):
    expected_types = schema.get("type")
    if expected_types is not None:
        if isinstance(expected_types, str):
            expected_types = [expected_types]
        if not any(type_matches(value, expected) for expected in expected_types):
            raise ValueError(f"{location}: expected type {expected_types}")
    if "const" in schema and value != schema["const"]:
        raise ValueError(f"{location}: value differs from const")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(f"{location}: value is outside enum")
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        missing = [key for key in schema.get("required", []) if key not in value]
        if missing:
            raise ValueError(f"{location}: missing required fields {missing}")
        if schema.get("additionalProperties") is False:
            extra = sorted(set(value) - set(properties))
            if extra:
                raise ValueError(f"{location}: unsupported fields {extra}")
        for key, child in value.items():
            if key in properties:
                validate(properties[key], child, f"{location}.{key}")
    elif isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            raise ValueError(f"{location}: too few items")
        item_schema = schema.get("items")
        if item_schema is not None:
            for index, child in enumerate(value):
                validate(item_schema, child, f"{location}[{index}]")
    elif isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            raise ValueError(f"{location}: string is too short")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            raise ValueError(f"{location}: string is too long")
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            raise ValueError(f"{location}: string does not match pattern")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema", required=True, type=pathlib.Path)
    parser.add_argument("--schema-source-commit", required=True)
    parser.add_argument("--schema-git-blob", required=True)
    parser.add_argument("--schema-sha256", required=True)
    parser.add_argument("--method", required=True, type=pathlib.Path)
    parser.add_argument("--expected-profile", required=True)
    parser.add_argument("--expected-property", required=True)
    parser.add_argument("--expected-actor", required=True)
    parser.add_argument("--expected-reviewer-kind", required=True)
    parser.add_argument("--expected-reviewer-identifier", required=True)
    parser.add_argument("--expected-reviewer-provider", required=True)
    parser.add_argument("--expected-nonclaim", action="append", default=[])
    parser.add_argument("--declared-independent-of", action="append", default=[])
    parser.add_argument("--shared-dependency", action="append", default=[])
    args = parser.parse_args()

    schema_bytes = args.schema.read_bytes()
    schema_sha256 = hashlib.sha256(schema_bytes).hexdigest()
    if schema_sha256 != args.schema_sha256:
        raise SystemExit("frozen Review Method schema digest mismatch")
    schema = json.loads(schema_bytes, object_pairs_hook=strict_object)
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        raise SystemExit("unexpected Review Method schema dialect")

    method_bytes = args.method.read_bytes()
    method = json.loads(method_bytes, object_pairs_hook=strict_object)
    canonical = (json.dumps(method, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n").encode()
    if method_bytes != canonical:
        raise SystemExit("Review Method is not canonical JSON plus one LF")
    validate(schema, method)

    expected = {
        "profile": args.expected_profile,
        "property": args.expected_property,
        "attested_by_actor_id": args.expected_actor,
        "does_not_establish": args.expected_nonclaim,
    }
    for field, value in expected.items():
        if method[field] != value:
            raise SystemExit(f"Review Method {field} differs from the verification request")
    reviewer = method["reviewer"]
    if reviewer["kind"] != args.expected_reviewer_kind:
        raise SystemExit("Review Method reviewer kind mismatch")
    if reviewer["identifier"] != args.expected_reviewer_identifier:
        raise SystemExit("Review Method reviewer identifier mismatch")
    if reviewer["provider"] != args.expected_reviewer_provider:
        raise SystemExit("Review Method reviewer provider mismatch")
    for field, values in [
        ("declared independence", args.declared_independent_of),
        ("shared dependency", args.shared_dependency),
    ]:
        if len(values) != len(set(values)) or any(not value.strip() or value != value.strip() for value in values):
            raise SystemExit(f"invalid {field} disclosure")
    if not args.shared_dependency:
        raise SystemExit("at least one shared dependency is required")

    receipt = {
        "actor": method["attested_by_actor_id"],
        "candidate_output_accessed": False,
        "discrepancies": [],
        "independence": {
            "declared_independent_of": args.declared_independent_of,
            "shared_dependencies": args.shared_dependency,
        },
        "method_sha256": hashlib.sha256(method_bytes).hexdigest(),
        "nonclaims": method["does_not_establish"],
        "outcome": "pass",
        "profile": method["profile"],
        "property": method["property"],
        "reviewer": method["reviewer"],
        "reader": "frozen-vela-review-method-validator",
        "schema_sha256": schema_sha256,
        "schema_source_commit": args.schema_source_commit,
        "schema_git_blob": args.schema_git_blob,
        "validator": "scripts/validate-review-method.py",
        "verdict": "pass",
    }
    print(json.dumps(receipt, ensure_ascii=False, separators=(",", ":"), sort_keys=True))


if __name__ == "__main__":
    main()
