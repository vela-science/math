#!/usr/bin/env python3
"""Strict, offline projection of retained Formal Conjectures PR audit records."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
RETAINED_ROOT = HERE / "retained-source"
METHOD_PATH = REPO_ROOT / "methods/formal-conjectures/pr-audit-source-adapter.v0.1.json"
CONFORMANCE_CONTRACT_PATH = REPO_ROOT / "methods/source-adapters/conformance.py"
CONFORMANCE_PROFILE_PATH = HERE / "conformance-profile.v1.json"
PROJECTION_PATH = HERE / "projection.v1.json"
SOURCE_VALIDATOR_PATH = RETAINED_ROOT / "scripts/pr_audit.py"
SOURCE_VALIDATOR_SHA256 = "sha256:f18be0d9db226e2a5545309287212d49a652d111d032483886f98d4c9f897a66"
METHOD_SCHEMA = "vela.math.fc-pr-audit-source-adapter-method.v0.1"
PROJECTION_SCHEMA = "vela.math.fc-pr-audit-projection.v1"
SOURCE_CORE_SCHEMA = "formal-conjectures.pr-audit.v1"
SOURCE_OBSERVATION_SCHEMA = "formal-conjectures.pr-audit-observation.v1"
ROOT_DOMAINS = {"artifact", "fc_audit_core", "fc_audit_observation", "projection", "source_content"}
EXPECTED_SOURCE_REPOSITORY = "https://github.com/google-deepmind/formal-conjectures"
MAX_FIXTURES = 5


class AdapterError(ValueError):
    """Raised when source bytes cannot safely produce the bounded projection."""


def _sha256(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _load_source_validator() -> Any:
    if _sha256(SOURCE_VALIDATOR_PATH.read_bytes()) != SOURCE_VALIDATOR_SHA256:
        raise AdapterError("retained source validator root drift")
    spec = importlib.util.spec_from_file_location("retained_fc_pr_audit", SOURCE_VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise AdapterError("cannot load retained source validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SOURCE = _load_source_validator()


def _load_conformance_contract() -> Any:
    spec = importlib.util.spec_from_file_location(
        "vela_source_adapter_conformance",
        CONFORMANCE_CONTRACT_PATH,
    )
    if spec is None or spec.loader is None:
        raise AdapterError("cannot load source-adapter conformance contract")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CONFORMANCE = _load_conformance_contract()


def _strict_file(path: Path, label: str) -> tuple[bytes, Any]:
    raw = path.read_bytes()
    if not raw.endswith(b"\n") or raw.endswith(b"\n\n"):
        raise AdapterError(f"{label} must have exactly one trailing LF")
    try:
        value = SOURCE.parse_json_bytes(raw, label=label)
    except SOURCE.AuditError as error:
        raise AdapterError(str(error)) from error
    return raw, value


def _typed_root(domain: str, value: str) -> dict[str, str]:
    if domain not in ROOT_DOMAINS:
        raise AdapterError(f"unsupported root domain: {domain}")
    if not isinstance(value, str) or len(value) != 71 or not value.startswith("sha256:"):
        raise AdapterError(f"invalid full SHA-256 root for {domain}")
    try:
        int(value[7:], 16)
    except ValueError as error:
        raise AdapterError(f"invalid full SHA-256 root for {domain}") from error
    return {"domain": domain, "value": value}


def _expect_exact_keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise AdapterError(f"{label} field inventory drift")


def _method_root(method: dict[str, Any]) -> str:
    payload = copy.deepcopy(method)
    payload.pop("method_root", None)
    return SOURCE.content_root(payload)


def load_conformance_profile() -> dict[str, Any]:
    try:
        return CONFORMANCE.load_profile(CONFORMANCE_PROFILE_PATH)
    except CONFORMANCE.ConformanceError as error:
        raise AdapterError(str(error)) from error


def load_method() -> dict[str, Any]:
    _, value = _strict_file(METHOD_PATH, "adapter method")
    if not isinstance(value, dict):
        raise AdapterError("adapter method must be an object")
    if value.get("schema") != METHOD_SCHEMA:
        raise AdapterError("unsupported adapter method schema")
    if value.get("method_root_definition") != "sha256 of canonical JSON after removing only method_root":
        raise AdapterError("adapter method root definition drift")
    if value.get("method_root") != _method_root(value):
        raise AdapterError("adapter method root drift")
    if value.get("authority_effect") != "none":
        raise AdapterError("adapter method cannot carry authority")
    if value["supported_source_schemas"] != {
        "core": SOURCE_CORE_SCHEMA,
        "observation": SOURCE_OBSERVATION_SCHEMA,
    }:
        raise AdapterError("supported source schema inventory drift")
    limits = value["limits"]
    if limits != {
        "fixture_count": 5,
        "max_fixture_count": 5,
        "max_record_bytes": 2097152,
        "pagination": "none_complete_closed_inventory",
    }:
        raise AdapterError("adapter limit contract drift")
    profile = load_conformance_profile()
    expected_adapter = {
        "adapter_id": value["adapter"]["name"],
        "version": value["adapter"]["version"],
        "implementation_path": value["adapter"]["implementation_path"],
        "implementation_root": _sha256(HERE.joinpath("adapter.py").read_bytes()),
        "output_schema": value["adapter"]["output_schema"],
    }
    if profile["adapter"] != expected_adapter:
        raise AdapterError("adapter conformance implementation identity drift")
    if profile["native_identity"]["source_id"] != value["source"]["source_id"]:
        raise AdapterError("adapter conformance source identity drift")
    if profile["custody"]["source_locator"] != (
        value["source"]["repository"] + "/tree/" + value["source"]["commit"]
    ):
        raise AdapterError("adapter conformance source revision locator drift")
    if profile["custody"]["mode"] != "copied" or profile["custody"]["retained_bytes"] is not True:
        raise AdapterError("adapter conformance custody drift")
    if profile["read_contract"] != {
        "completeness": "complete",
        "scope": "The five frozen Formal Conjectures PR-audit fixtures and their exact core and observation records.",
        "pagination": value["limits"]["pagination"],
        "max_records": value["limits"]["max_fixture_count"],
        "max_bytes_per_record": value["limits"]["max_record_bytes"],
        "bounded_read_behavior": "refuse",
    }:
        raise AdapterError("adapter conformance read contract drift")
    if profile["rights"] != {
        "license": value["source"]["license"],
        "access": value["source"]["access"],
        "redistribution": "full_under_license",
        "public_redaction": "Only public source records are retained; GitHub request IDs, transport receipts, and reviewer identities are omitted from the Math projection.",
    }:
        raise AdapterError("adapter conformance rights drift")
    if profile["semantics"]["preserves"] != value["preserves"]:
        raise AdapterError("adapter conformance preserved semantics drift")
    if profile["semantics"]["omits"] != value["omits"]:
        raise AdapterError("adapter conformance omitted semantics drift")
    if profile["reconstructibility"]["unavailable"] != value["unreconstructible_from_projection"]:
        raise AdapterError("adapter conformance reconstruction-loss drift")
    if profile["lifecycle"] != {
        "deletion": value["mutation_policy"]["disappearance"],
        "tombstone": "A later source observation may report absence, but this immutable projection is never rewritten as a tombstone.",
        "update_detection": "A new exact source commit, tree, or retained file root requires a new projection.",
        "drift_response": value["mutation_policy"]["replacement"],
    }:
        raise AdapterError("adapter conformance lifecycle drift")
    return value


def _verify_retained_inventory(method: dict[str, Any]) -> dict[str, str]:
    declared = method["retained_files"]
    if not isinstance(declared, list) or not declared:
        raise AdapterError("retained source inventory is empty")
    roots: dict[str, str] = {}
    for item in declared:
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            raise AdapterError("retained source descriptor shape drift")
        path = item["path"]
        if not isinstance(path, str) or path.startswith("/") or ".." in Path(path).parts:
            raise AdapterError("unsafe retained source path")
        if path in roots:
            raise AdapterError("duplicate retained source path")
        roots[path] = _typed_root("source_content", item["sha256"])["value"]
    observed = sorted(
        path.relative_to(RETAINED_ROOT).as_posix()
        for path in RETAINED_ROOT.rglob("*")
        if path.is_file()
    )
    if observed != sorted(roots):
        raise AdapterError("retained source directory inventory drift")
    for relative, expected in roots.items():
        raw = (RETAINED_ROOT / relative).read_bytes()
        if len(raw) > method["limits"]["max_record_bytes"]:
            raise AdapterError(f"retained source file exceeds byte bound: {relative}")
        if _sha256(raw) != expected:
            raise AdapterError(f"retained source root drift: {relative}")
    return roots


def _project_rooted_item(item: dict[str, Any], root_field: str) -> dict[str, Any]:
    projected = copy.deepcopy(item)
    projected[root_field] = _typed_root("source_content", projected[root_field])
    return projected


def _project_check(check: dict[str, Any]) -> dict[str, Any]:
    expected = {
        "assumptions", "conditions", "does_not_establish", "evidence", "id",
        "implementation", "inputs", "kind", "limitations", "mode", "outcome",
        "proofs", "property", "role", "scope", "severity",
    }
    _expect_exact_keys(check, expected, f"source check {check.get('id', '<unknown>')}")
    implementation = copy.deepcopy(check["implementation"])
    implementation["root"] = _typed_root("source_content", implementation["root"])
    inputs = [_project_rooted_item(item, "root") for item in check["inputs"]]
    evidence = []
    for item in check["evidence"]:
        projected = copy.deepcopy(item)
        projected["content_root"] = _typed_root("source_content", projected.pop("sha256"))
        evidence.append(projected)
    return {
        "id": check["id"],
        "property": check["property"],
        "outcome": check["outcome"],
        "severity": check["severity"],
        "kind": check["kind"],
        "mode": check["mode"],
        "role": check["role"],
        "scope": copy.deepcopy(check["scope"]),
        "implementation": implementation,
        "inputs": inputs,
        "evidence": evidence,
        "proofs": copy.deepcopy(check["proofs"]),
        "conditions": copy.deepcopy(check["conditions"]),
        "assumptions": copy.deepcopy(check["assumptions"]),
        "limitations": copy.deepcopy(check["limitations"]),
        "does_not_establish": copy.deepcopy(check["does_not_establish"]),
        "protocol_conversion": {
            "automatic": False,
            "outcome": None,
            "requires": "separate tracked Math method, eligible verifier, exact inputs, local signing, and Repository policy",
        },
    }


def _record_root(record: dict[str, Any]) -> dict[str, str]:
    payload = copy.deepcopy(record)
    payload.pop("root", None)
    return _typed_root("projection", SOURCE.content_root(payload))


def _build_record(
    fixture: dict[str, Any], method: dict[str, Any], retained_roots: dict[str, str]
) -> dict[str, Any]:
    fixture_id = fixture["id"]
    core_path = fixture["core_path"]
    observation_path = fixture["observation_path"]
    core_raw, core_value = _strict_file(RETAINED_ROOT / core_path, f"{fixture_id} core")
    observation_raw, observation_value = _strict_file(
        RETAINED_ROOT / observation_path, f"{fixture_id} observation"
    )
    try:
        core = SOURCE.validate_core(core_value)
        observation = SOURCE.validate_observation(observation_value)
    except SOURCE.AuditError as error:
        raise AdapterError(f"{fixture_id}: {error}") from error
    if core_raw != SOURCE.canonical_bytes(core) + b"\n":
        raise AdapterError(f"{fixture_id}: core is not canonical source framing")
    if observation_raw != SOURCE.canonical_bytes(observation) + b"\n":
        raise AdapterError(f"{fixture_id}: observation is not canonical source framing")
    repository = core["repository"]
    native_repository = repository["repository"]
    pull_request = repository["pull_request"]
    observed_pr = observation["pull_request"]
    if native_repository["url"] != EXPECTED_SOURCE_REPOSITORY:
        raise AdapterError(f"{fixture_id}: native repository identity drift")
    if pull_request["number"] != fixture["pull_request"] or observed_pr["number"] != fixture["pull_request"]:
        raise AdapterError(f"{fixture_id}: pull-request identity drift")
    if pull_request["url"] != observed_pr["url"]:
        raise AdapterError(f"{fixture_id}: pull-request locator drift")
    if repository["base"]["commit_oid"] != observed_pr["base_commit_oid"]:
        raise AdapterError(f"{fixture_id}: base commit drift")
    if repository["head"]["commit_oid"] != observed_pr["head_commit_oid"]:
        raise AdapterError(f"{fixture_id}: head commit drift")
    if observation["core"] != {
        "root": core["root"],
        "sha256": _sha256(core_raw),
    }:
        raise AdapterError(f"{fixture_id}: observation does not bind exact core")
    if retained_roots[core_path] != _sha256(core_raw) or retained_roots[observation_path] != _sha256(observation_raw):
        raise AdapterError(f"{fixture_id}: retained descriptor drift")
    changes = []
    for change in repository["changes"]:
        changes.append({
            "path": change["path"],
            "status": change["status"],
            "base_blob_oid": change["base_blob_oid"],
            "base_content_root": None if change["base_blob_sha256"] is None else _typed_root("source_content", change["base_blob_sha256"]),
            "head_blob_oid": change["head_blob_oid"],
            "head_content_root": None if change["head_blob_sha256"] is None else _typed_root("source_content", change["head_blob_sha256"]),
        })
    record = {
        "schema": "vela.math.fc-pr-audit-record.v1",
        "fixture_id": fixture_id,
        "native_identity": {
            "repository": native_repository,
            "pull_request": pull_request,
            "base": repository["base"],
            "head": repository["head"],
            "comparison": repository["comparison"],
            "changes": changes,
        },
        "source_records": {
            "core": {
                "path": core_path,
                "file_root": _typed_root("source_content", _sha256(core_raw)),
                "record_root": _typed_root("fc_audit_core", core["root"]),
            },
            "observation": {
                "path": observation_path,
                "file_root": _typed_root("source_content", _sha256(observation_raw)),
                "record_root": _typed_root("fc_audit_observation", observation["root"]),
            },
        },
        "source_axis": {
            "advisory_disposition": core["disposition"]["advisory"],
            "basis_check_ids": core["disposition"]["basis_check_ids"],
            "nonclaims": core["disposition"]["nonclaims"],
            "checks": [_project_check(check) for check in core["checks"]],
            "observed_pull_request_state": {
                "state": observed_pr["state"],
                "is_draft": observed_pr["is_draft"],
                "merge_state_status": observed_pr["merge_state_status"],
                "review_decision": observed_pr["review_decision"],
                "updated_at": observed_pr["updated_at"],
                "review_count": len(observed_pr["reviews"]),
            },
        },
        "custody": {
            "mode": "copied",
            "access": method["source"]["access"],
            "license": method["source"]["license"],
            "source_commit": method["source"]["commit"],
            "source_tree": method["source"]["tree"],
        },
        "authority_effect": "none",
        "standing_effect": "none",
        "automatic_verification": False,
        "loss": {
            "preserves": method["preserves"],
            "omits": method["omits"],
            "unreconstructible_from_projection": method["unreconstructible_from_projection"],
        },
    }
    record["root"] = _record_root(record)
    return record


def build_projection() -> dict[str, Any]:
    method = load_method()
    conformance_profile = load_conformance_profile()
    retained_roots = _verify_retained_inventory(method)
    fixtures = method["fixtures"]
    if len(fixtures) != MAX_FIXTURES or len(fixtures) > method["limits"]["max_fixture_count"]:
        raise AdapterError("fixture inventory is truncated or over bound")
    fixture_ids = [fixture["id"] for fixture in fixtures]
    pull_requests = [fixture["pull_request"] for fixture in fixtures]
    if len(fixture_ids) != len(set(fixture_ids)) or len(pull_requests) != len(set(pull_requests)):
        raise AdapterError("duplicate fixture or native identity")
    interpreter_raw = Path(__file__).read_bytes()
    records = [_build_record(fixture, method, retained_roots) for fixture in fixtures]
    projection = {
        "schema": PROJECTION_SCHEMA,
        "source": {
            "source_id": method["source"]["source_id"],
            "repository": method["source"]["repository"],
            "commit": method["source"]["commit"],
            "tree": method["source"]["tree"],
            "access": method["source"]["access"],
            "license": method["source"]["license"],
            "custody": method["source"]["custody"],
            "retained_files": [
                {"path": item["path"], "root": _typed_root("source_content", item["sha256"])}
                for item in method["retained_files"]
            ],
        },
        "interpreter": {
            "name": method["adapter"]["name"],
            "version": method["adapter"]["version"],
            "path": method["adapter"]["implementation_path"],
            "root": _typed_root("artifact", _sha256(interpreter_raw)),
            "method_path": METHOD_PATH.relative_to(REPO_ROOT).as_posix(),
            "method_root": _typed_root("artifact", method["method_root"]),
            "source_validator": {
                "path": "retained-source/scripts/pr_audit.py",
                "root": _typed_root("artifact", SOURCE_VALIDATOR_SHA256),
            },
        },
        "conformance": {
            "schema": conformance_profile["schema"],
            "profile_path": CONFORMANCE_PROFILE_PATH.relative_to(REPO_ROOT).as_posix(),
            "profile_root": _typed_root("artifact", conformance_profile["profile_root"]),
            "contract_path": CONFORMANCE_CONTRACT_PATH.relative_to(REPO_ROOT).as_posix(),
            "contract_root": _typed_root(
                "artifact",
                _sha256(CONFORMANCE_CONTRACT_PATH.read_bytes()),
            ),
            "authority_effect": "none",
        },
        "read_contract": {
            "complete": True,
            "fixture_count": len(records),
            "max_fixture_count": method["limits"]["max_fixture_count"],
            "pagination": method["limits"]["pagination"],
            "update_detection": "new exact source commit, tree, or retained file root requires a new projection",
            "mutation_policy": method["mutation_policy"],
        },
        "records": records,
        "authority_effect": "none",
        "does_not_establish": [
            "a Formal Conjectures audit is a Vela Verification",
            "a source review, approval, merge, or publication is a Vela Decision",
            "any local Math Standing",
            "clean or source-faithful ground truth for the candidate fixture",
            "external adoption or independent validation",
        ],
    }
    projection["root"] = _record_root(projection)
    return projection


def validate_projection(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AdapterError("projection must be one object")
    expected = {
        "schema", "source", "interpreter", "conformance", "read_contract", "records",
        "authority_effect", "does_not_establish", "root",
    }
    _expect_exact_keys(value, expected, "projection")
    if value["schema"] != PROJECTION_SCHEMA:
        raise AdapterError("unsupported projection schema")
    if value["authority_effect"] != "none":
        raise AdapterError("projection cannot carry authority")
    if value["root"] != _record_root(value):
        raise AdapterError("projection root drift")
    rebuilt = build_projection()
    if value != rebuilt:
        raise AdapterError("projection does not match exact retained source and interpreter")
    if any(record["automatic_verification"] is not False for record in value["records"]):
        raise AdapterError("automatic Verification conversion is forbidden")
    for record in value["records"]:
        for check in record["source_axis"]["checks"]:
            if check["protocol_conversion"]["automatic"] is not False or check["protocol_conversion"]["outcome"] is not None:
                raise AdapterError("source outcome collapsed into protocol Verification")
    return copy.deepcopy(value)


def write_projection(path: Path = PROJECTION_PATH) -> dict[str, Any]:
    projection = build_projection()
    path.write_bytes(SOURCE.canonical_bytes(projection) + b"\n")
    return projection


__all__ = [
    "AdapterError", "CONFORMANCE_PROFILE_PATH", "METHOD_PATH", "PROJECTION_PATH",
    "build_projection", "load_conformance_profile", "load_method",
    "validate_projection", "write_projection",
]
