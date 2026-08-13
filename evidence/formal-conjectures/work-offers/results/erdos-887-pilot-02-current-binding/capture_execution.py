#!/usr/bin/env python3
"""Execute and retain the current Erdős 887 repair against an exact checkout."""

from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile
from typing import Any


HERE = Path(__file__).resolve().parent
WORK_OFFERS = HERE.parents[1]
REPO_ROOT = WORK_OFFERS.parents[2]
PACKET = WORK_OFFERS / "packets/erdos-887-pr-1237-fidelity-repair.v1.json"
INDEX = WORK_OFFERS / "index.v1.json"
PATCH = HERE / "repair.patch"
INVENTORY = HERE / "dependency-inventory.v1.json"
TRANSCRIPT = HERE / "execution-transcript.v1.json"
LEAN_STDOUT = HERE / "lean-stdout.txt"
LEAN_STDERR = HERE / "lean-stderr.txt"
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
PREREQUISITE_COMMAND = [
    "sandbox-exec", "-p", SANDBOX_POLICY,
    "lake", "--no-cache", "build", "+FormalConjectures.Util.ProblemImports:olean",
]

SOURCE_REPOSITORY = "https://github.com/google-deepmind/formal-conjectures"
SOURCE_COMMIT = "288608562e684a2f3c97ba0ce960a2649a71370b"
SOURCE_TREE = "db331ce2429aa6a53e30a66325493e0ad6b1d0b5"
SOURCE_PATH = "FormalConjectures/ErdosProblems/887.lean"
BASE_BLOB = "6feb58b9272ce638aba6da5ca7ee8ebf7785e0b8"
RESULT_BLOB = "18427d1cf11b1e6aa51bd1c78061240121beaeb2"
BASE_CONTENT_ROOT = "sha256:3e4c9376ebfa464985a2da4ac3b8401b1b54d64be1075368032eced0700706c5"
RESULT_CONTENT_ROOT = "sha256:249ba4bcc206477d2695e154acda204bed356b99d4f670730ca9adeed08f8f01"
LAKE_MANIFEST_ROOT = "sha256:ab80199a7506e24fdd4f865dcd140aca00489151ab8ea70a6f9b6b5318fec09f"
LAKEFILE_ROOT = "sha256:deb194d30e4faab79a6cf1bd5aace287b2d05349f4d4012b6b58ffbdbdb35169"
TOOLCHAIN_ROOT = "sha256:8f6680f8389e8adee06cb2bd44372c6d60dce0e8301630b61a99a5642d1bd71b"
EXPECTED_LEAN = "Lean (version 4.22.0, arm64-apple-darwin23.6.0, commit ba2cbbf09d4978f416e0ebd1fceeebc2c4138c05, Release)"
TARGET_COMMAND = ["sandbox-exec", "-p", SANDBOX_POLICY, "lake", "env", "lean", SOURCE_PATH]


class CaptureError(ValueError):
    pass


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CaptureError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def load(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    value = json.loads(raw, object_pairs_hook=unique_object)
    if not isinstance(value, dict) or raw != canonical(value) + b"\n":
        raise CaptureError(f"{path.relative_to(REPO_ROOT)} must contain canonical JSON plus one LF")
    return value


def root(value: dict[str, Any], field: str) -> str:
    preimage = copy.deepcopy(value)
    preimage.pop(field, None)
    return "sha256:" + hashlib.sha256(canonical(preimage)).hexdigest()


def raw_root(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def run(checkout: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(args, cwd=checkout, check=check, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def git(checkout: Path, *args: str) -> str:
    completed = run(checkout, "git", *args)
    if completed.stderr:
        raise CaptureError(f"git {' '.join(args)} wrote unexpected stderr")
    return completed.stdout.decode("utf-8").strip()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def current_binding() -> dict[str, str]:
    packet = load(PACKET)
    index = load(INDEX)
    targets = index.get("targets")
    if not isinstance(targets, list) or len(targets) != 1:
        raise CaptureError("work-offer inventory drift")
    binding = targets[0].get("execution_binding")
    if not isinstance(binding, dict) or binding.get("packet_root") != packet.get("packet_root"):
        raise CaptureError("current execution binding drift")
    return binding


def descriptor(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    return {"path": str(path.relative_to(HERE)), "raw_sha256": raw_root(raw), "size": len(raw)}


def validate_cache_snapshot() -> dict[str, Any]:
    snapshot = load(CACHE_SNAPSHOT)
    if snapshot.get("authority_effect") != "none" or snapshot.get("cache_snapshot_root") != root(snapshot, "cache_snapshot_root"):
        raise CaptureError("public cache snapshot authority or root drift")
    artifacts = snapshot.get("artifacts")
    expected = [
        ("leansearchclient-reservoir-barrel", LEANSEARCH_BARREL),
        ("proofwidgets-github-release-archive", PROOFWIDGETS_ARCHIVE),
    ]
    if not isinstance(artifacts, list) or len(artifacts) != len(expected):
        raise CaptureError("public cache snapshot inventory drift")
    for artifact, (artifact_id, path) in zip(artifacts, expected):
        if artifact.get("id") != artifact_id or artifact.get("snapshot") != descriptor(path):
            raise CaptureError("public cache snapshot artifact drift")
        receipt = artifact.get("normalized_acquisition_command_metadata")
        if not isinstance(receipt, dict) or artifact.get("public_url") not in receipt.get("command", []):
            raise CaptureError("public cache normalized acquisition-command metadata drift")
    return snapshot


def materialize_archive(archive: Path, destination: Path) -> tuple[bytes, bytes, int]:
    try:
        with tarfile.open(archive, "r:gz") as opened:
            members = opened.getmembers()
            if not members:
                raise CaptureError("public cache archive is empty")
            for member in members:
                member_path = Path(member.name)
                if member_path.is_absolute() or ".." in member_path.parts or member.issym() or member.islnk():
                    raise CaptureError("public cache archive contains an unsafe member")
            destination.mkdir(parents=True, exist_ok=False)
            opened.extractall(destination, members=members)
        stdout = f"materialized {archive.name} into $PACKAGE/.lake/build with validated tarfile extraction\n".encode()
        return stdout, b"", 0
    except Exception as error:
        return b"", (str(error) + "\n").encode(), 1


def capture_inventory(checkout: Path, cache_snapshot: dict[str, Any]) -> dict[str, Any]:
    manifest_path = checkout / "lake-manifest.json"
    manifest_raw = manifest_path.read_bytes()
    if raw_root(manifest_raw) != LAKE_MANIFEST_ROOT:
        raise CaptureError("lake-manifest root drift")
    manifest = json.loads(manifest_raw, object_pairs_hook=unique_object)
    RETAINED_MANIFEST.write_bytes(manifest_raw)
    packages: list[dict[str, Any]] = []
    preexisting_build_directories: list[str] = []
    preexisting_registry_barrels: list[str] = []
    source_build = checkout / ".lake/build"
    if source_build.exists() or source_build.is_symlink():
        preexisting_build_directories.append("$SOURCE_CHECKOUT/.lake/build")
    for package in manifest.get("packages", []):
        name = package.get("name")
        url = package.get("url")
        revision = package.get("rev")
        if not all(isinstance(value, str) and value for value in (name, url, revision)):
            raise CaptureError("malformed lake-manifest package")
        package_path = checkout / ".lake/packages" / name
        package_build = package_path / ".lake/build"
        if package_build.exists() or package_build.is_symlink():
            preexisting_build_directories.append(f"$SOURCE_CHECKOUT/.lake/packages/{name}/.lake/build")
        for barrel in package_path.glob(".lake/build.barrel*"):
            preexisting_registry_barrels.append(
                f"$SOURCE_CHECKOUT/.lake/packages/{name}/.lake/{barrel.name}"
            )
        actual_head = git(package_path, "rev-parse", "HEAD")
        actual_tree = git(package_path, "rev-parse", "HEAD^{tree}")
        status = git(package_path, "status", "--porcelain")
        packages.append({
            "name": name,
            "public_source": url,
            "manifest_revision": revision,
            "actual_head": actual_head,
            "actual_tree": actual_tree,
            "head_matches_manifest": actual_head == revision,
            "source_worktree_clean": status == "",
        })
    if not packages or not all(item["head_matches_manifest"] and item["source_worktree_clean"] for item in packages):
        raise CaptureError("dependency source checkout does not match the exact manifest")
    if preexisting_build_directories:
        raise CaptureError("compiled build directories must be absent before the prerequisite build")
    if preexisting_registry_barrels:
        raise CaptureError("Lake registry build barrels must be absent before the prerequisite build")
    script_path = Path(__file__).resolve()
    inventory: dict[str, Any] = {
        "schema": "vela.math.lean-dependency-inventory.v1",
        "authority_effect": "none",
        "custody": {
            "access": "public",
            "package_sources": "public Git repositories at exact commits",
            "compiled_cache_retained": True,
            "participant_private_data_allowed": False,
        },
        "source": {
            "repository": SOURCE_REPOSITORY,
            "commit": SOURCE_COMMIT,
            "tree": SOURCE_TREE,
            "lake_manifest": {"path": RETAINED_MANIFEST.name, "raw_sha256": LAKE_MANIFEST_ROOT, "size": len(manifest_raw)},
        },
        "capture": {
            "script_path": str(script_path.relative_to(REPO_ROOT)),
            "script_raw_sha256": raw_root(script_path.read_bytes()),
            "command": ["python3", "-B", str(script_path.relative_to(REPO_ROOT)), "--source-checkout", "$SOURCE_CHECKOUT"],
            "packages_directory": "$SOURCE_CHECKOUT/.lake/packages",
        },
        "packages": packages,
        "all_heads_match_manifest": True,
        "all_source_worktrees_clean": True,
        "compiled_build_directories_before_prerequisite": preexisting_build_directories,
        "prerequisite_build_started_from_source_only": False,
        "lake_registry_build_barrels_before_prerequisite": preexisting_registry_barrels,
        "compiled_cache_replay": {
            "path": CACHE_SNAPSHOT.name,
            "root": cache_snapshot["cache_snapshot_root"],
        },
        "lake_registry_network_during_replay": "denied_by_sandbox-exec_and_global_no_cache",
        "inventory_root_definition": "sha256 of canonical JSON after removing only inventory_root",
    }
    inventory["inventory_root"] = root(inventory, "inventory_root")
    return inventory


def capture(checkout: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    checkout = checkout.resolve()
    if git(checkout, "rev-parse", "HEAD") != SOURCE_COMMIT or git(checkout, "rev-parse", "HEAD^{tree}") != SOURCE_TREE:
        raise CaptureError("source checkout commit or tree drift")
    if git(checkout, "status", "--porcelain"):
        raise CaptureError("source checkout must start clean")
    source_path = checkout / SOURCE_PATH
    if raw_root(source_path.read_bytes()) != BASE_CONTENT_ROOT or git(checkout, "hash-object", SOURCE_PATH) != BASE_BLOB:
        raise CaptureError("base source bytes drift")
    if raw_root((checkout / "lakefile.lean").read_bytes()) != LAKEFILE_ROOT:
        raise CaptureError("lakefile root drift")
    if raw_root((checkout / "lean-toolchain").read_bytes()) != TOOLCHAIN_ROOT:
        raise CaptureError("Lean toolchain root drift")
    cache_snapshot = validate_cache_snapshot()
    inventory = capture_inventory(checkout, cache_snapshot)
    binding = current_binding()
    patch_root = raw_root(PATCH.read_bytes())
    run(checkout, "git", "apply", "--check", "--unidiff-zero", str(PATCH))
    run(checkout, "git", "apply", "--unidiff-zero", str(PATCH))
    if raw_root(source_path.read_bytes()) != RESULT_CONTENT_ROOT or git(checkout, "hash-object", SOURCE_PATH) != RESULT_BLOB:
        raise CaptureError("patched source bytes drift")
    lean_version = run(checkout, "lake", "env", "lean", "--version").stdout.decode("utf-8").strip()
    if lean_version != EXPECTED_LEAN:
        raise CaptureError("Lean version drift")
    materializations: list[dict[str, Any]] = []
    materialization_specs = [
        (
            "materialize_leansearchclient_cache",
            checkout / ".lake/packages/LeanSearchClient",
            LEANSEARCH_BARREL,
            LEANSEARCH_UNPACK_STDOUT,
            LEANSEARCH_UNPACK_STDERR,
        ),
        (
            "materialize_proofwidgets_cache",
            checkout / ".lake/packages/proofwidgets",
            PROOFWIDGETS_ARCHIVE,
            PROOFWIDGETS_UNPACK_STDOUT,
            PROOFWIDGETS_UNPACK_STDERR,
        ),
    ]
    for name, package_path, snapshot_path, stdout_path, stderr_path in materialization_specs:
        recorded_command = [
            "python3", "-B", "$RESULT_DIR/capture_execution.py", "--materialize-validated-tar",
            "$RESULT_DIR/" + str(snapshot_path.relative_to(HERE)), "$PACKAGE/.lake/build",
        ]
        started_at = utc_now()
        unpack_stdout, unpack_stderr, unpack_exit = materialize_archive(snapshot_path, package_path / ".lake/build")
        completed_at = utc_now()
        stdout_path.write_bytes(unpack_stdout)
        stderr_path.write_bytes(unpack_stderr)
        if unpack_exit != 0:
            raise CaptureError(f"{name} failed; retained stdout and stderr for inspection")
        materializations.append({
            "name": name,
            "command": recorded_command,
            "started_at": started_at,
            "completed_at": completed_at,
            "exit_code": unpack_exit,
            "output": {
                "stdout": {"path": stdout_path.name, "raw_sha256": raw_root(unpack_stdout), "size": len(unpack_stdout)},
                "stderr": {"path": stderr_path.name, "raw_sha256": raw_root(unpack_stderr), "size": len(unpack_stderr)},
            },
        })
    build_started_at = utc_now()
    prerequisite = run(checkout, *PREREQUISITE_COMMAND, check=False)
    build_completed_at = utc_now()
    BUILD_STDOUT.write_bytes(prerequisite.stdout)
    BUILD_STDERR.write_bytes(prerequisite.stderr)
    if prerequisite.returncode != 0:
        raise CaptureError("prerequisite build failed; retained stdout and stderr for inspection")
    created_barrels = sorted(
        str(path.relative_to(checkout))
        for path in (checkout / ".lake/packages").glob("*/.lake/build.barrel*")
    )
    combined_prerequisite_output = prerequisite.stdout + prerequisite.stderr
    if created_barrels or b"reservoir.lean-lang.org" in combined_prerequisite_output:
        raise CaptureError("Lake registry build-cache acquisition occurred despite --no-cache")
    started_at = utc_now()
    completed = run(checkout, *TARGET_COMMAND, check=False)
    completed_at = utc_now()
    LEAN_STDOUT.write_bytes(completed.stdout)
    LEAN_STDERR.write_bytes(completed.stderr)
    if completed.returncode != 0:
        raise CaptureError("exact target check failed; retained stdout and stderr for inspection")
    script_path = Path(__file__).resolve()
    transcript: dict[str, Any] = {
        "schema": "vela.math.source-fidelity-execution-transcript.v1",
        "authority_effect": "none",
        "execution_binding": binding,
        "custody": {"access": "public", "participant_private_data_allowed": False},
        "runner": {
            "script_path": str(script_path.relative_to(REPO_ROOT)),
            "script_raw_sha256": raw_root(script_path.read_bytes()),
            "working_directory": "$SOURCE_CHECKOUT",
        },
        "source": {
            "repository": SOURCE_REPOSITORY,
            "commit": SOURCE_COMMIT,
            "tree": SOURCE_TREE,
            "path": SOURCE_PATH,
            "base_blob_oid": BASE_BLOB,
            "base_content_root": BASE_CONTENT_ROOT,
            "patch_raw_sha256": patch_root,
            "result_blob_oid": RESULT_BLOB,
            "result_content_root": RESULT_CONTENT_ROOT,
        },
        "dependency_inventory": {
            "path": "dependency-inventory.v1.json",
            "root": inventory["inventory_root"],
        },
        "compiled_cache_replay": {
            "path": CACHE_SNAPSHOT.name,
            "root": cache_snapshot["cache_snapshot_root"],
        },
        "stages": materializations + [
            {
                "name": "prerequisite_build",
                "command": PREREQUISITE_COMMAND,
                "started_at": build_started_at,
                "completed_at": build_completed_at,
                "exit_code": prerequisite.returncode,
                "output": {
                    "stdout": {"path": BUILD_STDOUT.name, "raw_sha256": raw_root(prerequisite.stdout), "size": len(prerequisite.stdout)},
                    "stderr": {"path": BUILD_STDERR.name, "raw_sha256": raw_root(prerequisite.stderr), "size": len(prerequisite.stderr)},
                },
            },
            {
                "name": "target_lean",
                "command": TARGET_COMMAND,
                "started_at": started_at,
                "completed_at": completed_at,
                "exit_code": completed.returncode,
                "output": {
                    "stdout": {"path": LEAN_STDOUT.name, "raw_sha256": raw_root(completed.stdout), "size": len(completed.stdout)},
                    "stderr": {"path": LEAN_STDERR.name, "raw_sha256": raw_root(completed.stderr), "size": len(completed.stderr)},
                },
            },
        ],
        "environment": {
            "lean": lean_version,
            "lean_toolchain_raw_sha256": TOOLCHAIN_ROOT,
            "lakefile_raw_sha256": LAKEFILE_ROOT,
            "lake_manifest_raw_sha256": LAKE_MANIFEST_ROOT,
            "network_during_archive_materialization": "no_network_operations_in_validated_standard_library_extraction",
            "network_during_build_and_target": "denied_by_sandbox-exec_policy",
        },
        "nonclaims": [
            "This transcript establishes the exact prerequisite build and target commands, inputs, package source commits, exit codes, and retained outputs of this run.",
            "The package source checkouts are public and exactly pinned; two public compiled artifacts and canonical normalized acquisition-command metadata are selectively retained and rooted; HTTP status and final redirect URL were not retained.",
            "The source checkout and every package checkout contained no .lake/build directory before the two retained artifacts were materialized locally with network denied.",
            "The prerequisite used Lake's global --no-cache option under an operating-system network-denial policy, created no build.barrel artifact, and emitted no reservoir.lean-lang.org fetch reference.",
            "This is an exact public compiled-cache replay, not a from-source dependency build.",
            "This same-operator run is not an independent reproduction, Vela Verification, human Decision, or change to Standing.",
        ],
        "transcript_root_definition": "sha256 of canonical JSON after removing only transcript_root",
    }
    transcript["transcript_root"] = root(transcript, "transcript_root")
    INVENTORY.write_bytes(canonical(inventory) + b"\n")
    TRANSCRIPT.write_bytes(canonical(transcript) + b"\n")
    return inventory, transcript


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-checkout", type=Path)
    parser.add_argument("--materialize-validated-tar", nargs=2, metavar=("ARCHIVE", "DESTINATION"), type=Path)
    args = parser.parse_args()
    if args.materialize_validated_tar is not None:
        if args.source_checkout is not None:
            parser.error("--source-checkout and --materialize-validated-tar are mutually exclusive")
        stdout, stderr, exit_code = materialize_archive(*args.materialize_validated_tar)
        print(stdout.decode(), end="")
        if stderr:
            print(stderr.decode(), end="", file=sys.stderr)
        return exit_code
    if args.source_checkout is None:
        parser.error("--source-checkout is required for execution capture")
    inventory, transcript = capture(args.source_checkout)
    print(json.dumps({"inventory_root": inventory["inventory_root"], "transcript_root": transcript["transcript_root"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
