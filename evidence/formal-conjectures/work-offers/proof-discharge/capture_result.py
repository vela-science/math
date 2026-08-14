#!/usr/bin/env python3
"""Capture or verify the first bounded Erdős 887 proof-discharge attempt."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]
PACKET_PATH = HERE.parent / "packets/erdos-887-proof-discharge.v1.json"
TARGET_ID = "erdos:887:proof-discharge"
SOURCE_COMMIT = "158727e43d3be335f902ac7ef6b9beb819e38c9d"
SOURCE_TREE = "80d17febad5b2f724165561f5af74e19156e34d5"
SOURCE_PATH = "FormalConjectures/ErdosProblems/887.lean"
SOURCE_BLOB = "21c7d60d90d013de645b46f318980ba4b4a5d9f7"
SOURCE_RAW_SHA256 = "sha256:c2225a17de2f5210dbdb010bf7e915940d6776daf4ba4220d59b3002856a429a"

AXIOM_PROBE = """import FormalConjectures.ErdosProblems.«887»

#check Erdos887.erdos_887.parts.ii
#print axioms Erdos887.erdos_887.parts.ii
"""

CANDIDATE_PROBE = """import FormalConjectures.ErdosProblems.«887»

open Filter Finset Real
namespace Erdos887

example : ∃ K, ∀ C > (0 : ℝ), ∀ᶠ n in atTop,
    #{ d ∈ Ioo ⌊√n⌋₊ ⌈√n + C * n^((1 : ℝ) / 4)⌉₊ | d ∣ n } ≤ K := by
  aesop

end Erdos887
"""


class CaptureError(RuntimeError):
    """Raised when the retained attempt cannot be produced or verified."""


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _sha256(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _root(value: Any) -> str:
    return _sha256(_canonical_bytes(value))


def _root_without(value: dict[str, Any], field: str) -> str:
    preimage = copy.deepcopy(value)
    preimage.pop(field, None)
    return _root(preimage)


def _write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


def _descriptor(path: Path, raw: bytes) -> dict[str, Any]:
    return {
        "path": path.name,
        "size": len(raw),
        "raw_sha256": _sha256(raw),
    }


def _run(args: list[str], cwd: Path) -> tuple[int, bytes, bytes]:
    result = subprocess.run(args, cwd=cwd, capture_output=True, check=False)
    return result.returncode, result.stdout, result.stderr


def _git(args: list[str], cwd: Path) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise CaptureError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def _validate_source(source: Path) -> dict[str, str]:
    raw = (source / SOURCE_PATH).read_bytes()
    identity = {
        "commit": _git(["rev-parse", "HEAD"], source),
        "tree": _git(["show", "-s", "--format=%T", "HEAD"], source),
        "git_blob_oid": _git(["rev-parse", f"HEAD:{SOURCE_PATH}"], source),
        "raw_sha256": _sha256(raw),
    }
    if identity != {
        "commit": SOURCE_COMMIT,
        "tree": SOURCE_TREE,
        "git_blob_oid": SOURCE_BLOB,
        "raw_sha256": SOURCE_RAW_SHA256,
    }:
        raise CaptureError("source identity drift")
    return identity


def _load_context(workspace: Path) -> dict[str, Any]:
    path = workspace / "attempt-context.v1.json"
    raw = path.read_bytes()
    context = json.loads(raw)
    if raw != _canonical_bytes(context) + b"\n":
        raise CaptureError("attempt context canonical framing drift")
    if context.get("target_id") != TARGET_ID or context.get("authority_effect") != "none":
        raise CaptureError("attempt context identity or authority drift")
    return context


def _capture(workspace: Path, output: Path, *, replace_generated: bool = False) -> dict[str, Any]:
    workspace = workspace.resolve()
    source = workspace / "source"
    output = output.resolve()
    if output.exists():
        if not replace_generated:
            raise CaptureError(f"output already exists: {output}")
        existing_raw = (output / "result.v1.json").read_bytes()
        existing = json.loads(existing_raw)
        if (
            existing_raw != _canonical_bytes(existing) + b"\n"
            or existing.get("target_id") != TARGET_ID
            or existing.get("result_root") != _root_without(existing, "result_root")
        ):
            raise CaptureError("refusing to replace an unrecognized result directory")
        shutil.rmtree(output)
    context = _load_context(workspace)
    identity = _validate_source(source)
    lake = source / ".lake"
    if not lake.exists():
        raise CaptureError("this bounded run requires an explicitly disclosed compatible compiled cache")
    cache_owner = lake.resolve().parent
    source_manifest = (source / "lake-manifest.json").read_bytes()
    cache_manifest = (cache_owner / "lake-manifest.json").read_bytes()
    source_toolchain = (source / "lean-toolchain").read_bytes()
    cache_toolchain = (cache_owner / "lean-toolchain").read_bytes()
    if source_manifest != cache_manifest or source_toolchain != cache_toolchain:
        raise CaptureError("shared compiled cache manifest or toolchain drift")

    axiom_path = source / "ProofAttempt.lean"
    candidate_path = source / "ProofCandidate.lean"
    axiom_path.write_text(AXIOM_PROBE, encoding="utf-8")
    candidate_path.write_text(CANDIDATE_PROBE, encoding="utf-8")
    started = time.monotonic()
    try:
        version_exit, version_stdout, version_stderr = _run(["lake", "env", "lean", "--version"], source)
        axiom_exit, axiom_stdout, axiom_stderr = _run(["lake", "env", "lean", "ProofAttempt.lean"], source)
        candidate_exit, candidate_stdout, candidate_stderr = _run(["lake", "env", "lean", "ProofCandidate.lean"], source)
        search_exit, search_stdout, search_stderr = _run(
            ["git", "grep", "-n", "erdos_887.parts.ii", "HEAD", "--", "*.lean"],
            source,
        )
    finally:
        axiom_path.unlink(missing_ok=True)
        candidate_path.unlink(missing_ok=True)
    elapsed_seconds = round(time.monotonic() - started, 3)
    if version_exit != 0 or axiom_exit != 0 or search_exit != 0:
        raise CaptureError("environment, axiom, or source-search probe failed")
    if b"sorryAx" not in axiom_stdout + axiom_stderr:
        raise CaptureError("axiom audit did not expose the current sorryAx dependency")
    if candidate_exit == 0 or b"unsolved goals" not in candidate_stdout + candidate_stderr:
        raise CaptureError("bounded tactic probe did not retain the expected unsolved goal")
    if _git(["status", "--porcelain"], source):
        raise CaptureError("source checkout remained dirty after capture")

    raw_artifacts = {
        "upstream-887.lean": (source / SOURCE_PATH).read_bytes(),
        "axiom-probe.lean": AXIOM_PROBE.encode("utf-8"),
        "axiom-probe.stdout.txt": axiom_stdout,
        "axiom-probe.stderr.txt": axiom_stderr,
        "candidate-probe.lean": CANDIDATE_PROBE.encode("utf-8"),
        "candidate-probe.stdout.txt": candidate_stdout,
        "candidate-probe.stderr.txt": candidate_stderr,
        "repository-search.stdout.txt": search_stdout,
        "repository-search.stderr.txt": search_stderr,
        "lean-version.stdout.txt": version_stdout,
        "lean-version.stderr.txt": version_stderr,
    }
    for name, raw in raw_artifacts.items():
        _write(output / name, raw)

    execution: dict[str, Any] = {
        "schema": "vela.math.proof-attempt-execution.v1",
        "authority_effect": "none",
        "target_id": TARGET_ID,
        "execution_binding": context["execution_binding"],
        "source": {
            "repository": "https://github.com/google-deepmind/formal-conjectures",
            **identity,
            "path": SOURCE_PATH,
        },
        "environment": {
            "lean_version": version_stdout.decode("utf-8").strip(),
            "lake_manifest_raw_sha256": _sha256(source_manifest),
            "lean_toolchain_raw_sha256": _sha256(source_toolchain),
            "compiled_cache": {
                "kind": "same-machine compatible shared cache",
                "manifest_and_toolchain_equal": True,
                "locator_retained": False,
                "independent_reproduction": False,
            },
        },
        "stages": [
            {"name": "environment", "command": ["lake", "env", "lean", "--version"], "exit_code": version_exit},
            {"name": "axiom_audit", "command": ["lake", "env", "lean", "ProofAttempt.lean"], "exit_code": axiom_exit},
            {"name": "bounded_aesop", "command": ["lake", "env", "lean", "ProofCandidate.lean"], "exit_code": candidate_exit},
            {"name": "source_search", "command": ["git", "grep", "-n", "erdos_887.parts.ii", "HEAD", "--", "*.lean"], "exit_code": search_exit},
        ],
        "elapsed_seconds": elapsed_seconds,
        "artifacts": {name: _descriptor(output / name, raw) for name, raw in sorted(raw_artifacts.items())},
        "nonclaims": [
            "The compatible same-machine compiled cache is disclosed and is not an independent or from-source dependency reproduction.",
            "Successful elaboration of the retained source depends on sorryAx and is not a proof.",
            "Failure of one exhaustive aesop search is not evidence of mathematical impossibility.",
        ],
        "execution_root_definition": "sha256 of canonical JSON after removing only execution_root",
    }
    execution["execution_root"] = _root(execution)
    execution_raw = _canonical_bytes(execution) + b"\n"
    _write(output / "execution.v1.json", execution_raw)

    result: dict[str, Any] = {
        "schema": "vela.math.proof-attempt-result.v1",
        "authority_effect": "none",
        "target_id": TARGET_ID,
        "packet_root": context["execution_binding"]["packet_root"],
        "execution_binding": context["execution_binding"],
        "producer": {
            "actor_class": "agent",
            "actor_id": "agent:codex-root",
            "provider": "OpenAI",
            "interface": "Codex",
            "model_family": "GPT-5",
            "exact_serving_model": "not_exposed_to_task_runtime",
            "independent_of_offer_author": False,
            "shared_dependencies": ["same task context", "same operator", "same local compiled cache", "same public source"],
        },
        "terminal_state": "not_proved_within_declared_bounds",
        "declared_bounds": context["declared_bounds"],
        "source_roots": {
            "commit": SOURCE_COMMIT,
            "tree": SOURCE_TREE,
            "path": SOURCE_PATH,
            "git_blob_oid": SOURCE_BLOB,
            "raw_sha256": SOURCE_RAW_SHA256,
        },
        "artifacts": {
            "execution": {
                "path": "execution.v1.json",
                "size": len(execution_raw),
                "raw_sha256": _sha256(execution_raw),
                "root": execution["execution_root"],
            },
            **{name: _descriptor(output / name, raw) for name, raw in sorted(raw_artifacts.items())},
        },
        "findings": [
            {
                "kind": "exact_source_status",
                "finding": "The current exact declaration is still category research open and its retained proof body is sorry.",
                "evidence": ["upstream-887.lean", "axiom-probe.stdout.txt", "repository-search.stdout.txt"],
            },
            {
                "kind": "axiom_dependency",
                "finding": "The exact declaration currently depends on sorryAx in addition to standard logical axioms.",
                "evidence": ["axiom-probe.stdout.txt"],
            },
            {
                "kind": "bounded_tactic_result",
                "finding": "Exhaustive aesop did not prove the target; the remaining normalized goal is an absolute K followed by a C-dependent eventual threshold.",
                "evidence": ["candidate-probe.stdout.txt", "candidate-probe.stderr.txt"],
            },
            {
                "kind": "primary_problem_record",
                "finding": "The current Erdős Problems record labels problem 887 open, says finite computation cannot resolve it, and distinguishes the known C-dependent 1+C^2 bound from the requested absolute K.",
                "locator": "https://www.erdosproblems.com/887",
                "accessed_on": "2026-08-13",
                "retained_source_bytes": False,
            },
        ],
        "remaining_obligations": [
            "Develop new number-theoretic control that removes dependence on C, or locate and verify literature that already does so.",
            "Translate any such argument into Lean and discharge the exact parts.ii declaration without sorryAx.",
            "Obtain separately attributed proof review and an independent execution when a proof candidate exists.",
        ],
        "nonclaims": [
            "This bounded result does not establish falsehood, impossibility, or exhaustion of proof strategies.",
            "The primary-source status observation is a locator-bound reading, not retained webpage custody.",
            "This result is not a Vela Verification, Decision, Event, change to Standing, or upstream contribution.",
            "Agent provenance is descriptive and is not a lower or higher evidentiary rank than human provenance.",
        ],
        "result_root_definition": "sha256 of canonical JSON after removing only result_root",
    }
    result["result_root"] = _root(result)
    _write(output / "result.v1.json", _canonical_bytes(result) + b"\n")
    return result


def _check(output: Path) -> dict[str, Any]:
    output = output.resolve()
    result_raw = (output / "result.v1.json").read_bytes()
    result = json.loads(result_raw)
    if result_raw != _canonical_bytes(result) + b"\n" or result.get("result_root") != _root_without(result, "result_root"):
        raise CaptureError("result canonical framing or root drift")
    if result.get("authority_effect") != "none" or result.get("target_id") != TARGET_ID:
        raise CaptureError("result identity or authority drift")
    if result.get("terminal_state") != "not_proved_within_declared_bounds":
        raise CaptureError("unexpected retained terminal state")
    packet_raw = PACKET_PATH.read_bytes()
    packet = json.loads(packet_raw)
    if packet_raw != _canonical_bytes(packet) + b"\n" or packet.get("packet_root") != _root_without(packet, "packet_root"):
        raise CaptureError("proof-discharge packet canonical framing or root drift")
    binding = {
        "schema": "vela.execution-binding.v1",
        "packet_root": packet["packet_root"],
        "profile_root": packet["execution_components"]["producer_profile"]["root"],
        "verifier_capsule_root": packet["execution_components"]["verifier_capsule"]["root"],
        "result_contract_root": packet["execution_components"]["result_contract"]["root"],
    }
    if result.get("packet_root") != packet["packet_root"] or result.get("execution_binding") != binding:
        raise CaptureError("result execution binding drift")
    if len(result_raw) > 131072:
        raise CaptureError("result exceeds its declared maximum size")
    for descriptor in result.get("artifacts", {}).values():
        path = (output / descriptor["path"]).resolve()
        if output not in path.parents:
            raise CaptureError("artifact path escapes result custody")
        raw = path.read_bytes()
        if len(raw) != descriptor["size"] or _sha256(raw) != descriptor["raw_sha256"]:
            raise CaptureError(f"artifact drift: {descriptor['path']}")
    execution = json.loads((output / "execution.v1.json").read_bytes())
    if execution.get("execution_root") != _root_without(execution, "execution_root"):
        raise CaptureError("execution root drift")
    if execution.get("execution_binding") != binding or execution.get("source", {}).get("commit") != SOURCE_COMMIT:
        raise CaptureError("execution input binding drift")
    if result["artifacts"]["execution"]["root"] != execution["execution_root"]:
        raise CaptureError("result execution binding drift")
    if b"sorryAx" not in (output / "axiom-probe.stdout.txt").read_bytes():
        raise CaptureError("retained axiom result drift")
    source_raw = (output / "upstream-887.lean").read_bytes()
    if _sha256(source_raw) != SOURCE_RAW_SHA256 or b"theorem erdos_887.parts.ii" not in source_raw or b"category research open" not in source_raw:
        raise CaptureError("retained exact source drift")
    candidate_output = (output / "candidate-probe.stdout.txt").read_bytes() + (output / "candidate-probe.stderr.txt").read_bytes()
    if b"unsolved goals" not in candidate_output:
        raise CaptureError("retained tactic result drift")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--replace-generated", action="store_true")
    args = parser.parse_args()
    if args.check:
        result = _check(args.output)
    else:
        if args.workspace is None:
            parser.error("--workspace is required unless --check is used")
        result = _capture(args.workspace, args.output, replace_generated=args.replace_generated)
    print(json.dumps({"ok": True, "result_root": result["result_root"], "terminal_state": result["terminal_state"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
