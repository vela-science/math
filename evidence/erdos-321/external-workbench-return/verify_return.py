#!/usr/bin/env python3
"""Capture a conformant external-workbench return without promoting authority."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import Any
from urllib.parse import urlparse


HERE = Path(__file__).resolve().parent
TERMINAL_VARIANTS = HERE.parent / "terminal-variants"
sys.path.insert(0, str(TERMINAL_VARIANTS))

from evidence_rooting import jcs, sha256_hex  # noqa: E402


CONTRACT_PATH = HERE / "return-contract.v0.1.json"
PACKET_PATH = HERE.parent / "workbench-compatibility" / "target-packet.json"
HEX_64 = re.compile(r"sha256:[0-9a-f]{64}\Z")
GIT_COMMIT = re.compile(r"[0-9a-f]{40}\Z")
SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:@/-]{0,127}\Z")
UTC_TIME = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z")


class ReturnError(ValueError):
    """The return does not satisfy the source-owned custody contract."""


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ReturnError("duplicate JSON key")
        result[key] = value
    return result


def sha256_root(data: bytes) -> str:
    return "sha256:" + sha256_hex(data)


def canonical_root(value: dict[str, Any]) -> str:
    return sha256_root(jcs(value))


def read_regular(path: Path, maximum: int) -> bytes:
    try:
        before = path.lstat()
    except OSError as error:
        raise ReturnError(f"missing input: {path.name}") from error
    if not stat.S_ISREG(before.st_mode) or before.st_size > maximum:
        raise ReturnError(f"input type or size drift: {path.name}")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags)
    try:
        opened = os.fstat(fd)
        if (opened.st_dev, opened.st_ino, opened.st_size) != (before.st_dev, before.st_ino, before.st_size):
            raise ReturnError(f"input identity drift: {path.name}")
        data = os.read(fd, maximum + 1)
        if len(data) > maximum or os.read(fd, 1):
            raise ReturnError(f"input exceeds size bound: {path.name}")
        after = os.fstat(fd)
        if (after.st_dev, after.st_ino, after.st_size) != (before.st_dev, before.st_ino, before.st_size):
            raise ReturnError(f"input changed during read: {path.name}")
        return data
    finally:
        os.close(fd)


def parse_json(data: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(data.decode("utf-8", errors="strict"), object_pairs_hook=unique_object)
    except (UnicodeError, json.JSONDecodeError, ReturnError) as error:
        raise ReturnError(f"strict JSON object required: {label}") from error
    if not isinstance(value, dict):
        raise ReturnError(f"strict JSON object required: {label}")
    return value


def load_contract() -> dict[str, Any]:
    contract = parse_json(read_regular(CONTRACT_PATH, 65_536), "contract")
    expected = canonical_root({key: value for key, value in contract.items() if key != "content_root"})
    if contract.get("content_root") != expected:
        raise ReturnError("contract content root drift")
    if contract.get("authority_effect") != "none" or contract.get("status") != "ready_for_external_operator":
        raise ReturnError("contract authority or status drift")
    packet_raw = read_regular(PACKET_PATH, 65_536)
    packet = parse_json(packet_raw, "target packet")
    if canonical_root({key: value for key, value in packet.items() if key != "packet_root"}) != packet.get("packet_root"):
        raise ReturnError("target packet content root drift")
    if packet["packet_root"] != contract["packet"]["packet_root"]:
        raise ReturnError("contract packet root drift")
    if sha256_root(packet_raw) != contract["packet"]["raw_sha256"]:
        raise ReturnError("contract packet raw root drift")
    return contract


def require_keys(value: dict[str, Any], expected: list[str], label: str) -> None:
    if set(value) != set(expected):
        raise ReturnError(f"{label} field drift")


def require_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not SAFE_ID.fullmatch(value):
        raise ReturnError(f"invalid {label}")
    return value


def require_https(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise ReturnError(f"invalid {label}")
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ReturnError(f"invalid {label}")
    return value


def require_utc(value: Any, label: str) -> str:
    if not isinstance(value, str) or not UTC_TIME.fullmatch(value):
        raise ReturnError(f"invalid {label}")
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as error:
        raise ReturnError(f"invalid {label}") from error
    return value


def require_unique_strings(values: Any, label: str, maximum: int, *, roots: bool = False) -> list[str]:
    if not isinstance(values, list) or len(values) > maximum or len(values) != len(set(values)):
        raise ReturnError(f"invalid {label}")
    if not all(isinstance(value, str) and value and (not roots or HEX_64.fullmatch(value)) for value in values):
        raise ReturnError(f"invalid {label}")
    return values


def validate_attestation(attestation: dict[str, Any], contract: dict[str, Any]) -> None:
    policy = contract["operator_attestation"]
    require_keys(attestation, policy["required_fields"], "operator attestation")
    if attestation["format"] != policy["format"]:
        raise ReturnError("operator attestation format drift")
    require_id(attestation["operator_id"], "operator id")
    require_id(attestation["controller_id"], "controller id")
    if attestation["relationship_to_experiment_operator"] != policy["relationship_to_experiment_operator"]:
        raise ReturnError("operator relationship does not establish separation")
    if attestation["operation_control"] != policy["operation_control"]:
        raise ReturnError("workbench operation was not separately controlled")
    if attestation["repository_authority_credentials_used"] is not False or attestation["scientific_decision_authority_used"] is not False:
        raise ReturnError("authority credentials or Decision authority were used")
    require_utc(attestation["attested_at"], "attestation time")
    require_id(attestation["identity_evidence_method"], "identity evidence method")
    require_https(attestation["identity_evidence_locator"], "identity evidence locator")
    if not isinstance(attestation["identity_evidence_root"], str) or not HEX_64.fullmatch(attestation["identity_evidence_root"]):
        raise ReturnError("invalid identity evidence root")


def validate_result(result: dict[str, Any], attestation: dict[str, Any], contract: dict[str, Any]) -> None:
    policy = contract["result"]
    require_keys(result, ["format", *policy["required_fields"]], "workbench result")
    if result["format"] != policy["format"] or result["packet_root"] != contract["packet"]["packet_root"]:
        raise ReturnError("result format or packet root drift")
    if result["authority_effect"] != "none":
        raise ReturnError("result claims an authority effect")
    if result["result_status"] not in policy["statuses"]:
        raise ReturnError("unsupported result status")
    workbench = result["workbench"]
    if not isinstance(workbench, dict):
        raise ReturnError("workbench object required")
    require_keys(workbench, policy["workbench_fields"], "workbench")
    require_id(workbench["name"], "workbench name")
    require_https(workbench["repository"], "workbench repository")
    if not isinstance(workbench["commit"], str) or not GIT_COMMIT.fullmatch(workbench["commit"]):
        raise ReturnError("invalid workbench commit")
    if require_id(workbench["operator_id"], "workbench operator id") != attestation["operator_id"]:
        raise ReturnError("result and attestation operator mismatch")
    require_id(workbench["operation_id"], "workbench operation id")
    events = require_unique_strings(result["activity_event_ids"], "activity event ids", 64)
    if result["result_status"] != "refused" and not events:
        raise ReturnError("at least one activity event is required")
    artifacts = require_unique_strings(result["artifact_roots"], "artifact roots", 64, roots=True)
    if result["result_status"] == "candidate_returned" and not artifacts:
        raise ReturnError("candidate return requires at least one artifact root")
    nonclaims = require_unique_strings(result["nonclaims"], "nonclaims", 32)
    if not set(contract["required_nonclaims"]).issubset(nonclaims):
        raise ReturnError("required nonclaims are missing")


def capture(result_path: Path, attestation_path: Path, received_at: str, custodian: str) -> dict[str, Any]:
    contract = load_contract()
    result_raw = read_regular(result_path, contract["packet"]["maximum_result_bytes"])
    attestation_raw = read_regular(attestation_path, contract["operator_attestation"]["maximum_bytes"])
    result = parse_json(result_raw, "workbench result")
    attestation = parse_json(attestation_raw, "operator attestation")
    validate_attestation(attestation, contract)
    validate_result(result, attestation, contract)
    require_utc(received_at, "receipt time")
    custodian = require_id(custodian, "custodian")
    receipt = {
        "attestation_content_root": canonical_root(attestation),
        "attestation_raw_sha256": sha256_root(attestation_raw),
        "authority_effect": "none",
        "contract_root": contract["content_root"],
        "custodian": custodian,
        "externality_status": contract["receipt"]["externality_status"],
        "format": contract["receipt"]["format"],
        "limitations": [
            "This receipt proves local schema, root, and nonclaim conformance only.",
            "The operator separation statement is retained as an attestation and is not independently verified by this tool.",
            "No scientific correctness, Submission, Verification, Decision, Event, Standing, human acceptance, or adoption is established.",
        ],
        "operator_id": attestation["operator_id"],
        "packet_root": contract["packet"]["packet_root"],
        "received_at": received_at,
        "result_content_root": canonical_root(result),
        "result_raw_sha256": sha256_root(result_raw),
        "result_status": result["result_status"],
        "scientific_status": contract["receipt"]["scientific_status_by_result"][result["result_status"]],
    }
    receipt["content_root_definition"] = "sha256 of RFC-8785 JSON after removing only content_root"
    receipt["content_root"] = canonical_root(receipt)
    return receipt


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--result", type=Path, required=True)
    result.add_argument("--operator-attestation", type=Path, required=True)
    result.add_argument("--received-at", required=True)
    result.add_argument("--custodian", required=True)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    receipt = capture(args.result, args.operator_attestation, args.received_at, args.custodian)
    sys.stdout.buffer.write(jcs(receipt) + b"\n")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ReturnError) as error:
        print(f"external_workbench_return_refused: {error}", file=sys.stderr)
        raise SystemExit(1) from error
