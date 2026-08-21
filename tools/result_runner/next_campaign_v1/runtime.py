#!/usr/bin/env python3
"""Lean-aware verification and single-cell campaign controls.

This module is prospective execution software.  It does not create Vela
Protocol objects, scientific acceptance, authority, or Standing.
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import functools
import json
import os
import pathlib
import re
import shlex
import sys
from dataclasses import dataclass
from typing import Any, Iterable


RUNNER_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RUNNER_ROOT))
import runner  # noqa: E402


HEX64 = re.compile(r"[0-9a-f]{64}")
GIT40 = re.compile(r"[0-9a-f]{40}")
DECLARATION = re.compile(r"[A-Za-z_][A-Za-z0-9_'.]*(?:\.[A-Za-z_][A-Za-z0-9_']*)*")
PLACEHOLDER = re.compile(r"(?m)(?:\bsorry\b|\badmit\b|\baxiom\b|\bunsafe\b)")
AXIOM_LIST = re.compile(r"depends on axioms:\s*\[([^]]*)\]")
NO_AXIOMS = re.compile(r"does not depend on any axioms")
ALLOWED_AXIOMS = frozenset({"propext", "Quot.sound", "Classical.choice"})
EXACT_FIVE = 5


class HardeningError(runner.RunnerError):
    """A typed fail-closed prospective runner error."""


def _hex(value: Any, label: str, *, git: bool = False) -> str:
    pattern = GIT40 if git else HEX64
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise HardeningError("invalid_binding", f"{label} is not an exact digest")
    return value


def _load(path: pathlib.Path) -> Any:
    try:
        return json.loads(path.read_text())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise HardeningError("invalid_json", f"invalid JSON: {path}") from error


def _new_directory(path: pathlib.Path) -> pathlib.Path:
    if not path.is_absolute():
        raise HardeningError("path_not_absolute", "output must be absolute")
    if path.exists() or path.is_symlink():
        raise HardeningError("output_collision", "output must not exist")
    path.mkdir(parents=False)
    return path


def _regular_file(path: pathlib.Path, label: str) -> pathlib.Path:
    return runner.canonical_existing_path(path, label, file=True)


def _tree_root(paths: Iterable[pathlib.Path], base: pathlib.Path) -> str:
    rows = runner.manifest(list(paths), base)
    return runner.sha256_bytes(runner.canonical_json(rows))


@dataclass(frozen=True)
class RuntimePin:
    image: str
    platform: str
    source_repository: str
    source_commit: str
    source_tree: str
    source_archive_sha256: str
    lean_toolchain_sha256: str
    lake_manifest_sha256: str
    lean_version: str
    codex_version: str
    embedded_source: str

    @classmethod
    def read(cls, path: pathlib.Path) -> "RuntimePin":
        value = _load(_regular_file(path, "runtime pin"))
        expected = {
            "codex_version",
            "embedded_source",
            "image",
            "lake_manifest_sha256",
            "lean_toolchain_sha256",
            "lean_version",
            "platform",
            "schema",
            "source_archive_sha256",
            "source_commit",
            "source_repository",
            "source_tree",
        }
        if not isinstance(value, dict) or set(value) != expected:
            raise HardeningError("runtime_pin", "runtime pin keys do not match v1")
        if value["schema"] != "result-runner.next-campaign-runtime.v1":
            raise HardeningError("runtime_pin", "unexpected runtime pin schema")
        if not runner.IMAGE_RE.fullmatch(value["image"]):
            raise HardeningError("runtime_pin", "runtime image is not digest-pinned")
        if value["platform"] != "linux/arm64":
            raise HardeningError("runtime_pin", "runtime platform must be linux/arm64")
        _hex(value["source_commit"], "source commit", git=True)
        _hex(value["source_tree"], "source tree", git=True)
        for name in (
            "source_archive_sha256",
            "lean_toolchain_sha256",
            "lake_manifest_sha256",
        ):
            _hex(value[name], name)
        if value["embedded_source"] != "/opt/formal-conjectures":
            raise HardeningError("runtime_pin", "unexpected embedded source root")
        return cls(**{name: value[name] for name in cls.__dataclass_fields__})

    def as_json(self) -> dict[str, str]:
        return {name: getattr(self, name) for name in self.__dataclass_fields__}


def _expected_source(pin: RuntimePin, repo: pathlib.Path) -> runner.GitSnapshot:
    snapshot = runner.git_snapshot(repo)
    runner.assert_expected_source(
        snapshot,
        repository_id=pin.source_repository,
        commit=pin.source_commit,
        tree=pin.source_tree,
        archive_sha256=pin.source_archive_sha256,
    )
    return snapshot


def _docker_context() -> None:
    context = runner.run(["docker", "context", "show"]).stdout.decode().strip()
    if context != "desktop-linux":
        raise HardeningError(
            "docker_context", f"required desktop-linux, observed {context!r}"
        )


def _preflight_script(pin: RuntimePin) -> str:
    expected = {
        "commit": pin.source_commit,
        "tree": pin.source_tree,
        "archive": pin.source_archive_sha256,
        "toolchain": pin.lean_toolchain_sha256,
        "manifest": pin.lake_manifest_sha256,
        "lean": pin.lean_version,
        "codex": pin.codex_version,
    }
    quoted = {name: shlex.quote(value) for name, value in expected.items()}
    return f"""set -euo pipefail
test \"$(git rev-parse HEAD)\" = {quoted['commit']}
test \"$(git rev-parse HEAD^{{tree}})\" = {quoted['tree']}
test \"$(git archive --format=tar HEAD | sha256sum | cut -d' ' -f1)\" = {quoted['archive']}
test \"$(sha256sum lean-toolchain | cut -d' ' -f1)\" = {quoted['toolchain']}
test \"$(sha256sum lake-manifest.json | cut -d' ' -f1)\" = {quoted['manifest']}
test \"$(git -C /source rev-parse HEAD)\" = {quoted['commit']}
test \"$(git -C /source rev-parse HEAD^{{tree}})\" = {quoted['tree']}
test \"$(git -C /source archive --format=tar HEAD | sha256sum | cut -d' ' -f1)\" = {quoted['archive']}
test -z \"$(git -C /source status --porcelain=v1 --untracked-files=all)\"
lake env lean --version | grep -F {quoted['lean']}
codex --version | grep -F {quoted['codex']}
lake env lean FormalConjectures/ErdosProblems/1052.lean -o /tmp/preflight.olean
test -s /tmp/preflight.olean
rm /tmp/preflight.olean
"""


def preflight_runtime(
    pin_path: pathlib.Path,
    repo: pathlib.Path,
    output: pathlib.Path,
    *,
    timeout_seconds: float = 300.0,
) -> dict[str, Any]:
    """Prove the pinned image can run the exact source toolchain without network."""

    pin = RuntimePin.read(pin_path)
    repo = runner.canonical_existing_path(repo, "source repository", directory=True)
    before = _expected_source(pin, repo)
    _docker_context()
    image = runner.inspect_docker_image(pin.image)
    destination = _new_directory(output)
    argv = [
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
        "--read-only",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=268435456",
        "--mount",
        f"type=bind,src={repo},dst=/source,readonly",
        "--workdir",
        pin.embedded_source,
        "--entrypoint",
        "bash",
        pin.image,
        "-c",
        _preflight_script(pin),
    ]
    completed = runner.run_bounded(
        argv,
        timeout_seconds=timeout_seconds,
        stdout_limit=1 << 20,
        stderr_limit=1 << 20,
    )
    (destination / "stdout").write_bytes(completed.stdout)
    (destination / "stderr").write_bytes(completed.stderr)
    after = _expected_source(pin, repo)
    status = (
        "pass"
        if completed.status == "completed" and completed.returncode == 0
        else "infrastructure_failure"
    )
    receipt = {
        "argv": argv,
        "docker_image": image.as_json(),
        "elapsed_seconds": round(completed.elapsed_seconds, 3),
        "execution_status": completed.status,
        "exit_code": completed.returncode,
        "network": "none",
        "runtime_pin_sha256": runner.sha256_file(pin_path),
        "source_after": after.as_json(),
        "source_before": before.as_json(),
        "status": status,
        "stderr_sha256": runner.sha256_bytes(completed.stderr),
        "stdout_sha256": runner.sha256_bytes(completed.stdout),
        "type": "next-campaign-runtime-preflight-v1",
        "verifier_sha256": runner.sha256_file(pathlib.Path(__file__)),
    }
    runner.write_json(destination / "receipt.json", receipt)
    if status != "pass":
        raise HardeningError(
            "runtime_preflight", "pinned Lean runtime preflight failed"
        )
    return receipt


def _parse_axioms(stdout: bytes) -> tuple[tuple[str, ...], bool]:
    text = stdout.decode(errors="replace")
    match = AXIOM_LIST.search(text)
    if match:
        return (
            tuple(
                sorted(
                    item.strip() for item in match.group(1).split(",") if item.strip()
                )
            ),
            True,
        )
    return (), bool(NO_AXIOMS.search(text))


def _proof_classification(
    *,
    declared_status: str,
    compiled: bool,
    axiom_audit_complete: bool,
    placeholders: list[str],
    unsupported_axioms: list[str],
) -> tuple[str, bool]:
    if not compiled:
        return (
            "invalid" if declared_status == "checked_proof" else "proof_sketch",
            False,
        )
    if not axiom_audit_complete or placeholders or unsupported_axioms:
        return ("repairable", False)
    return ("checked_proof", True)


def verify_proof(
    *,
    pin_path: pathlib.Path,
    repo: pathlib.Path,
    candidate_result: pathlib.Path,
    candidate_artifact: pathlib.Path,
    declaration: str,
    output: pathlib.Path,
    timeout_seconds: float = 300.0,
) -> dict[str, Any]:
    """Compile one submitted proof artifact and retain an immutable receipt."""

    pin = RuntimePin.read(pin_path)
    if not DECLARATION.fullmatch(declaration):
        raise HardeningError("declaration", "invalid Lean declaration name")
    result_path = _regular_file(candidate_result, "candidate result")
    artifact_path = _regular_file(candidate_artifact, "candidate artifact")
    result = _load(result_path)
    if not isinstance(result, dict) or not isinstance(result.get("result_status"), str):
        raise HardeningError("candidate_result", "candidate result_status is required")
    repo = runner.canonical_existing_path(repo, "source repository", directory=True)
    before = _expected_source(pin, repo)
    _docker_context()
    image = runner.inspect_docker_image(pin.image)
    destination = _new_directory(output)
    runtime_output = destination / "runtime-output"
    runtime_output.mkdir()
    artifact_bytes = artifact_path.read_bytes()
    audited = destination / "submitted-audited.lean"
    audited.write_bytes(artifact_bytes + f"\n#print axioms {declaration}\n".encode())
    placeholders = sorted(
        set(PLACEHOLDER.findall(artifact_bytes.decode(errors="replace")))
    )
    argv = [
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
        "--read-only",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=268435456",
        "--mount",
        f"type=bind,src={audited},dst={pin.embedded_source}/ResultRunnerSubmitted.lean,readonly",
        "--mount",
        f"type=bind,src={runtime_output},dst=/proof-output",
        "--workdir",
        pin.embedded_source,
        "--entrypoint",
        "lake",
        pin.image,
        "env",
        "lean",
        f"{pin.embedded_source}/ResultRunnerSubmitted.lean",
        "-o",
        "/proof-output/Submitted.olean",
    ]
    completed = runner.run_bounded(
        argv,
        timeout_seconds=timeout_seconds,
        stdout_limit=2 << 20,
        stderr_limit=2 << 20,
        monitor=runner.runtime_monitor(
            runtime_output,
            max_files=8,
            max_bytes=32 << 20,
            max_result_bytes=32 << 20,
        ),
    )
    (destination / "stdout").write_bytes(completed.stdout)
    (destination / "stderr").write_bytes(completed.stderr)
    compiled = completed.status == "completed" and completed.returncode == 0
    axioms, axiom_audit_complete = _parse_axioms(completed.stdout)
    unsupported_axioms = sorted(set(axioms) - ALLOWED_AXIOMS)
    classification, conversion_ready = _proof_classification(
        declared_status=result["result_status"],
        compiled=compiled,
        axiom_audit_complete=axiom_audit_complete,
        placeholders=placeholders,
        unsupported_axioms=unsupported_axioms,
    )
    generated = sorted(path for path in runtime_output.rglob("*") if path.is_file())
    after = _expected_source(pin, repo)
    receipt = {
        "axiom_audit": {
            "allowed": sorted(ALLOWED_AXIOMS),
            "complete": axiom_audit_complete,
            "observed": list(axioms),
            "unsupported": unsupported_axioms,
        },
        "candidate_artifact_sha256": runner.sha256_file(artifact_path),
        "candidate_result_sha256": runner.sha256_file(result_path),
        "classification": classification,
        "clean_worktree_after": after.clean,
        "clean_worktree_before": before.clean,
        "command": argv,
        "compiled": compiled,
        "conversion_ready": conversion_ready,
        "declaration": declaration,
        "docker_image": image.as_json(),
        "elapsed_seconds": round(completed.elapsed_seconds, 3),
        "execution_status": completed.status,
        "exit_code": completed.returncode,
        "generated_artifact_root": _tree_root(generated, runtime_output),
        "generated_files": runner.manifest(generated, runtime_output),
        "network": "none",
        "placeholder_audit": placeholders,
        "runtime_pin_sha256": runner.sha256_file(pin_path),
        "source_after": after.as_json(),
        "source_before": before.as_json(),
        "stderr_sha256": runner.sha256_bytes(completed.stderr),
        "stdout_sha256": runner.sha256_bytes(completed.stdout),
        "submitted_audited_sha256": runner.sha256_file(audited),
        "type": "source-native-proof-verification-v1",
        "verifier_sha256": runner.sha256_file(pathlib.Path(__file__)),
    }
    runner.write_json(destination / "receipt.json", receipt)
    return receipt


def verify_nonconversion(
    *,
    kind: str,
    pin_path: pathlib.Path,
    repo: pathlib.Path,
    candidate_result: pathlib.Path,
    evidence: pathlib.Path,
    output: pathlib.Path,
) -> dict[str, Any]:
    """Retain a supported duplicate or non-result as a valid non-conversion."""

    labels = {"duplicate": "duplicate_non_conversion", "non_result": "valid_non_result"}
    if kind not in labels:
        raise HardeningError("nonconversion_kind", "expected duplicate or non_result")
    pin = RuntimePin.read(pin_path)
    snapshot = _expected_source(pin, repo)
    result_path = _regular_file(candidate_result, "candidate result")
    evidence_path = _regular_file(evidence, "source-native evidence")
    destination = _new_directory(output)
    receipt = {
        "candidate_result_sha256": runner.sha256_file(result_path),
        "classification": labels[kind],
        "conversion_ready": False,
        "evidence_sha256": runner.sha256_file(evidence_path),
        "infrastructure_failure": False,
        "runtime_pin_sha256": runner.sha256_file(pin_path),
        "source": snapshot.as_json(),
        "task_outcome_valid": True,
        "type": "source-native-nonconversion-verification-v1",
        "verifier_sha256": runner.sha256_file(pathlib.Path(__file__)),
    }
    runner.write_json(destination / "receipt.json", receipt)
    return receipt


def record_reviewer_correction(
    *,
    submitted_result: pathlib.Path,
    submitted_receipt: pathlib.Path,
    corrected_artifact: pathlib.Path,
    corrected_receipt: pathlib.Path,
    output: pathlib.Path,
) -> dict[str, Any]:
    """Root a reviewer correction without changing the submitted candidate."""

    files = [
        _regular_file(submitted_result, "submitted result"),
        _regular_file(submitted_receipt, "submitted verification receipt"),
        _regular_file(corrected_artifact, "reviewer correction artifact"),
        _regular_file(corrected_receipt, "reviewer correction receipt"),
    ]
    original_result = files[0].read_bytes()
    original_receipt = _load(files[1])
    corrected = _load(files[3])
    if corrected.get("candidate_artifact_sha256") != runner.sha256_file(files[2]):
        raise HardeningError(
            "correction_binding", "correction receipt/artifact mismatch"
        )
    destination = _new_directory(output)
    value = {
        "corrected_artifact_sha256": runner.sha256_file(files[2]),
        "corrected_verification_receipt_sha256": runner.sha256_file(files[3]),
        "correction_may_upgrade_submitted_candidate": False,
        "reviewer_artifact_root": runner.sha256_bytes(
            runner.canonical_json(
                {
                    "artifact": runner.sha256_file(files[2]),
                    "receipt": runner.sha256_file(files[3]),
                }
            )
        ),
        "submitted_classification": original_receipt.get("classification"),
        "submitted_conversion_ready": original_receipt.get("conversion_ready"),
        "submitted_result_sha256": runner.sha256_bytes(original_result),
        "submitted_verification_receipt_sha256": runner.sha256_file(files[1]),
        "type": "reviewer-proof-correction-v1",
    }
    runner.write_json(destination / "reviewer-correction.json", value)
    if files[0].read_bytes() != original_result:
        raise HardeningError("submitted_mutation", "submitted candidate changed")
    return value


def validate_canary(value: dict[str, Any], runtime_pin_sha256: str) -> None:
    """Require the neutral, non-scoring one-run runtime calibration contract."""

    required_equal = {
        "campaign_denominator_effect": "excluded",
        "credential_findings": 0,
        "exactly_one_permit_consumed": True,
        "lean_preflight": "pass",
        "compile_receipt": "pass",
        "model_auth_access": "pass",
        "provider_requests": 1,
        "status": "pass",
        "teardown": "pass",
        "timeout_enforced": True,
        "usage_parsed": True,
    }
    if value.get("runtime_pin_sha256") != runtime_pin_sha256:
        raise HardeningError("canary_binding", "canary runtime binding mismatch")
    for name, expected in required_equal.items():
        if value.get(name) != expected:
            raise HardeningError("canary_incomplete", f"canary check failed: {name}")
    for name in ("output_sha256", "compile_receipt_sha256", "permit_sha256"):
        _hex(value.get(name), f"canary {name}")


def freeze_cell_plan(
    *,
    campaign_id: str,
    config_root: str,
    image: str,
    source_root: str,
    candidate_assignments: list[dict[str, Any]],
    evaluator_assignments: list[dict[str, Any]],
    canary_receipt: pathlib.Path,
    runtime_pin: pathlib.Path,
    independent_review: pathlib.Path,
    output: pathlib.Path,
) -> dict[str, Any]:
    """Freeze five candidate plus five evaluator cells only after canary/review PASS."""

    if (
        len(candidate_assignments) != EXACT_FIVE
        or len(evaluator_assignments) != EXACT_FIVE
    ):
        raise HardeningError(
            "denominator", "exactly five candidate and five evaluator cells required"
        )
    for value, label in ((config_root, "config root"), (source_root, "source root")):
        _hex(value, label)
    if not runner.IMAGE_RE.fullmatch(image):
        raise HardeningError("image_digest", "campaign image must be digest-pinned")
    runtime_pin_sha = runner.sha256_file(_regular_file(runtime_pin, "runtime pin"))
    pin = RuntimePin.read(runtime_pin)
    if image != pin.image:
        raise HardeningError("image_binding", "campaign image differs from runtime pin")
    canary = _load(_regular_file(canary_receipt, "canary receipt"))
    validate_canary(canary, runtime_pin_sha)
    review = _load(_regular_file(independent_review, "independent review"))
    if (
        review.get("status") != "pass"
        or review.get("runtime_pin_sha256") != runtime_pin_sha
    ):
        raise HardeningError(
            "independent_review", "immutable runtime review has not passed"
        )
    cells: list[dict[str, Any]] = []
    seen: set[str] = set()
    for role, assignments in (
        ("candidate", candidate_assignments),
        ("evaluator", evaluator_assignments),
    ):
        for index, assignment in enumerate(assignments, 1):
            if not isinstance(assignment, dict):
                raise HardeningError("assignment", "assignment must be an object")
            cell_id = assignment.get("cell_id")
            run_root = assignment.get("run_root")
            assignment_root = assignment.get("assignment_root")
            if not isinstance(cell_id, str) or cell_id in seen:
                raise HardeningError("assignment", "cell ids must be unique strings")
            seen.add(cell_id)
            _hex(run_root, "run root")
            _hex(assignment_root, "assignment root")
            cells.append(
                {
                    "assignment_root": assignment_root,
                    "cell_id": cell_id,
                    "ordinal": len(cells) + 1,
                    "role": role,
                    "run_root": run_root,
                    "target_ordinal": index,
                }
            )
    plan = {
        "campaign_id": campaign_id,
        "candidate_denominator": EXACT_FIVE,
        "cells": cells,
        "config_root": config_root,
        "evaluator_denominator": EXACT_FIVE,
        "image": image,
        "independent_review_sha256": runner.sha256_file(independent_review),
        "neutral_canary_sha256": runner.sha256_file(canary_receipt),
        "retries": 0,
        "runtime_pin_sha256": runtime_pin_sha,
        "source_root": source_root,
        "type": "result-runner-fixed-cell-plan-v1",
        "verifier_sha256": runner.sha256_file(pathlib.Path(__file__)),
    }
    destination = _new_directory(output)
    runner.write_json(destination / "plan.json", plan)
    state = {
        "active_permit": None,
        "completed": [],
        "next_ordinal": 1,
        "plan_sha256": runner.sha256_file(destination / "plan.json"),
        "status": "operator_hold",
        "type": "result-runner-permit-state-v1",
        "verifications": {},
    }
    runner.write_json(destination / "state.json", state)
    return plan


def _write_state(path: pathlib.Path, value: dict[str, Any]) -> None:
    temporary = path.with_suffix(".tmp")
    runner.write_json(temporary, value)
    os.replace(temporary, path)


@contextlib.contextmanager
def _state_lock(state_path: pathlib.Path):
    lock_path = state_path.with_name(state_path.name + ".lock")
    descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _state_locked(function):
    @functools.wraps(function)
    def wrapped(*args, **kwargs):
        state_path = kwargs.get("state_path")
        if state_path is None:
            state_path = args[1]
        with _state_lock(state_path):
            return function(*args, **kwargs)

    return wrapped


@_state_locked
def mint_permit(
    plan_path: pathlib.Path,
    state_path: pathlib.Path,
    cell_id: str,
    output: pathlib.Path,
) -> dict[str, Any]:
    """Mint only the next predetermined cell permit while held."""

    plan = _load(_regular_file(plan_path, "cell plan"))
    state = _load(_regular_file(state_path, "permit state"))
    plan_sha = runner.sha256_file(plan_path)
    if state.get("plan_sha256") != plan_sha or state.get("status") != "operator_hold":
        raise HardeningError("permit_state", "state is not a held plan binding")
    if state.get("active_permit") is not None:
        raise HardeningError("active_permit", "one permit is already active")
    ordinal = state.get("next_ordinal")
    cells = plan.get("cells", [])
    if not isinstance(ordinal, int) or ordinal < 1 or ordinal > len(cells):
        raise HardeningError("permit_complete", "no further cell is eligible")
    cell = cells[ordinal - 1]
    if cell.get("cell_id") != cell_id:
        raise HardeningError(
            "permit_order", "requested cell is not the predetermined next cell"
        )
    if cell.get("role") == "evaluator":
        target = str(cell.get("target_ordinal"))
        verifications = state.get("verifications", {})
        if not isinstance(verifications, dict) or target not in verifications:
            raise HardeningError(
                "verification_required",
                "source-native verification must be bound before evaluator permit",
            )
        source_verification_sha256 = verifications[target].get("receipt_sha256")
        _hex(source_verification_sha256, "source verification receipt")
    else:
        source_verification_sha256 = None
    permit = {
        "assignment_root": cell["assignment_root"],
        "campaign_id": plan["campaign_id"],
        "cell_id": cell_id,
        "config_root": plan["config_root"],
        "image": plan["image"],
        "ordinal": ordinal,
        "plan_sha256": plan_sha,
        "role": cell["role"],
        "run_root": cell["run_root"],
        "single_use": True,
        "source_root": plan["source_root"],
        "target_ordinal": cell.get("target_ordinal"),
        "type": "result-runner-single-use-permit-v1",
    }
    if source_verification_sha256 is not None:
        permit["source_verification_sha256"] = source_verification_sha256
    permit_root = runner.sha256_bytes(runner.canonical_json(permit))
    permit["permit_root"] = permit_root
    destination = _new_directory(output)
    permit_path = destination / "permit.json"
    runner.write_json(permit_path, permit)
    state["active_permit"] = {
        "cell_id": cell_id,
        "consumed": False,
        "permit_root": permit_root,
        "permit_sha256": runner.sha256_file(permit_path),
    }
    _write_state(state_path, state)
    return permit


@_state_locked
def consume_permit(
    permit_path: pathlib.Path, state_path: pathlib.Path
) -> dict[str, Any]:
    """Consume one exact permit once; never auto-advance or mint another."""

    permit = _load(_regular_file(permit_path, "permit"))
    state = _load(_regular_file(state_path, "permit state"))
    active = state.get("active_permit")
    if not isinstance(active, dict) or active.get(
        "permit_sha256"
    ) != runner.sha256_file(permit_path):
        raise HardeningError("permit_binding", "permit is not the active exact bytes")
    if active.get("consumed") is not False:
        raise HardeningError("permit_reuse", "permit was already consumed")
    active["consumed"] = True
    state["status"] = "cell_running"
    _write_state(state_path, state)
    return permit


@_state_locked
def record_terminal(
    permit_path: pathlib.Path,
    state_path: pathlib.Path,
    terminal_receipt: pathlib.Path,
) -> dict[str, Any]:
    """Validate one terminal receipt, then return to hold without auto-advance."""

    permit = _load(_regular_file(permit_path, "permit"))
    state = _load(_regular_file(state_path, "permit state"))
    receipt = _load(_regular_file(terminal_receipt, "terminal receipt"))
    active = state.get("active_permit")
    if (
        state.get("status") != "cell_running"
        or not isinstance(active, dict)
        or active.get("consumed") is not True
    ):
        raise HardeningError(
            "terminal_state", "no consumed permit awaits a terminal receipt"
        )
    if active.get("permit_sha256") != runner.sha256_file(permit_path) or active.get(
        "permit_root"
    ) != permit.get("permit_root"):
        raise HardeningError("terminal_permit", "terminal uses a different permit")
    for name in (
        "assignment_root",
        "campaign_id",
        "cell_id",
        "config_root",
        "image",
        "permit_root",
        "role",
        "run_root",
        "source_root",
    ):
        if receipt.get(name) != permit.get(name):
            raise HardeningError(
                "terminal_binding", f"terminal receipt mismatches {name}"
            )
    if permit.get("role") == "evaluator" and receipt.get(
        "source_verification_sha256"
    ) != permit.get("source_verification_sha256"):
        raise HardeningError(
            "terminal_binding",
            "evaluator terminal receipt mismatches source verification",
        )
    if receipt.get("terminal") is not True:
        raise HardeningError("terminal_binding", "receipt is not terminal")
    completed = state.get("completed")
    if not isinstance(completed, list):
        raise HardeningError("permit_state", "completed ledger is invalid")
    completed.append(
        {
            "cell_id": permit["cell_id"],
            "permit_root": permit["permit_root"],
            "receipt_sha256": runner.sha256_file(terminal_receipt),
            "role": permit["role"],
            "target_ordinal": permit.get("target_ordinal"),
        }
    )
    state["active_permit"] = None
    state["next_ordinal"] = permit["ordinal"] + 1
    state["status"] = "operator_hold"
    _write_state(state_path, state)
    return state


@_state_locked
def bind_source_verification(
    plan_path: pathlib.Path,
    state_path: pathlib.Path,
    candidate_cell_id: str,
    terminal_receipt: pathlib.Path,
    verification_receipt: pathlib.Path,
) -> dict[str, Any]:
    """Bind a deterministic candidate verification before evaluator launch."""

    plan = _load(_regular_file(plan_path, "cell plan"))
    state = _load(_regular_file(state_path, "permit state"))
    terminal_path = _regular_file(terminal_receipt, "candidate terminal receipt")
    verification_path = _regular_file(
        verification_receipt, "source-native verification receipt"
    )
    terminal = _load(terminal_path)
    verification = _load(verification_path)
    if state.get("status") != "operator_hold" or state.get(
        "plan_sha256"
    ) != runner.sha256_file(plan_path):
        raise HardeningError("verification_state", "plan is not held for verification")
    cell = next(
        (
            value
            for value in plan.get("cells", [])
            if value.get("cell_id") == candidate_cell_id
            and value.get("role") == "candidate"
        ),
        None,
    )
    if cell is None:
        raise HardeningError("verification_cell", "unknown candidate cell")
    completed = next(
        (
            value
            for value in state.get("completed", [])
            if value.get("cell_id") == candidate_cell_id
        ),
        None,
    )
    if completed is None or completed.get("receipt_sha256") != runner.sha256_file(
        terminal_path
    ):
        raise HardeningError(
            "verification_terminal", "candidate terminal bytes mismatch"
        )
    if terminal.get("result_sha256") != verification.get("candidate_result_sha256"):
        raise HardeningError(
            "verification_result", "verification does not bind candidate Result"
        )
    if verification.get("type") not in {
        "source-native-proof-verification-v1",
        "source-native-nonconversion-verification-v1",
    }:
        raise HardeningError(
            "verification_type", "unsupported candidate verification receipt"
        )
    verifications = state.setdefault("verifications", {})
    target = str(cell["target_ordinal"])
    if target in verifications:
        raise HardeningError(
            "verification_reuse", "candidate verification already bound"
        )
    verifications[target] = {
        "candidate_cell_id": candidate_cell_id,
        "classification": verification.get("classification"),
        "receipt_sha256": runner.sha256_file(verification_path),
        "terminal_receipt_sha256": runner.sha256_file(terminal_path),
    }
    _write_state(state_path, state)
    return state


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    preflight = sub.add_parser("preflight")
    preflight.add_argument("--pin", type=pathlib.Path, required=True)
    preflight.add_argument("--repo", type=pathlib.Path, required=True)
    preflight.add_argument("--output", type=pathlib.Path, required=True)
    proof = sub.add_parser("verify-proof")
    proof.add_argument("--pin", type=pathlib.Path, required=True)
    proof.add_argument("--repo", type=pathlib.Path, required=True)
    proof.add_argument("--candidate-result", type=pathlib.Path, required=True)
    proof.add_argument("--candidate-artifact", type=pathlib.Path, required=True)
    proof.add_argument("--declaration", required=True)
    proof.add_argument("--output", type=pathlib.Path, required=True)
    nonconversion = sub.add_parser("verify-nonconversion")
    nonconversion.add_argument(
        "--kind", choices=("duplicate", "non_result"), required=True
    )
    nonconversion.add_argument("--pin", type=pathlib.Path, required=True)
    nonconversion.add_argument("--repo", type=pathlib.Path, required=True)
    nonconversion.add_argument("--candidate-result", type=pathlib.Path, required=True)
    nonconversion.add_argument("--evidence", type=pathlib.Path, required=True)
    nonconversion.add_argument("--output", type=pathlib.Path, required=True)
    correction = sub.add_parser("record-correction")
    correction.add_argument("--submitted-result", type=pathlib.Path, required=True)
    correction.add_argument("--submitted-receipt", type=pathlib.Path, required=True)
    correction.add_argument("--corrected-artifact", type=pathlib.Path, required=True)
    correction.add_argument("--corrected-receipt", type=pathlib.Path, required=True)
    correction.add_argument("--output", type=pathlib.Path, required=True)
    freeze = sub.add_parser("freeze-plan")
    freeze.add_argument("--spec", type=pathlib.Path, required=True)
    freeze.add_argument("--canary-receipt", type=pathlib.Path, required=True)
    freeze.add_argument("--pin", type=pathlib.Path, required=True)
    freeze.add_argument("--independent-review", type=pathlib.Path, required=True)
    freeze.add_argument("--output", type=pathlib.Path, required=True)
    mint = sub.add_parser("mint-permit")
    mint.add_argument("--plan", type=pathlib.Path, required=True)
    mint.add_argument("--state", type=pathlib.Path, required=True)
    mint.add_argument("--cell-id", required=True)
    mint.add_argument("--output", type=pathlib.Path, required=True)
    consume = sub.add_parser("consume-permit")
    consume.add_argument("--permit", type=pathlib.Path, required=True)
    consume.add_argument("--state", type=pathlib.Path, required=True)
    terminal = sub.add_parser("record-terminal")
    terminal.add_argument("--permit", type=pathlib.Path, required=True)
    terminal.add_argument("--state", type=pathlib.Path, required=True)
    terminal.add_argument("--receipt", type=pathlib.Path, required=True)
    bind = sub.add_parser("bind-verification")
    bind.add_argument("--plan", type=pathlib.Path, required=True)
    bind.add_argument("--state", type=pathlib.Path, required=True)
    bind.add_argument("--candidate-cell-id", required=True)
    bind.add_argument("--terminal-receipt", type=pathlib.Path, required=True)
    bind.add_argument("--verification-receipt", type=pathlib.Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        if args.command == "preflight":
            preflight_runtime(args.pin, args.repo, args.output)
        elif args.command == "verify-proof":
            verify_proof(
                pin_path=args.pin,
                repo=args.repo,
                candidate_result=args.candidate_result,
                candidate_artifact=args.candidate_artifact,
                declaration=args.declaration,
                output=args.output,
            )
        elif args.command == "verify-nonconversion":
            verify_nonconversion(
                kind=args.kind,
                pin_path=args.pin,
                repo=args.repo,
                candidate_result=args.candidate_result,
                evidence=args.evidence,
                output=args.output,
            )
        elif args.command == "record-correction":
            record_reviewer_correction(
                submitted_result=args.submitted_result,
                submitted_receipt=args.submitted_receipt,
                corrected_artifact=args.corrected_artifact,
                corrected_receipt=args.corrected_receipt,
                output=args.output,
            )
        elif args.command == "freeze-plan":
            spec = _load(_regular_file(args.spec, "campaign plan spec"))
            required = {
                "campaign_id",
                "candidate_assignments",
                "config_root",
                "evaluator_assignments",
                "image",
                "source_root",
            }
            if not isinstance(spec, dict) or set(spec) != required:
                raise HardeningError(
                    "campaign_plan_spec", "campaign plan spec keys do not match v1"
                )
            freeze_cell_plan(
                campaign_id=spec["campaign_id"],
                config_root=spec["config_root"],
                image=spec["image"],
                source_root=spec["source_root"],
                candidate_assignments=spec["candidate_assignments"],
                evaluator_assignments=spec["evaluator_assignments"],
                canary_receipt=args.canary_receipt,
                runtime_pin=args.pin,
                independent_review=args.independent_review,
                output=args.output,
            )
        elif args.command == "mint-permit":
            mint_permit(args.plan, args.state, args.cell_id, args.output)
        elif args.command == "consume-permit":
            consume_permit(args.permit, args.state)
        elif args.command == "record-terminal":
            record_terminal(args.permit, args.state, args.receipt)
        elif args.command == "bind-verification":
            bind_source_verification(
                args.plan,
                args.state,
                args.candidate_cell_id,
                args.terminal_receipt,
                args.verification_receipt,
            )
    except HardeningError as error:
        print(f"{error.code}: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
