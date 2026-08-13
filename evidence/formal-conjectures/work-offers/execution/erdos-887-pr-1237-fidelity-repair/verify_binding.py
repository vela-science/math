#!/usr/bin/env python3
"""Verify the public Erdős 887 execution binding and an optional result."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
WORK_OFFERS = HERE.parents[1]
REPO_ROOT = WORK_OFFERS.parents[2]
PACKET = WORK_OFFERS / "packets/erdos-887-pr-1237-fidelity-repair.v1.json"
INDEX = WORK_OFFERS / "index.v1.json"

ROOT_FIELDS = {
    "producer_profile": "profile_root",
    "verifier_capsule": "verifier_capsule_root",
    "result_contract": "result_contract_root",
}


class BindingError(ValueError):
    pass


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise BindingError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def load(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    if not raw.endswith(b"\n") or raw.endswith(b"\n\n"):
        raise BindingError(f"{path} must have exactly one trailing LF")
    try:
        value = json.loads(raw, object_pairs_hook=unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise BindingError(f"invalid JSON at {path}: {error}") from error
    if not isinstance(value, dict) or raw != canonical(value) + b"\n":
        raise BindingError(f"{path} must contain one canonical JSON object")
    return value, raw


def rooted(value: dict[str, Any], field: str) -> str:
    preimage = copy.deepcopy(value)
    preimage.pop(field, None)
    return "sha256:" + hashlib.sha256(canonical(preimage)).hexdigest()


def raw_root(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def full_sha256_root(value: Any) -> bool:
    return (
        isinstance(value, str)
        and value.startswith("sha256:")
        and len(value) == 71
        and all(character in "0123456789abcdef" for character in value[7:])
    )


def result_artifact_path(result_path: Path, locator: Any) -> Path:
    if not isinstance(locator, str) or not locator or Path(locator).is_absolute():
        raise BindingError("result artifact locator must be a relative path")
    base = result_path.parent.resolve()
    resolved = (base / locator).resolve()
    if resolved.parent != base:
        raise BindingError("result artifact locator escapes the result directory")
    return resolved


def verify_binding() -> dict[str, str]:
    packet, packet_raw = load(PACKET)
    index, _ = load(INDEX)
    if packet.get("authority_effect") != "none" or index.get("authority_effect") != "none":
        raise BindingError("packet or index claims authority")
    if packet.get("packet_root") != rooted(packet, "packet_root"):
        raise BindingError("packet root drift")
    if index.get("index_root") != rooted(index, "index_root"):
        raise BindingError("index root drift")
    targets = index.get("targets")
    if not isinstance(targets, list) or len(targets) != 1 or targets[0].get("id") != "erdos:887":
        raise BindingError("exact Target inventory drift")
    target = targets[0]
    packet_descriptor = target.get("packet")
    if packet_descriptor != {
        "schema": packet["schema"],
        "path": str(PACKET.relative_to(REPO_ROOT)),
        "size": len(packet_raw),
        "raw_sha256": raw_root(packet_raw),
        "packet_root": packet["packet_root"],
    }:
        raise BindingError("packet descriptor drift")
    components = packet.get("execution_components")
    if not isinstance(components, dict) or components.get("authority_effect") != "none":
        raise BindingError("execution component boundary drift")
    roots: dict[str, str] = {}
    for name, root_field in ROOT_FIELDS.items():
        descriptor = components.get(name)
        if not isinstance(descriptor, dict):
            raise BindingError(f"missing {name} descriptor")
        path = REPO_ROOT / descriptor.get("path", "")
        value, raw = load(path)
        if value.get("authority_effect") != "none":
            raise BindingError(f"{name} claims authority")
        custody = value.get("custody")
        if not isinstance(custody, dict) or custody.get("access") != "public" or custody.get("participant_private_data_allowed") is not False:
            raise BindingError(f"{name} public custody drift")
        root = value.get(root_field)
        if root != rooted(value, root_field):
            raise BindingError(f"{name} root drift")
        if descriptor != {
            "schema": value["schema"],
            "path": str(path.relative_to(REPO_ROOT)),
            "root": root,
            "raw_sha256": raw_root(raw),
            "size": len(raw),
        }:
            raise BindingError(f"{name} descriptor drift")
        if name == "verifier_capsule":
            implementation = value.get("implementation")
            if not isinstance(implementation, dict) or implementation.get("path") != str(Path(__file__).resolve().relative_to(REPO_ROOT)):
                raise BindingError("verifier capsule implementation path drift")
            if implementation.get("raw_sha256") != raw_root(Path(__file__).resolve().read_bytes()):
                raise BindingError("verifier capsule implementation root drift")
        roots[name] = root
    expected = {
        "schema": "vela.execution-binding.v1",
        "packet_root": packet["packet_root"],
        "profile_root": roots["producer_profile"],
        "verifier_capsule_root": roots["verifier_capsule"],
        "result_contract_root": roots["result_contract"],
    }
    if target.get("execution_binding") != expected:
        raise BindingError("execution binding drift")
    return expected


def verify_result(path: Path, binding: dict[str, str]) -> str:
    result, raw = load(path)
    contract, _ = load(HERE / "result-contract.v1.json")
    result_contract = contract["result"]
    if len(raw) > result_contract["maximum_bytes"] or result.get("schema") != result_contract["schema"]:
        raise BindingError("result contract framing or schema drift")
    missing = sorted(set(result_contract["required_fields"]) - set(result))
    if missing:
        raise BindingError(f"result is missing required fields: {missing}")
    if result.get("authority_effect") != "none" or result.get("target_id") != "erdos:887":
        raise BindingError("result Target or authority drift")
    if result.get("packet_root") != binding["packet_root"]:
        raise BindingError("result packet binding drift")
    positive = contract["positive_result"]
    if result.get("result_status") != positive["result_status"]:
        raise BindingError("result status drift")
    review = result.get("semantic_review")
    review_contract = positive["semantic_review"]
    if not isinstance(review, dict) or any(review.get(key) != value for key, value in review_contract.items()):
        raise BindingError("human semantic-review boundary drift")
    artifacts = result.get("artifacts")
    if not isinstance(artifacts, dict) or any(name not in artifacts for name in positive["required_artifacts"]):
        raise BindingError("required result artifact inventory drift")
    patch_descriptor = artifacts["source_patch"]
    if not isinstance(patch_descriptor, dict):
        raise BindingError("source patch descriptor drift")
    patch_path = result_artifact_path(path, patch_descriptor.get("path"))
    patch_raw = patch_path.read_bytes()
    patch_root = raw_root(patch_raw)
    if patch_descriptor != {"path": patch_descriptor.get("path"), "raw_sha256": patch_root, "size": len(patch_raw)}:
        raise BindingError("source patch descriptor drift")
    if result.get("source_patch_root") != patch_root:
        raise BindingError("source patch root drift")
    check_descriptor = artifacts["lean_check"]
    if not isinstance(check_descriptor, dict):
        raise BindingError("Lean check descriptor drift")
    check_path = result_artifact_path(path, check_descriptor.get("path"))
    check, _ = load(check_path)
    if check.get("authority_effect") != "none" or check.get("check_result_root") != rooted(check, "check_result_root"):
        raise BindingError("Lean check authority or root drift")
    if check_descriptor != {"path": check_descriptor.get("path"), "root": check["check_result_root"]}:
        raise BindingError("Lean check descriptor drift")
    if result.get("check_result_root") != check["check_result_root"] or check.get("source", {}).get("patch_raw_sha256") != patch_root:
        raise BindingError("result, Lean check, and patch binding drift")
    source_roots = result.get("source_roots")
    if not isinstance(source_roots, dict) or any(not full_sha256_root(value) for key, value in source_roots.items() if key.endswith("_root")):
        raise BindingError("result source root shape drift")
    if result.get("result_root") != rooted(result, "result_root"):
        raise BindingError("result root drift")
    return result["result_root"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", type=Path)
    args = parser.parse_args()
    binding = verify_binding()
    output: dict[str, Any] = {"execution_binding": binding, "status": "binding_valid"}
    if args.result is not None:
        output["result_root"] = verify_result(args.result, binding)
        output["status"] = "binding_and_result_valid"
    print(json.dumps(output, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
