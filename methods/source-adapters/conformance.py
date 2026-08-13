#!/usr/bin/env python3
"""Small, source-local conformance contract for Vela source adapters.

This is producer and projection metadata. It is not a Vela protocol object and
has no authority effect.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping


PROFILE_SCHEMA = "vela.source-adapter-conformance-profile.v1"
PROFILE_ROOT_DEFINITION = "sha256 of canonical JSON after removing only profile_root"
REQUIRED_REQUIREMENT_IDS = frozenset({
    "unsupported_schema_and_version_refusal",
    "field_and_schema_typed_roots",
    "exact_source_revision_and_drift",
    "complete_bounded_reads",
    "copied_or_referenced_custody",
    "interpreting_implementation_identity",
    "license_access_and_public_redaction",
    "reconstructibility_and_loss",
    "deletion_tombstone_and_mutability",
})

_HASH_ROOT = re.compile(r"^sha256:[0-9a-f]{64}$")
_SOURCE_ID = re.compile(r"^source:[a-z0-9]+(?:-[a-z0-9]+)*$")
_ADAPTER_ID = re.compile(r"^[a-z][a-z0-9]*(?:[./-][a-z0-9]+)*$")
_VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
_ROOT_DOMAIN = re.compile(r"^[a-z][a-z0-9_]*$")


class ConformanceError(ValueError):
    """Raised when an adapter profile is incomplete, contradictory, or stale."""


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ConformanceError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def canonical_bytes(value: Any) -> bytes:
    """Canonical bytes for this I-JSON profile (which deliberately has no floats)."""
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def sha256(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def profile_root(value: Mapping[str, Any]) -> str:
    body = copy.deepcopy(dict(value))
    body.pop("profile_root", None)
    return sha256(canonical_bytes(body))


def finalize_profile(body: Mapping[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(dict(body))
    value["profile_root"] = profile_root(value)
    return validate_profile(value)


def _object(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ConformanceError(f"{label} field inventory drift")
    return value


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConformanceError(f"{label} must be a non-empty string")
    return value


def _text_list(value: Any, label: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not value and not allow_empty):
        raise ConformanceError(f"{label} must be a {'possibly empty' if allow_empty else 'non-empty'} list")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ConformanceError(f"{label} entries must be non-empty strings")
    if len(value) != len(set(value)):
        raise ConformanceError(f"{label} entries must be unique")
    return value


def _root(value: Any, label: str) -> str:
    if not isinstance(value, str) or _HASH_ROOT.fullmatch(value) is None:
        raise ConformanceError(f"{label} must be a full SHA-256 root")
    return value


def _relative_path(value: Any, label: str) -> str:
    path = Path(_text(value, label))
    if path.is_absolute() or ".." in path.parts or path.as_posix() in {"", "."}:
        raise ConformanceError(f"{label} must be a safe repository-relative path")
    return path.as_posix()


def validate_profile(input_value: Any) -> dict[str, Any]:
    value = _object(input_value, {
        "schema", "adapter", "native_identity", "roots", "read_contract",
        "custody", "rights", "semantics", "lifecycle", "field_classes",
        "reconstructibility", "writeback", "requirement_evidence",
        "authority_effect", "profile_root_definition", "profile_root",
    }, "adapter conformance profile")
    if value["schema"] != PROFILE_SCHEMA:
        raise ConformanceError("unsupported adapter conformance profile schema")
    if value["authority_effect"] != "none":
        raise ConformanceError("adapter conformance profiles cannot carry authority")
    if value["profile_root_definition"] != PROFILE_ROOT_DEFINITION:
        raise ConformanceError("adapter conformance profile root definition drift")
    if _root(value["profile_root"], "profile_root") != profile_root(value):
        raise ConformanceError("adapter conformance profile root drift")

    adapter = _object(value["adapter"], {
        "adapter_id", "version", "implementation_path", "implementation_root",
        "output_schema",
    }, "adapter identity")
    if _ADAPTER_ID.fullmatch(_text(adapter["adapter_id"], "adapter_id")) is None:
        raise ConformanceError("invalid adapter_id")
    if _VERSION.fullmatch(_text(adapter["version"], "adapter version")) is None:
        raise ConformanceError("invalid adapter version")
    _relative_path(adapter["implementation_path"], "implementation_path")
    _root(adapter["implementation_root"], "implementation_root")
    _text(adapter["output_schema"], "output_schema")

    native = _object(value["native_identity"], {
        "source_id", "object_identity", "revision_semantics", "mapping_semantics",
    }, "native identity")
    if _SOURCE_ID.fullmatch(_text(native["source_id"], "source_id")) is None:
        raise ConformanceError("invalid source_id")
    _text_list(native["object_identity"], "native object identity")
    _text(native["revision_semantics"], "native revision semantics")
    if native["mapping_semantics"] not in {
        "exact_native_identity_only",
        "versioned_mapping_with_alias_history",
        "source_declared_aliases_merges_and_splits",
    }:
        raise ConformanceError("unsupported native mapping semantics")

    roots = _object(value["roots"], {"content", "observation"}, "root contract")
    for axis in ("content", "observation"):
        descriptors = roots[axis]
        if not isinstance(descriptors, list) or not descriptors:
            raise ConformanceError(f"{axis} roots must be declared")
        fields: set[str] = set()
        for descriptor in descriptors:
            item = _object(descriptor, {"field", "domain", "meaning"}, f"{axis} root")
            field = _text(item["field"], f"{axis} root field")
            if field in fields:
                raise ConformanceError(f"duplicate {axis} root field")
            fields.add(field)
            if _ROOT_DOMAIN.fullmatch(_text(item["domain"], f"{axis} root domain")) is None:
                raise ConformanceError(f"invalid {axis} root domain")
            _text(item["meaning"], f"{axis} root meaning")

    reads = _object(value["read_contract"], {
        "completeness", "scope", "pagination", "max_records",
        "max_bytes_per_record", "bounded_read_behavior",
    }, "read contract")
    if reads["completeness"] not in {"complete", "partial"}:
        raise ConformanceError("read completeness must be complete or partial")
    _text(reads["scope"], "read scope")
    _text(reads["pagination"], "pagination semantics")
    if type(reads["max_records"]) is not int or reads["max_records"] < 1:
        raise ConformanceError("max_records must be a positive integer")
    if type(reads["max_bytes_per_record"]) is not int or reads["max_bytes_per_record"] < 1:
        raise ConformanceError("max_bytes_per_record must be a positive integer")
    if reads["bounded_read_behavior"] not in {"refuse", "explicit_partial"}:
        raise ConformanceError("unsupported bounded-read behavior")

    custody = _object(value["custody"], {
        "mode", "source_locator", "retained_bytes", "copied", "referenced",
    }, "custody")
    if custody["mode"] not in {"copied", "referenced", "mixed"}:
        raise ConformanceError("unsupported custody mode")
    locator = _text(custody["source_locator"], "source locator")
    if not locator.startswith("https://"):
        raise ConformanceError("source locator must use HTTPS")
    if not isinstance(custody["retained_bytes"], bool):
        raise ConformanceError("retained_bytes must be boolean")
    copied = _text_list(custody["copied"], "copied custody", allow_empty=True)
    referenced = _text_list(custody["referenced"], "referenced custody", allow_empty=True)
    if custody["mode"] == "copied" and (not copied or referenced):
        raise ConformanceError("copied custody must name copied bytes only")
    if custody["mode"] == "referenced" and (copied or not referenced):
        raise ConformanceError("referenced custody must name references only")
    if custody["mode"] == "mixed" and (not copied or not referenced):
        raise ConformanceError("mixed custody must name copied and referenced material")

    rights = _object(value["rights"], {
        "license", "access", "redistribution", "public_redaction",
    }, "rights")
    if rights["license"] is not None:
        _text(rights["license"], "license")
    if rights["access"] not in {"public", "restricted", "local"}:
        raise ConformanceError("unsupported access policy")
    if rights["redistribution"] not in {
        "full_under_license", "reference_only", "existing_repository_only",
    }:
        raise ConformanceError("unsupported redistribution policy")
    if rights["license"] is None and rights["redistribution"] == "full_under_license":
        raise ConformanceError("full redistribution requires a declared license")
    _text(rights["public_redaction"], "public redaction policy")

    semantics = _object(value["semantics"], {
        "preserves", "omits", "unsupported_states", "fail_closed_behavior",
        "nonclaims",
    }, "semantics")
    _text_list(semantics["preserves"], "preserved semantics")
    _text_list(semantics["omits"], "omitted semantics")
    _text_list(semantics["unsupported_states"], "unsupported source states")
    _text(semantics["fail_closed_behavior"], "fail-closed behavior")
    _text_list(semantics["nonclaims"], "adapter nonclaims")

    lifecycle = _object(value["lifecycle"], {
        "deletion", "tombstone", "update_detection", "drift_response",
    }, "lifecycle")
    for field in lifecycle:
        _text(lifecycle[field], f"lifecycle {field}")

    field_classes = value["field_classes"]
    if not isinstance(field_classes, list) or not field_classes:
        raise ConformanceError("source field mutability classes must be declared")
    seen_paths: set[str] = set()
    for descriptor in field_classes:
        item = _object(descriptor, {"path", "mutability", "meaning"}, "field class")
        path = _text(item["path"], "field class path")
        if path in seen_paths:
            raise ConformanceError("duplicate field class path")
        seen_paths.add(path)
        if item["mutability"] not in {"immutable", "mutable", "observation_time_only"}:
            raise ConformanceError("unsupported source field mutability")
        _text(item["meaning"], "field class meaning")
    if "immutable" not in {item["mutability"] for item in field_classes}:
        raise ConformanceError("at least one immutable source field class is required")

    reconstructibility = _object(value["reconstructibility"], {
        "possible", "unavailable",
    }, "reconstructibility")
    _text_list(reconstructibility["possible"], "reconstructible facts")
    _text_list(reconstructibility["unavailable"], "unreconstructible facts")

    writeback = _object(value["writeback"], {"mode", "path", "nonclaim"}, "writeback")
    if writeback["mode"] not in {"none", "documented", "implemented"}:
        raise ConformanceError("unsupported writeback mode")
    if writeback["path"] is not None:
        _text(writeback["path"], "writeback path")
    if writeback["mode"] != "none" and writeback["path"] is None:
        raise ConformanceError("documented or implemented writeback requires a path")
    _text(writeback["nonclaim"], "writeback nonclaim")

    evidence = value["requirement_evidence"]
    if not isinstance(evidence, dict) or set(evidence) != REQUIRED_REQUIREMENT_IDS:
        raise ConformanceError("adapter conformance requirement inventory drift")
    for requirement_id, test_ids in evidence.items():
        _text_list(test_ids, f"requirement evidence {requirement_id}")

    return copy.deepcopy(value)


def load_profile(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if not raw.endswith(b"\n") or raw.endswith(b"\n\n"):
        raise ConformanceError("adapter conformance profile must have exactly one trailing LF")
    try:
        value = json.loads(raw, object_pairs_hook=_unique_object)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ConformanceError("adapter conformance profile is not strict UTF-8 JSON") from error
    profile = validate_profile(value)
    if raw != canonical_bytes(profile) + b"\n":
        raise ConformanceError("adapter conformance profile is not canonically framed")
    return profile


def assert_requirement_coverage(
    profile: Mapping[str, Any],
    observed: Mapping[str, set[str]],
) -> None:
    validate_profile(profile)
    if set(observed) != REQUIRED_REQUIREMENT_IDS:
        raise ConformanceError("observed adapter requirement inventory drift")
    for requirement_id in REQUIRED_REQUIREMENT_IDS:
        declared = set(profile["requirement_evidence"][requirement_id])
        actual = observed[requirement_id]
        if not actual or declared != actual:
            raise ConformanceError(f"adapter evidence drift for {requirement_id}")


__all__ = [
    "ConformanceError", "PROFILE_ROOT_DEFINITION", "PROFILE_SCHEMA",
    "REQUIRED_REQUIREMENT_IDS", "assert_requirement_coverage", "canonical_bytes",
    "finalize_profile", "load_profile", "profile_root", "sha256", "validate_profile",
]
