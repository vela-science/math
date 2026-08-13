#!/usr/bin/env python3
"""Verify the exact Erdős 887 pilot result without granting authority."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
RESULT = HERE / "result.v1.json"
CHECK = HERE / "lean-check.v1.json"
PATCH = HERE / "repair.patch"
PACKET = HERE.parents[1] / "packets/erdos-887-pr-1237-fidelity-repair.v1.json"


class ResultError(ValueError):
    pass


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ResultError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if not raw.endswith(b"\n") or raw.endswith(b"\n\n"):
        raise ResultError(f"{path.name} must have exactly one trailing LF")
    value = json.loads(raw, object_pairs_hook=unique_object)
    if not isinstance(value, dict):
        raise ResultError(f"{path.name} must contain one JSON object")
    if raw != canonical(value) + b"\n":
        raise ResultError(f"{path.name} must use canonical JSON framing")
    return value


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()


def root(value: dict[str, Any], field: str) -> str:
    preimage = copy.deepcopy(value)
    preimage.pop(field, None)
    return "sha256:" + hashlib.sha256(canonical(preimage)).hexdigest()


def raw_root(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def historical_packet_root(packet: dict[str, Any]) -> str:
    """Recover the pre-execution-component packet root used by pilot 01."""
    historical = copy.deepcopy(packet)
    historical.pop("execution_components", None)
    historical["expected_return"]["required_fields"] = [
        "target_id",
        "packet_root",
        "producer",
        "result_status",
        "source_patch_root",
        "check_result_root",
        "semantic_review",
        "source_roots",
        "nonclaims",
    ]
    return root(historical, "packet_root")


def verify() -> dict[str, Any]:
    packet = load(PACKET)
    check = load(CHECK)
    result = load(RESULT)
    patch_raw = PATCH.read_bytes()
    if result.get("schema") != "vela.math.fidelity-repair-result.v1":
        raise ResultError("unsupported result schema")
    if check.get("schema") != "vela.math.lean-source-check.v1":
        raise ResultError("unsupported check schema")
    if result.get("authority_effect") != "none" or check.get("authority_effect") != "none":
        raise ResultError("result or check claims authority")
    if result.get("target_id") != packet["target"]["id"] or result.get("packet_root") != historical_packet_root(packet):
        raise ResultError("Target or packet root drift")
    expected_patch_root = raw_root(patch_raw)
    if result.get("source_patch_root") != expected_patch_root:
        raise ResultError("source patch root drift")
    if result["artifacts"]["source_patch"] != {
        "path": "repair.patch", "raw_sha256": expected_patch_root, "size": len(patch_raw)
    }:
        raise ResultError("source patch artifact drift")
    if check.get("check_result_root") != root(check, "check_result_root"):
        raise ResultError("check result root drift")
    if result.get("check_result_root") != check["check_result_root"]:
        raise ResultError("result/check binding drift")
    if result["artifacts"]["lean_check"] != {"path": "lean-check.v1.json", "root": check["check_result_root"]}:
        raise ResultError("Lean check artifact drift")
    if check["source"]["patch_raw_sha256"] != expected_patch_root:
        raise ResultError("Lean check patch binding drift")
    if result.get("result_status") != "candidate_ready_for_human_review":
        raise ResultError("unsupported result status")
    review = result.get("semantic_review")
    if review != {
        "independent": False,
        "required": True,
        "reviewer": None,
        "status": "pending",
        "witness": "The candidate moves answer(sorry) outside the C and n binders and makes it the truth value of the intended existential absolute-K statement; this is an agent-prepared rationale awaiting human confirmation.",
    }:
        raise ResultError("pending semantic review boundary drift")
    if result.get("result_root") != root(result, "result_root"):
        raise ResultError("result root drift")
    return result


if __name__ == "__main__":
    verified = verify()
    print(json.dumps({"result_root": verified["result_root"], "status": verified["result_status"]}, sort_keys=True))
