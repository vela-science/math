#!/usr/bin/env python3
"""Build the current-binding Erdős 887 repair result from observed exact facts."""

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
PACKET = HERE / "target-packet.v1.json"
INDEX = HERE / "work-offer-index.v1.json"
PATCH = HERE / "repair.patch"
CHECK = HERE / "lean-check.v1.json"
RESULT = HERE / "result.v1.json"
LEAN_STDOUT = HERE / "lean-stdout.txt"
LEAN_STDERR = HERE / "lean-stderr.txt"
INVENTORY = HERE / "dependency-inventory.v1.json"
TRANSCRIPT = HERE / "execution-transcript.v1.json"
RETAINED_MANIFEST = HERE / "retained-lake-manifest.json"
BUILD_STDOUT = HERE / "prerequisite-build-stdout.txt"
BUILD_STDERR = HERE / "prerequisite-build-stderr.txt"
CACHE_SNAPSHOT = HERE / "public-cache-snapshot.v1.json"
LEANSEARCH_BARREL = HERE / "public-cache-snapshots/LeanSearchClient-build.barrel"
PROOFWIDGETS_ARCHIVE = HERE / "public-cache-snapshots/ProofWidgets4.tar.gz"
LEANSEARCH_UNPACK_STDOUT = HERE / "leansearch-unpack-stdout.txt"
LEANSEARCH_UNPACK_STDERR = HERE / "leansearch-unpack-stderr.txt"
PROOFWIDGETS_UNPACK_STDOUT = HERE / "proofwidgets-unpack-stdout.txt"
PROOFWIDGETS_UNPACK_STDERR = HERE / "proofwidgets-unpack-stderr.txt"
SANDBOX_POLICY = "(version 1)(allow default)(deny network*)"

SOURCE_COMMIT = "288608562e684a2f3c97ba0ce960a2649a71370b"
SOURCE_TREE = "db331ce2429aa6a53e30a66325493e0ad6b1d0b5"
SOURCE_PATH = "FormalConjectures/ErdosProblems/887.lean"
BASE_BLOB = "6feb58b9272ce638aba6da5ca7ee8ebf7785e0b8"
RESULT_BLOB = "18427d1cf11b1e6aa51bd1c78061240121beaeb2"
BASE_CONTENT_ROOT = "sha256:3e4c9376ebfa464985a2da4ac3b8401b1b54d64be1075368032eced0700706c5"
RESULT_CONTENT_ROOT = "sha256:249ba4bcc206477d2695e154acda204bed356b99d4f670730ca9adeed08f8f01"
class ResultBuildError(ValueError):
    pass


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ResultBuildError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def load(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if not raw.endswith(b"\n") or raw.endswith(b"\n\n"):
        raise ResultBuildError(f"{path.relative_to(REPO_ROOT)} must have exactly one trailing LF")
    value = json.loads(raw, object_pairs_hook=unique_object)
    if not isinstance(value, dict) or raw != canonical(value) + b"\n":
        raise ResultBuildError(f"{path.relative_to(REPO_ROOT)} must contain canonical JSON")
    return value


def root(value: dict[str, Any], field: str) -> str:
    preimage = copy.deepcopy(value)
    preimage.pop(field, None)
    return "sha256:" + hashlib.sha256(canonical(preimage)).hexdigest()


def raw_root(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def retained_execution_binding() -> tuple[dict[str, Any], dict[str, Any]]:
    packet = load(PACKET)
    index = load(INDEX)
    targets = index.get("targets")
    if not isinstance(targets, list) or len(targets) != 1 or targets[0].get("id") != "erdos:887":
        raise ResultBuildError("retained work-offer inventory drift")
    binding = targets[0].get("execution_binding")
    if not isinstance(binding, dict) or binding.get("schema") != "vela.execution-binding.v1":
        raise ResultBuildError("retained execution binding is missing")
    if binding.get("packet_root") != packet.get("packet_root") or packet.get("packet_root") != root(packet, "packet_root"):
        raise ResultBuildError("retained packet binding drift")
    components = packet.get("execution_components")
    expected = {
        "schema": "vela.execution-binding.v1",
        "packet_root": packet["packet_root"],
        "profile_root": components["producer_profile"]["root"],
        "verifier_capsule_root": components["verifier_capsule"]["root"],
        "result_contract_root": components["result_contract"]["root"],
    }
    if binding != expected:
        raise ResultBuildError("execution binding/component drift")
    return packet, binding


def build_check(binding: dict[str, Any]) -> dict[str, Any]:
    patch_root = raw_root(PATCH.read_bytes())
    lean_stdout = LEAN_STDOUT.read_bytes()
    lean_stderr = LEAN_STDERR.read_bytes()
    manifest_raw = RETAINED_MANIFEST.read_bytes()
    inventory = load(INVENTORY)
    transcript = load(TRANSCRIPT)
    if inventory.get("authority_effect") != "none" or inventory.get("inventory_root") != root(inventory, "inventory_root"):
        raise ResultBuildError("dependency inventory authority or root drift")
    if (
        not inventory.get("all_heads_match_manifest")
        or not inventory.get("all_source_worktrees_clean")
        or inventory.get("prerequisite_build_started_from_source_only") is not False
        or inventory.get("compiled_build_directories_before_prerequisite") != []
        or inventory.get("lake_registry_build_barrels_before_prerequisite") != []
        or inventory.get("lake_registry_network_during_replay") != "denied_by_sandbox-exec_and_global_no_cache"
    ):
        raise ResultBuildError("dependency inventory does not establish exact public source custody")
    if inventory.get("source", {}).get("lake_manifest") != {
        "path": RETAINED_MANIFEST.name,
        "raw_sha256": raw_root(manifest_raw),
        "size": len(manifest_raw),
    }:
        raise ResultBuildError("retained lake-manifest binding drift")
    packages = inventory.get("packages")
    if not isinstance(packages, list) or not packages or any(
        item.get("actual_head") != item.get("manifest_revision")
        or item.get("head_matches_manifest") is not True
        or item.get("source_worktree_clean") is not True
        for item in packages
    ):
        raise ResultBuildError("dependency source HEAD evidence drift")
    if transcript.get("authority_effect") != "none" or transcript.get("transcript_root") != root(transcript, "transcript_root"):
        raise ResultBuildError("execution transcript authority or root drift")
    if transcript.get("execution_binding") != binding:
        raise ResultBuildError("execution transcript binding drift")
    if transcript.get("dependency_inventory") != {"path": INVENTORY.name, "root": inventory["inventory_root"]}:
        raise ResultBuildError("execution transcript dependency binding drift")
    cache_snapshot = load(CACHE_SNAPSHOT)
    if cache_snapshot.get("authority_effect") != "none" or cache_snapshot.get("cache_snapshot_root") != root(cache_snapshot, "cache_snapshot_root"):
        raise ResultBuildError("public cache snapshot authority or root drift")
    cache_descriptor = {"path": CACHE_SNAPSHOT.name, "root": cache_snapshot["cache_snapshot_root"]}
    if inventory.get("compiled_cache_replay") != cache_descriptor or transcript.get("compiled_cache_replay") != cache_descriptor:
        raise ResultBuildError("public cache snapshot execution binding drift")
    build_stdout = BUILD_STDOUT.read_bytes()
    build_stderr = BUILD_STDERR.read_bytes()
    cache_snapshot = load(CACHE_SNAPSHOT)
    leansearch_barrel = LEANSEARCH_BARREL.read_bytes()
    proofwidgets_archive = PROOFWIDGETS_ARCHIVE.read_bytes()
    leansearch_unpack_stdout = LEANSEARCH_UNPACK_STDOUT.read_bytes()
    leansearch_unpack_stderr = LEANSEARCH_UNPACK_STDERR.read_bytes()
    proofwidgets_unpack_stdout = PROOFWIDGETS_UNPACK_STDOUT.read_bytes()
    proofwidgets_unpack_stderr = PROOFWIDGETS_UNPACK_STDERR.read_bytes()
    leansearch_unpack_stdout = LEANSEARCH_UNPACK_STDOUT.read_bytes()
    leansearch_unpack_stderr = LEANSEARCH_UNPACK_STDERR.read_bytes()
    proofwidgets_unpack_stdout = PROOFWIDGETS_UNPACK_STDOUT.read_bytes()
    proofwidgets_unpack_stderr = PROOFWIDGETS_UNPACK_STDERR.read_bytes()
    expected_stages = [
        (["python3", "-B", "$RESULT_DIR/capture_execution.py", "--materialize-validated-tar", "$RESULT_DIR/public-cache-snapshots/LeanSearchClient-build.barrel", "$PACKAGE/.lake/build"], LEANSEARCH_UNPACK_STDOUT.name, leansearch_unpack_stdout, LEANSEARCH_UNPACK_STDERR.name, leansearch_unpack_stderr),
        (["python3", "-B", "$RESULT_DIR/capture_execution.py", "--materialize-validated-tar", "$RESULT_DIR/public-cache-snapshots/ProofWidgets4.tar.gz", "$PACKAGE/.lake/build"], PROOFWIDGETS_UNPACK_STDOUT.name, proofwidgets_unpack_stdout, PROOFWIDGETS_UNPACK_STDERR.name, proofwidgets_unpack_stderr),
        (["sandbox-exec", "-p", SANDBOX_POLICY, "lake", "--no-cache", "build", "+FormalConjectures.Util.ProblemImports:olean"], BUILD_STDOUT.name, build_stdout, BUILD_STDERR.name, build_stderr),
        (["sandbox-exec", "-p", SANDBOX_POLICY, "lake", "env", "lean", SOURCE_PATH], LEAN_STDOUT.name, lean_stdout, LEAN_STDERR.name, lean_stderr),
    ]
    stages = transcript.get("stages")
    if not isinstance(stages, list) or len(stages) != 4:
        raise ResultBuildError("execution transcript stage inventory drift")
    for stage, (command, stdout_name, stdout_raw, stderr_name, stderr_raw) in zip(stages, expected_stages):
        if stage.get("command") != command or stage.get("exit_code") != 0 or stage.get("output") != {
            "stdout": {"path": stdout_name, "raw_sha256": raw_root(stdout_raw), "size": len(stdout_raw)},
            "stderr": {"path": stderr_name, "raw_sha256": raw_root(stderr_raw), "size": len(stderr_raw)},
        }:
            raise ResultBuildError("execution transcript stage binding drift")
    source = transcript.get("source")
    if not isinstance(source, dict) or source.get("patch_raw_sha256") != patch_root or source.get("result_content_root") != RESULT_CONTENT_ROOT:
        raise ResultBuildError("execution transcript source binding drift")
    check: dict[str, Any] = {
        "schema": "vela.math.lean-source-check.v1",
        "authority_effect": "none",
        "execution_binding": binding,
        "command": stages[3]["command"],
        "started_at": stages[3]["started_at"],
        "completed_at": stages[3]["completed_at"],
        "exit_code": stages[3]["exit_code"],
        "environment": transcript["environment"],
        "dependency_inventory": {"path": INVENTORY.name, "root": inventory["inventory_root"]},
        "execution_transcript": {"path": TRANSCRIPT.name, "root": transcript["transcript_root"]},
        "source": {
            "base_commit": SOURCE_COMMIT,
            "base_tree": SOURCE_TREE,
            "path": SOURCE_PATH,
            "base_blob_oid": BASE_BLOB,
            "base_content_root": BASE_CONTENT_ROOT,
            "patch_raw_sha256": patch_root,
            "result_blob_oid": RESULT_BLOB,
            "result_content_root": RESULT_CONTENT_ROOT,
        },
        "output": {**stages[3]["output"], "warning_count": 4},
        "warnings": [
            f"{SOURCE_PATH}:35:8: declaration uses sorry",
            f"{SOURCE_PATH}:44:8: declaration uses sorry",
            f"{SOURCE_PATH}:53:8: declaration uses sorry",
            f"{SOURCE_PATH}:62:8: declaration uses sorry",
        ],
        "nonclaims": [
            "The successful check establishes only elaboration of the patched source under the exact retained toolchain and dependency revisions.",
            "The retained public package source inventory independently reads each checkout HEAD and tree; two exact public compiled artifacts and their normalized acquisition-command metadata are selectively retained, rooted, and materialized locally before the prerequisite.",
            "Validated standard-library archive materialization performs no network operation; the global --no-cache prerequisite and target check ran under an operating-system network-denial policy.",
            "This is an exact public compiled-cache replay, not a from-source dependency build.",
            "The same operator does not constitute an independent reproduction.",
            "The four sorry placeholders mean the check does not prove Erdős problem 887.",
            "This check is not a Vela Verification, human Decision, upstream acceptance, or change to Math Standing.",
        ],
        "check_result_root_definition": "sha256 of canonical JSON after removing only check_result_root",
    }
    check["check_result_root"] = root(check, "check_result_root")
    return check


def validate_result(result: dict[str, Any], binding: dict[str, Any]) -> None:
    if result.get("authority_effect") != "none" or result.get("execution_binding") != binding:
        raise ResultBuildError("result authority or execution binding drift")
    review = result.get("semantic_review")
    if not isinstance(review, dict) or review.get("status") != "pending" or review.get("reviewer") is not None or review.get("independent") is not False:
        raise ResultBuildError("result human-review boundary drift")
    if result.get("result_root") != root(result, "result_root"):
        raise ResultBuildError("result root drift")


def build() -> tuple[dict[str, Any], bytes, dict[str, Any], bytes]:
    packet, binding = retained_execution_binding()
    check = build_check(binding)
    check_raw = canonical(check) + b"\n"
    patch_raw = PATCH.read_bytes()
    inventory = load(INVENTORY)
    transcript = load(TRANSCRIPT)
    lean_stdout = LEAN_STDOUT.read_bytes()
    lean_stderr = LEAN_STDERR.read_bytes()
    manifest_raw = RETAINED_MANIFEST.read_bytes()
    build_stdout = BUILD_STDOUT.read_bytes()
    build_stderr = BUILD_STDERR.read_bytes()
    cache_snapshot = load(CACHE_SNAPSHOT)
    leansearch_barrel = LEANSEARCH_BARREL.read_bytes()
    proofwidgets_archive = PROOFWIDGETS_ARCHIVE.read_bytes()
    leansearch_unpack_stdout = LEANSEARCH_UNPACK_STDOUT.read_bytes()
    leansearch_unpack_stderr = LEANSEARCH_UNPACK_STDERR.read_bytes()
    proofwidgets_unpack_stdout = PROOFWIDGETS_UNPACK_STDOUT.read_bytes()
    proofwidgets_unpack_stderr = PROOFWIDGETS_UNPACK_STDERR.read_bytes()
    artifacts = {
        "source_patch": {"path": PATCH.name, "raw_sha256": raw_root(patch_raw), "size": len(patch_raw)},
        "lean_check": {"path": CHECK.name, "root": check["check_result_root"]},
        "dependency_inventory": {"path": INVENTORY.name, "root": inventory["inventory_root"]},
        "execution_transcript": {"path": TRANSCRIPT.name, "root": transcript["transcript_root"]},
        "lean_stdout": {"path": LEAN_STDOUT.name, "raw_sha256": raw_root(lean_stdout), "size": len(lean_stdout)},
        "lean_stderr": {"path": LEAN_STDERR.name, "raw_sha256": raw_root(lean_stderr), "size": len(lean_stderr)},
        "lake_manifest": {"path": RETAINED_MANIFEST.name, "raw_sha256": raw_root(manifest_raw), "size": len(manifest_raw)},
        "prerequisite_build_stdout": {"path": BUILD_STDOUT.name, "raw_sha256": raw_root(build_stdout), "size": len(build_stdout)},
        "prerequisite_build_stderr": {"path": BUILD_STDERR.name, "raw_sha256": raw_root(build_stderr), "size": len(build_stderr)},
        "public_cache_snapshot": {"path": CACHE_SNAPSHOT.name, "root": cache_snapshot["cache_snapshot_root"]},
        "leansearchclient_cache_barrel": {"path": str(LEANSEARCH_BARREL.relative_to(HERE)), "raw_sha256": raw_root(leansearch_barrel), "size": len(leansearch_barrel)},
        "proofwidgets_release_archive": {"path": str(PROOFWIDGETS_ARCHIVE.relative_to(HERE)), "raw_sha256": raw_root(proofwidgets_archive), "size": len(proofwidgets_archive)},
        "leansearch_unpack_stdout": {"path": LEANSEARCH_UNPACK_STDOUT.name, "raw_sha256": raw_root(leansearch_unpack_stdout), "size": len(leansearch_unpack_stdout)},
        "leansearch_unpack_stderr": {"path": LEANSEARCH_UNPACK_STDERR.name, "raw_sha256": raw_root(leansearch_unpack_stderr), "size": len(leansearch_unpack_stderr)},
        "proofwidgets_unpack_stdout": {"path": PROOFWIDGETS_UNPACK_STDOUT.name, "raw_sha256": raw_root(proofwidgets_unpack_stdout), "size": len(proofwidgets_unpack_stdout)},
        "proofwidgets_unpack_stderr": {"path": PROOFWIDGETS_UNPACK_STDERR.name, "raw_sha256": raw_root(proofwidgets_unpack_stderr), "size": len(proofwidgets_unpack_stderr)},
    }
    result: dict[str, Any] = {
        "schema": "vela.math.fidelity-repair-result.v1",
        "authority_effect": "none",
        "target_id": "erdos:887",
        "packet_root": packet["packet_root"],
        "execution_binding": binding,
        "producer": {
            "actor_class": "agent",
            "operator_id": "pilot-operator-02",
            "provider": "OpenAI Codex",
            "runtime": "Codex delegated task /root/memo_federated_frontier at Math 0c709e191d869b9d5ee0f1f6eae09ae549daf167",
            "source_root": RESULT_CONTENT_ROOT,
            "packet_root": packet["packet_root"],
            "output_roots": [
                raw_root(patch_raw),
                inventory["inventory_root"],
                cache_snapshot["cache_snapshot_root"],
                transcript["transcript_root"],
                check["check_result_root"],
            ],
            "timestamps": {"started_at": transcript["stages"][0]["started_at"], "completed_at": transcript["stages"][3]["completed_at"]},
            "access_limits": [
                "public Formal Conjectures and Math source plus the two exact retained public compiled artifacts",
                "no Repository authority credentials",
                "no signing, Verification, or Decision authority",
            ],
            "independence_disclosure": "same operator; public package source HEADs matched the exact manifest, two exact public compiled artifacts were selectively retained and replayed with network denied, and no from-source, independent-review, or independent-reproduction claim is made",
        },
        "result_status": "candidate_ready_for_human_review",
        "artifacts": artifacts,
        "source_patch_root": raw_root(patch_raw),
        "check_result_root": check["check_result_root"],
        "semantic_review": {
            "required": True,
            "status": "pending",
            "reviewer": None,
            "independent": False,
            "witness": "The repaired theorem makes answer(sorry) the truth value of an existential absolute-K statement outside the C and n binders; this agent-prepared source reading remains pending attributed human confirmation.",
        },
        "source_roots": {
            "audit_core_root": packet["source"]["audit_core_root"],
            "audit_observation_root": packet["source"]["audit_observation_root"],
            "base_commit": SOURCE_COMMIT,
            "base_content_root": BASE_CONTENT_ROOT,
            "result_content_root": RESULT_CONTENT_ROOT,
        },
        "nonclaims": [
            "This is an agent-prepared candidate, not an independent human source-fidelity verdict.",
            "Lean elaboration with sorry does not prove Erdős problem 887.",
            "The same operator does not establish independent reproduction.",
            "This exact public compiled-cache replay does not establish a from-source dependency build.",
            "No upstream comment, review, issue, branch, pull request, or merge was created.",
            "This result is not a Vela Submission, Verification, Decision, Event, or change to Math Standing.",
        ],
        "result_root_definition": "sha256 of canonical JSON after removing only result_root",
    }
    result["result_root"] = root(result, "result_root")
    validate_result(result, binding)
    return check, check_raw, result, canonical(result) + b"\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--print-roots", action="store_true")
    args = parser.parse_args()
    check, check_raw, result, result_raw = build()
    if args.check:
        if CHECK.read_bytes() != check_raw or RESULT.read_bytes() != result_raw:
            raise SystemExit("current-binding result bytes drifted from the retained exact facts")
    else:
        CHECK.write_bytes(check_raw)
        RESULT.write_bytes(result_raw)
    if args.print_roots:
        print(json.dumps({"check_result_root": check["check_result_root"], "result_root": result["result_root"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
