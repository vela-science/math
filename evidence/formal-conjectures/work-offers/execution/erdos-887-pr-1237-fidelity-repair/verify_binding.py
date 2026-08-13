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
CAPTURE_EXECUTION = (
    WORK_OFFERS
    / "results/erdos-887-pilot-02-current-binding/capture_execution.py"
)

ROOT_FIELDS = {
    "producer_profile": "profile_root",
    "verifier_capsule": "verifier_capsule_root",
    "result_contract": "result_contract_root",
}
SANDBOX_POLICY = "(version 1)(allow default)(deny network*)"


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


def full_git_oid(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 40 and all(character in "0123456789abcdef" for character in value)


def result_artifact_path(result_path: Path, locator: Any) -> Path:
    if not isinstance(locator, str) or not locator or Path(locator).is_absolute():
        raise BindingError("result artifact locator must be a relative path")
    base = result_path.parent.resolve()
    resolved = (base / locator).resolve()
    if resolved == base or base not in resolved.parents:
        raise BindingError("result artifact locator escapes the result directory")
    return resolved


def repository_custody_path(locator: Any) -> Path:
    if not isinstance(locator, str) or not locator or Path(locator).is_absolute():
        raise BindingError("repository artifact locator must be a relative path")
    base = REPO_ROOT.resolve()
    resolved = (base / locator).resolve()
    if resolved == base or base not in resolved.parents:
        raise BindingError("repository artifact locator escapes exact repository custody")
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
    if result.get("packet_root") != binding["packet_root"] or result.get("execution_binding") != binding:
        raise BindingError("result execution binding drift")
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
    if set(artifacts) != set(positive["required_artifacts"]):
        raise BindingError("unexpected result artifact inventory")
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
    if check.get("execution_binding") != binding:
        raise BindingError("Lean check execution binding drift")
    if check_descriptor != {"path": check_descriptor.get("path"), "root": check["check_result_root"]}:
        raise BindingError("Lean check descriptor drift")
    if result.get("check_result_root") != check["check_result_root"] or check.get("source", {}).get("patch_raw_sha256") != patch_root:
        raise BindingError("result, Lean check, and patch binding drift")
    inventory_descriptor = artifacts["dependency_inventory"]
    transcript_descriptor = artifacts["execution_transcript"]
    if not isinstance(inventory_descriptor, dict) or not isinstance(transcript_descriptor, dict):
        raise BindingError("execution evidence descriptor drift")
    inventory_path = result_artifact_path(path, inventory_descriptor.get("path"))
    transcript_path = result_artifact_path(path, transcript_descriptor.get("path"))
    inventory, _ = load(inventory_path)
    transcript, _ = load(transcript_path)
    inventory_capture = inventory.get("capture")
    transcript_runner = transcript.get("runner")
    if not isinstance(inventory_capture, dict) or not isinstance(transcript_runner, dict):
        raise BindingError("execution capture implementation descriptor drift")
    inventory_capture_path = repository_custody_path(inventory_capture.get("script_path"))
    transcript_capture_path = repository_custody_path(transcript_runner.get("script_path"))
    expected_capture_path = CAPTURE_EXECUTION.resolve()
    if inventory_capture_path != expected_capture_path or transcript_capture_path != expected_capture_path:
        raise BindingError("execution capture implementation path drift")
    actual_capture_root = raw_root(expected_capture_path.read_bytes())
    if (
        inventory_capture.get("script_raw_sha256") != actual_capture_root
        or transcript_runner.get("script_raw_sha256") != actual_capture_root
        or inventory_capture.get("script_raw_sha256") != transcript_runner.get("script_raw_sha256")
    ):
        raise BindingError("execution capture implementation root drift")
    if inventory.get("authority_effect") != "none" or inventory.get("inventory_root") != rooted(inventory, "inventory_root"):
        raise BindingError("dependency inventory authority or root drift")
    custody = inventory.get("custody")
    if (
        not isinstance(custody, dict)
        or custody.get("access") != "public"
        or custody.get("participant_private_data_allowed") is not False
        or custody.get("compiled_cache_retained") is not True
    ):
        raise BindingError("dependency inventory public custody drift")
    packages = inventory.get("packages")
    if (
        not isinstance(packages, list)
        or not packages
        or inventory.get("all_heads_match_manifest") is not True
        or inventory.get("all_source_worktrees_clean") is not True
        or inventory.get("prerequisite_build_started_from_source_only") is not False
        or inventory.get("compiled_build_directories_before_prerequisite") != []
        or inventory.get("lake_registry_build_barrels_before_prerequisite") != []
        or inventory.get("lake_registry_network_during_replay") != "denied_by_sandbox-exec_and_global_no_cache"
        or any(
            item.get("actual_head") != item.get("manifest_revision")
            or item.get("head_matches_manifest") is not True
            or item.get("source_worktree_clean") is not True
            or not full_git_oid(item.get("actual_tree"))
            for item in packages
        )
    ):
        raise BindingError("dependency package HEAD evidence drift")
    if inventory_descriptor != {"path": inventory_descriptor.get("path"), "root": inventory["inventory_root"]}:
        raise BindingError("dependency inventory descriptor drift")
    if transcript.get("authority_effect") != "none" or transcript.get("transcript_root") != rooted(transcript, "transcript_root"):
        raise BindingError("execution transcript authority or root drift")
    if transcript.get("execution_binding") != binding:
        raise BindingError("execution transcript binding drift")
    if transcript.get("dependency_inventory") != {"path": inventory_descriptor.get("path"), "root": inventory["inventory_root"]}:
        raise BindingError("execution transcript dependency binding drift")
    if transcript_descriptor != {"path": transcript_descriptor.get("path"), "root": transcript["transcript_root"]}:
        raise BindingError("execution transcript descriptor drift")
    for name in (
        "lean_stdout", "lean_stderr", "lake_manifest",
        "prerequisite_build_stdout", "prerequisite_build_stderr",
        "leansearchclient_cache_barrel", "proofwidgets_release_archive",
        "leansearch_unpack_stdout", "leansearch_unpack_stderr",
        "proofwidgets_unpack_stdout", "proofwidgets_unpack_stderr",
    ):
        descriptor = artifacts[name]
        if not isinstance(descriptor, dict):
            raise BindingError(f"{name} descriptor drift")
        output_path = result_artifact_path(path, descriptor.get("path"))
        output_raw = output_path.read_bytes()
        if descriptor != {"path": descriptor.get("path"), "raw_sha256": raw_root(output_raw), "size": len(output_raw)}:
            raise BindingError(f"{name} descriptor drift")
    manifest_descriptor = inventory.get("source", {}).get("lake_manifest")
    if manifest_descriptor != artifacts["lake_manifest"]:
        raise BindingError("retained lake-manifest binding drift")
    cache_descriptor = artifacts["public_cache_snapshot"]
    if not isinstance(cache_descriptor, dict):
        raise BindingError("public cache snapshot descriptor drift")
    cache_path = result_artifact_path(path, cache_descriptor.get("path"))
    cache_snapshot, cache_raw = load(cache_path)
    if (
        cache_snapshot.get("authority_effect") != "none"
        or cache_snapshot.get("cache_snapshot_root") != rooted(cache_snapshot, "cache_snapshot_root")
        or cache_descriptor != {"path": cache_descriptor.get("path"), "root": cache_snapshot.get("cache_snapshot_root")}
        or b"/private/" in cache_raw
        or b"/Users/" in cache_raw
    ):
        raise BindingError("public cache snapshot authority, root, or privacy drift")
    cache_artifacts = cache_snapshot.get("artifacts")
    if not isinstance(cache_artifacts, list) or len(cache_artifacts) != 2:
        raise BindingError("public cache snapshot inventory drift")
    expected_cache_artifacts = [
        ("leansearchclient-reservoir-barrel", artifacts["leansearchclient_cache_barrel"]),
        ("proofwidgets-github-release-archive", artifacts["proofwidgets_release_archive"]),
    ]
    for cache_artifact, (artifact_id, snapshot_descriptor) in zip(cache_artifacts, expected_cache_artifacts):
        receipt = cache_artifact.get("normalized_acquisition_command_metadata")
        if (
            cache_artifact.get("id") != artifact_id
            or cache_artifact.get("snapshot") != snapshot_descriptor
            or not isinstance(receipt, dict)
            or cache_artifact.get("public_url") not in receipt.get("command", [])
        ):
            raise BindingError("public cache artifact or normalized acquisition-command metadata drift")
    cache_execution_descriptor = {"path": cache_descriptor.get("path"), "root": cache_snapshot["cache_snapshot_root"]}
    if inventory.get("compiled_cache_replay") != cache_execution_descriptor or transcript.get("compiled_cache_replay") != cache_execution_descriptor:
        raise BindingError("public cache execution binding drift")
    stages = transcript.get("stages")
    if not isinstance(stages, list) or len(stages) != 4:
        raise BindingError("execution transcript stage inventory drift")
    expected_stages = [
        (["python3", "-B", "$RESULT_DIR/capture_execution.py", "--materialize-validated-tar", "$RESULT_DIR/public-cache-snapshots/LeanSearchClient-build.barrel", "$PACKAGE/.lake/build"], artifacts["leansearch_unpack_stdout"], artifacts["leansearch_unpack_stderr"]),
        (["python3", "-B", "$RESULT_DIR/capture_execution.py", "--materialize-validated-tar", "$RESULT_DIR/public-cache-snapshots/ProofWidgets4.tar.gz", "$PACKAGE/.lake/build"], artifacts["proofwidgets_unpack_stdout"], artifacts["proofwidgets_unpack_stderr"]),
        (["sandbox-exec", "-p", SANDBOX_POLICY, "lake", "--no-cache", "build", "+FormalConjectures.Util.ProblemImports:olean"], artifacts["prerequisite_build_stdout"], artifacts["prerequisite_build_stderr"]),
        (["sandbox-exec", "-p", SANDBOX_POLICY, "lake", "env", "lean", "FormalConjectures/ErdosProblems/887.lean"], artifacts["lean_stdout"], artifacts["lean_stderr"]),
    ]
    for stage, (command, stdout, stderr) in zip(stages, expected_stages):
        if stage.get("command") != command or stage.get("exit_code") != 0 or stage.get("output") != {"stdout": stdout, "stderr": stderr}:
            raise BindingError("execution transcript stage binding drift")
    if check.get("dependency_inventory") != inventory_descriptor or check.get("execution_transcript") != transcript_descriptor:
        raise BindingError("Lean check execution evidence binding drift")
    check_output = check.get("output")
    if not isinstance(check_output, dict) or check_output.get("stdout") != artifacts["lean_stdout"] or check_output.get("stderr") != artifacts["lean_stderr"]:
        raise BindingError("Lean check output binding drift")
    if check.get("command") != stages[3]["command"] or check.get("exit_code") != stages[3]["exit_code"]:
        raise BindingError("Lean check command or exit binding drift")
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
