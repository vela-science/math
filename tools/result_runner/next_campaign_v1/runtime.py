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
import shutil
import sys
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

RUNNER_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RUNNER_ROOT))
import runner

HEX64 = re.compile(r"[0-9a-f]{64}")
GIT40 = re.compile(r"[0-9a-f]{40}")
DECLARATION = re.compile(r"[A-Za-z_][A-Za-z0-9_'.]*(?:\.[A-Za-z_][A-Za-z0-9_']*)*")
PLACEHOLDER = re.compile(r"(?m)(?:\bsorry\b|\badmit\b|\baxiom\b|\bunsafe\b)")
AXIOM_LIST = re.compile(r"depends on axioms:\s*\[([^]]*)\]")
NO_AXIOMS = re.compile(r"does not depend on any axioms")
ALLOWED_AXIOMS = frozenset({"propext", "Quot.sound", "Classical.choice"})
EXACT_FIVE = 5
PROOF_STATUSES = frozenset({"checked_proof", "proof_sketch"})
NONCONVERSION_STATUSES = frozenset({"duplicate", "non_result"})
CELL_ASSIGNMENT_KEYS = frozenset(
    {"cell_id", "prompt_sha256", "role", "schema", "target_ordinal"}
)
CELL_RUN_KEYS = frozenset(
    {
        "cell_id",
        "image",
        "model",
        "output_schema_sha256",
        "prompt_sha256",
        "reasoning",
        "runner_sha256",
        "schema",
        "source_root",
    }
)
NONRESULT_REASONS = frozenset(
    {
        "conditional_dependency",
        "negative_control",
        "proof_not_found",
        "source_inconclusive",
        "status_conflict",
        "unsupported_assumption",
    }
)


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


def _closed(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise HardeningError("closed_schema", f"{label} keys do not match v1")
    return value


def _source_root(value: dict[str, Any]) -> str:
    return runner.sha256_bytes(runner.canonical_json(value))


def _git_identity(repo: pathlib.Path, label: str) -> tuple[str, str]:
    root = runner.canonical_existing_path(repo, label, directory=True)
    commit = runner.git(root, "rev-parse", "HEAD")
    tree = runner.git(root, "rev-parse", "HEAD^{tree}")
    _hex(commit, f"{label} commit", git=True)
    _hex(tree, f"{label} tree", git=True)
    return commit, tree


def _tracked_blob_matches(
    repo: pathlib.Path, path: pathlib.Path, commit: str, label: str
) -> None:
    root = runner.canonical_existing_path(repo, f"{label} repository", directory=True)
    file_path = _regular_file(path, label)
    try:
        relative = file_path.relative_to(root)
    except ValueError as error:
        raise HardeningError(
            "immutable_evidence", f"{label} is outside repository"
        ) from error
    result = runner.run(
        ["git", "-C", str(root), "show", f"{commit}:{relative.as_posix()}"],
        check=False,
    )
    if result.returncode != 0 or result.stdout != file_path.read_bytes():
        raise HardeningError(
            "immutable_evidence", f"{label} is not the exact committed blob"
        )


def _validate_cell_inputs(
    assignment_path: pathlib.Path,
    run_path: pathlib.Path,
    *,
    permit: dict[str, Any],
    semantic: dict[str, Any],
) -> None:
    assignment = _closed(
        _load(assignment_path), set(CELL_ASSIGNMENT_KEYS), "cell assignment"
    )
    run_spec = _closed(_load(run_path), set(CELL_RUN_KEYS), "cell run specification")
    expected_assignment = {
        "cell_id": permit["cell_id"],
        "prompt_sha256": semantic["prompt_sha256"],
        "role": permit["role"],
        "schema": "result-runner-cell-assignment.v1",
        "target_ordinal": permit["target_ordinal"],
    }
    expected_run = {
        "cell_id": permit["cell_id"],
        "image": permit["image"],
        "model": semantic["model"],
        "output_schema_sha256": semantic["schema_sha256"],
        "prompt_sha256": semantic["prompt_sha256"],
        "reasoning": semantic["reasoning"],
        "runner_sha256": semantic["runner_sha256"],
        "schema": "result-runner-cell-run.v1",
        "source_root": permit["source_root"],
    }
    if assignment != expected_assignment or run_spec != expected_run:
        raise HardeningError(
            "execution_inputs", "assignment/run bytes do not match the invocation"
        )


def _parse_bind_mount(value: Any, destination: str, *, read_only: bool) -> pathlib.Path:
    if not isinstance(value, str):
        raise HardeningError("execution_invocation", "runner mount is not a string")
    suffix = ",readonly" if read_only else ""
    prefix = "type=bind,src="
    marker = f",dst={destination}{suffix}"
    if not value.startswith(prefix) or not value.endswith(marker):
        raise HardeningError(
            "execution_invocation", f"runner mount for {destination} is not exact"
        )
    source = value[len(prefix) : -len(marker)]
    if not source or "," in source:
        raise HardeningError("execution_invocation", "runner mount source is invalid")
    return pathlib.Path(source)


def _validate_maintained_runner_argv(
    argv: Any,
    *,
    semantic: dict[str, Any],
) -> None:
    if not isinstance(argv, list) or any(not isinstance(item, str) for item in argv):
        raise HardeningError("execution_invocation", "runner argv is invalid")
    if len(argv) != 37:
        raise HardeningError("execution_invocation", "runner argv length mismatch")
    repo = runner.canonical_existing_path(
        _parse_bind_mount(argv[5], "/repo", read_only=True),
        "invoked source repository",
        directory=True,
    )
    auth = _regular_file(
        _parse_bind_mount(argv[7], "/root/.codex/auth.json", read_only=True),
        "invoked OAuth file",
    )
    schema = _regular_file(
        _parse_bind_mount(argv[9], "/inputs/output.schema.json", read_only=True),
        "invoked output schema",
    )
    output = runner.canonical_existing_path(
        _parse_bind_mount(argv[11], "/output", read_only=False),
        "invoked output directory",
        directory=True,
    )
    source = runner.git_snapshot(repo)
    if source.as_json() != semantic["source"]:
        raise HardeningError("execution_source", "runner argv source mount mismatch")
    if runner.sha256_file(schema) != semantic["schema_sha256"]:
        raise HardeningError("execution_config", "runner argv schema mismatch")
    expected = runner.docker_codex_command(
        image=semantic["image"]["resolved_id"],
        repo=repo,
        auth=auth,
        schema=schema,
        output=output,
        model=semantic["model"],
        reasoning=semantic["reasoning"],
    )
    if argv != expected:
        raise HardeningError(
            "execution_invocation", "argv is not the maintained runner command"
        )


def _relative_source_file(repo: pathlib.Path, relative: Any) -> pathlib.Path:
    if not isinstance(relative, str) or not relative or relative.startswith("/"):
        raise HardeningError("source_path", "source path must be relative")
    candidate = repo / relative
    resolved = runner.canonical_existing_path(candidate, "source file", file=True)
    try:
        resolved.relative_to(repo)
    except ValueError as error:
        raise HardeningError("source_path", "source path escapes repository") from error
    return resolved


def _validate_target(
    value: Any,
    *,
    pin: RuntimePin,
    repo: pathlib.Path,
    snapshot: runner.GitSnapshot,
) -> dict[str, Any]:
    target = _closed(
        value,
        {
            "declaration",
            "source_archive_sha256",
            "source_commit",
            "source_file_sha256",
            "source_path",
            "source_repository",
            "source_statement",
            "source_statement_sha256",
            "source_tree",
            "statement",
            "statement_sha256",
        },
        "candidate target",
    )
    if not isinstance(target["declaration"], str) or not DECLARATION.fullmatch(
        target["declaration"]
    ):
        raise HardeningError("target_declaration", "target declaration is invalid")
    statement = target["statement"]
    if (
        not isinstance(statement, str)
        or not statement.strip()
        or len(statement) > 16384
    ):
        raise HardeningError("target_statement", "target statement is invalid")
    if target["statement_sha256"] != runner.sha256_bytes(statement.encode()):
        raise HardeningError("target_statement", "target statement digest mismatch")
    source_statement = target["source_statement"]
    if (
        not isinstance(source_statement, str)
        or not source_statement.strip()
        or len(source_statement) > 16384
        or target["source_statement_sha256"]
        != runner.sha256_bytes(source_statement.encode())
    ):
        raise HardeningError("target_statement", "source statement root mismatch")
    expected_source = {
        "source_archive_sha256": pin.source_archive_sha256,
        "source_commit": pin.source_commit,
        "source_repository": pin.source_repository,
        "source_tree": pin.source_tree,
    }
    for name, expected in expected_source.items():
        if target.get(name) != expected:
            raise HardeningError("target_source", f"target mismatches {name}")
    if snapshot.as_json()["archive_sha256"] != pin.source_archive_sha256:
        raise HardeningError("target_source", "live source snapshot mismatch")
    source_file = _relative_source_file(repo, target["source_path"])
    if target["source_file_sha256"] != runner.sha256_file(source_file):
        raise HardeningError("target_source", "target source file digest mismatch")
    source_text = source_file.read_text(errors="strict")
    declaration_tail = target["declaration"].split(".")[-1]
    if (
        declaration_tail not in source_text
        or source_statement.strip() not in source_text
    ):
        raise HardeningError(
            "target_fidelity",
            "exact declaration/statement bytes are absent from source",
        )
    return target


def _occurrence_root(target: dict[str, Any]) -> str:
    occurrence = {
        "declaration": target["declaration"],
        "source_commit": target["source_commit"],
        "source_file_sha256": target["source_file_sha256"],
        "source_path": target["source_path"],
        "source_repository": target["source_repository"],
        "source_statement_sha256": target["source_statement_sha256"],
        "source_tree": target["source_tree"],
        "statement_sha256": target["statement_sha256"],
    }
    return runner.sha256_bytes(runner.canonical_json(occurrence))


def _validate_candidate_result(
    value: Any,
    *,
    pin: RuntimePin,
    repo: pathlib.Path,
    snapshot: runner.GitSnapshot,
    expected_kind: str,
) -> dict[str, Any]:
    if expected_kind == "proof":
        keys = {
            "artifact_sha256",
            "proof_declaration",
            "result_kind",
            "result_status",
            "schema",
            "target",
        }
        allowed = PROOF_STATUSES
    else:
        keys = {
            "evidence_sha256",
            "result_kind",
            "result_status",
            "schema",
            "target",
        }
        allowed = NONCONVERSION_STATUSES
    result = _closed(value, keys, "candidate Result")
    if result["schema"] != "source-native-candidate-result.v1":
        raise HardeningError("candidate_result", "unexpected Result schema")
    if result["result_kind"] != expected_kind:
        raise HardeningError("candidate_result", "Result kind mismatch")
    if result["result_status"] not in allowed:
        raise HardeningError("candidate_status", "unsupported Result status")
    _hex(
        result["artifact_sha256"]
        if expected_kind == "proof"
        else result["evidence_sha256"],
        "candidate payload digest",
    )
    if expected_kind == "proof" and (
        not isinstance(result["proof_declaration"], str)
        or not DECLARATION.fullmatch(result["proof_declaration"])
    ):
        raise HardeningError("proof_declaration", "proof declaration is invalid")
    _validate_target(result["target"], pin=pin, repo=repo, snapshot=snapshot)
    return result


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
    def read(cls, path: pathlib.Path) -> RuntimePin:
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
test \"$(git rev-parse HEAD)\" = {quoted["commit"]}
test \"$(git rev-parse HEAD^{{tree}})\" = {quoted["tree"]}
test \"$(git archive --format=tar HEAD | sha256sum | cut -d' ' -f1)\" = {quoted["archive"]}
test \"$(sha256sum lean-toolchain | cut -d' ' -f1)\" = {quoted["toolchain"]}
test \"$(sha256sum lake-manifest.json | cut -d' ' -f1)\" = {quoted["manifest"]}
test \"$(git -C /source rev-parse HEAD)\" = {quoted["commit"]}
test \"$(git -C /source rev-parse HEAD^{{tree}})\" = {quoted["tree"]}
test \"$(git -C /source archive --format=tar HEAD | sha256sum | cut -d' ' -f1)\" = {quoted["archive"]}
test -z \"$(git -C /source status --porcelain=v1 --untracked-files=all)\"
lake env lean --version | grep -F {quoted["lean"]}
codex --version | grep -F {quoted["codex"]}
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
        "source_root": _source_root(before.as_json()),
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
    if declared_status == "proof_sketch":
        return ("proof_sketch", False)
    if not axiom_audit_complete or placeholders or unsupported_axioms:
        return ("repairable", False)
    return ("checked_proof", True)


def _proof_artifact_root(root: pathlib.Path) -> str:
    files = [
        root / "candidate-result.json",
        root / "stderr",
        root / "stdout",
        root / "submitted-audited.lean",
        root / "submitted.lean",
        root / "target-statement.txt",
    ]
    runtime_output = runner.canonical_existing_path(
        root / "runtime-output", "proof output", directory=True
    )
    files.extend(sorted(path for path in runtime_output.rglob("*") if path.is_file()))
    return _tree_root([_regular_file(path, "proof artifact") for path in files], root)


def _proof_command_for(
    pin: RuntimePin, audited: pathlib.Path, runtime_output: pathlib.Path
) -> list[str]:
    return [
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


def _proof_command(pin: RuntimePin, root: pathlib.Path) -> list[str]:
    return _proof_command_for(
        pin,
        _regular_file(root / "submitted-audited.lean", "audited proof"),
        runner.canonical_existing_path(
            root / "runtime-output", "proof output", directory=True
        ),
    )


def _replay_proof_verification(
    *,
    root: pathlib.Path,
    pin: RuntimePin,
    retained_stdout: bytes,
    retained_stderr: bytes,
    retained_olean: bytes,
) -> None:
    """Re-run the exact network-disabled Lean check before gate consumption."""

    _docker_context()
    image = runner.inspect_docker_image(pin.image)
    if (
        image.as_json()
        != runner.DockerImage(
            requested_digest=pin.image,
            resolved_id=pin.image,
            os="linux",
            architecture="arm64",
        ).as_json()
    ):
        raise HardeningError("verification_replay", "replay image identity mismatch")
    with tempfile.TemporaryDirectory(prefix="result-runner-proof-replay-") as raw:
        output = pathlib.Path(raw).resolve()
        argv = _proof_command_for(
            pin,
            _regular_file(root / "submitted-audited.lean", "audited proof"),
            output,
        )
        completed = runner.run_bounded(
            argv,
            timeout_seconds=300.0,
            stdout_limit=2 << 20,
            stderr_limit=2 << 20,
            monitor=runner.runtime_monitor(
                output,
                max_files=8,
                max_bytes=32 << 20,
                max_result_bytes=32 << 20,
            ),
        )
        replayed = output / "Submitted.olean"
        if (
            completed.status != "completed"
            or completed.returncode != 0
            or completed.stdout != retained_stdout
            or completed.stderr != retained_stderr
            or not replayed.is_file()
            or replayed.is_symlink()
            or replayed.read_bytes() != retained_olean
        ):
            raise HardeningError(
                "verification_replay", "fresh Lean replay does not match retained proof"
            )


def verify_proof(
    *,
    pin_path: pathlib.Path,
    repo: pathlib.Path,
    candidate_result: pathlib.Path,
    candidate_artifact: pathlib.Path,
    target_statement: pathlib.Path,
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
    statement_path = _regular_file(target_statement, "target statement")
    result = _load(result_path)
    repo = runner.canonical_existing_path(repo, "source repository", directory=True)
    before = _expected_source(pin, repo)
    result = _validate_candidate_result(
        result, pin=pin, repo=repo, snapshot=before, expected_kind="proof"
    )
    if result["proof_declaration"] != declaration:
        raise HardeningError("proof_declaration", "Result/declaration mismatch")
    if result["artifact_sha256"] != runner.sha256_file(artifact_path):
        raise HardeningError("candidate_artifact", "Result/artifact digest mismatch")
    statement_bytes = statement_path.read_bytes()
    if result["target"]["statement_sha256"] != runner.sha256_bytes(statement_bytes):
        raise HardeningError("target_statement", "target statement file mismatch")
    try:
        statement = statement_bytes.decode()
    except UnicodeDecodeError as error:
        raise HardeningError(
            "target_statement", "target statement is not UTF-8"
        ) from error
    if statement != result["target"]["statement"]:
        raise HardeningError("target_statement", "target statement bytes mismatch")
    _docker_context()
    image = runner.inspect_docker_image(pin.image)
    destination = _new_directory(output)
    runtime_output = destination / "runtime-output"
    runtime_output.mkdir()
    artifact_bytes = artifact_path.read_bytes()
    shutil.copyfile(result_path, destination / "candidate-result.json")
    shutil.copyfile(artifact_path, destination / "submitted.lean")
    shutil.copyfile(statement_path, destination / "target-statement.txt")
    audited = destination / "submitted-audited.lean"
    audited.write_bytes(
        artifact_bytes
        + (
            f"\nexample : {statement} := by exact {declaration}\n"
            f"#print axioms {declaration}\n"
        ).encode()
    )
    placeholders = sorted(
        set(PLACEHOLDER.findall(artifact_bytes.decode(errors="replace")))
    )
    argv = _proof_command(pin, destination)
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
        "candidate_status": result["result_status"],
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
        "proof_artifact_root": _proof_artifact_root(destination),
        "runtime_pin_sha256": runner.sha256_file(pin_path),
        "source_after": after.as_json(),
        "source_before": before.as_json(),
        "source_root": _source_root(before.as_json()),
        "stderr_sha256": runner.sha256_bytes(completed.stderr),
        "stdout_sha256": runner.sha256_bytes(completed.stdout),
        "submitted_audited_sha256": runner.sha256_file(audited),
        "target_statement_sha256": runner.sha256_file(statement_path),
        "type": "source-native-proof-verification-v1",
        "verifier_sha256": runner.sha256_file(pathlib.Path(__file__)),
    }
    runner.write_json(destination / "receipt.json", receipt)
    return receipt


def _validate_nonconversion_contract(
    *,
    kind: str,
    result: dict[str, Any],
    evidence: Any,
    pin: RuntimePin,
    repo: pathlib.Path,
    snapshot: runner.GitSnapshot,
) -> dict[str, Any]:
    if result["result_status"] != kind:
        raise HardeningError("nonconversion_status", "Result status/kind mismatch")
    if kind == "duplicate":
        value = _closed(
            evidence,
            {
                "comparison",
                "duplicate",
                "duplicate_occurrence_root",
                "kind",
                "occurrences_are_distinct",
                "schema",
                "target",
                "target_occurrence_root",
            },
            "duplicate evidence",
        )
        if (
            value["schema"] != "source-native-duplicate-evidence.v1"
            or value["kind"] != "duplicate"
            or value["comparison"] != "exact_statement_bytes"
            or value["occurrences_are_distinct"] is not True
        ):
            raise HardeningError("duplicate_evidence", "invalid duplicate evidence")
        target = _validate_target(
            value["target"], pin=pin, repo=repo, snapshot=snapshot
        )
        duplicate = _validate_target(
            value["duplicate"], pin=pin, repo=repo, snapshot=snapshot
        )
        if target != result["target"] or target["statement"] != duplicate["statement"]:
            raise HardeningError(
                "duplicate_comparison", "duplicate statement bytes do not match target"
            )
        target_identity = (
            target["source_repository"],
            target["source_commit"],
            target["source_path"],
            target["declaration"],
        )
        duplicate_identity = (
            duplicate["source_repository"],
            duplicate["source_commit"],
            duplicate["source_path"],
            duplicate["declaration"],
        )
        target_root = _occurrence_root(target)
        duplicate_root = _occurrence_root(duplicate)
        if (
            target_identity == duplicate_identity
            or target_root == duplicate_root
            or value["target_occurrence_root"] != target_root
            or value["duplicate_occurrence_root"] != duplicate_root
        ):
            raise HardeningError(
                "duplicate_identity",
                "duplicate must bind a distinct retained source occurrence",
            )
        return value
    value = _closed(
        evidence,
        {"conclusion", "kind", "reason_code", "reviewed_sources", "schema", "target"},
        "non-result evidence",
    )
    if (
        value["schema"] != "source-native-non-result-evidence.v1"
        or value["kind"] != "non_result"
        or value["reason_code"] not in NONRESULT_REASONS
    ):
        raise HardeningError("nonresult_evidence", "invalid non-result evidence")
    if (
        _validate_target(value["target"], pin=pin, repo=repo, snapshot=snapshot)
        != result["target"]
    ):
        raise HardeningError("nonresult_target", "non-result target mismatch")
    conclusion = value["conclusion"]
    if (
        not isinstance(conclusion, str)
        or not conclusion.strip()
        or len(conclusion) > 4096
    ):
        raise HardeningError("nonresult_evidence", "invalid non-result conclusion")
    reviewed = value["reviewed_sources"]
    if not isinstance(reviewed, list) or not reviewed:
        raise HardeningError("nonresult_evidence", "reviewed sources are required")
    observed_paths: list[str] = []
    for item in reviewed:
        item = _closed(item, {"file_sha256", "source_path"}, "reviewed source")
        source_file = _relative_source_file(repo, item["source_path"])
        if item["file_sha256"] != runner.sha256_file(source_file):
            raise HardeningError(
                "nonresult_evidence", "reviewed source digest mismatch"
            )
        observed_paths.append(item["source_path"])
    if observed_paths != sorted(set(observed_paths)):
        raise HardeningError(
            "nonresult_evidence", "reviewed sources must be sorted and unique"
        )
    return value


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
    result = _validate_candidate_result(
        _load(result_path),
        pin=pin,
        repo=repo,
        snapshot=snapshot,
        expected_kind=kind,
    )
    if result["evidence_sha256"] != runner.sha256_file(evidence_path):
        raise HardeningError(
            "nonconversion_evidence", "Result/evidence digest mismatch"
        )
    evidence_value = _validate_nonconversion_contract(
        kind=kind,
        result=result,
        evidence=_load(evidence_path),
        pin=pin,
        repo=repo,
        snapshot=snapshot,
    )
    destination = _new_directory(output)
    shutil.copyfile(result_path, destination / "candidate-result.json")
    shutil.copyfile(evidence_path, destination / "evidence.json")
    receipt = {
        "candidate_result_sha256": runner.sha256_file(result_path),
        "classification": labels[kind],
        "conversion_ready": False,
        "evidence_sha256": runner.sha256_file(evidence_path),
        "evidence_schema": evidence_value["schema"],
        "infrastructure_failure": False,
        "runtime_pin_sha256": runner.sha256_file(pin_path),
        "source": snapshot.as_json(),
        "source_root": _source_root(snapshot.as_json()),
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


def _validate_source_snapshot(value: Any) -> runner.GitSnapshot:
    snapshot = _closed(
        value,
        {"archive_sha256", "clean", "commit", "repository_id", "shallow", "tree"},
        "runner source snapshot",
    )
    if snapshot["clean"] is not True or not isinstance(snapshot["shallow"], bool):
        raise HardeningError("execution_source", "runner source is not clean")
    _hex(snapshot["commit"], "runner source commit", git=True)
    _hex(snapshot["tree"], "runner source tree", git=True)
    _hex(snapshot["archive_sha256"], "runner source archive")
    if not isinstance(snapshot["repository_id"], str) or not snapshot["repository_id"]:
        raise HardeningError("execution_source", "runner source identity is absent")
    return runner.GitSnapshot(**snapshot)


def _validate_execution_result_shape(
    value: Any, role: str, permit: dict[str, Any]
) -> None:
    if role == "candidate":
        if not isinstance(value, dict):
            raise HardeningError(
                "execution_result", "candidate Result is not an object"
            )
        kind = value.get("result_kind")
        if kind == "proof":
            result = _closed(
                value,
                {
                    "artifact_sha256",
                    "proof_declaration",
                    "result_kind",
                    "result_status",
                    "schema",
                    "target",
                },
                "executed candidate Result",
            )
            status = result["result_status"]
            if status not in PROOF_STATUSES:
                raise HardeningError("candidate_status", "unsupported proof status")
        elif kind in NONCONVERSION_STATUSES:
            result = _closed(
                value,
                {
                    "evidence_sha256",
                    "result_kind",
                    "result_status",
                    "schema",
                    "target",
                },
                "executed candidate Result",
            )
            status = result["result_status"]
            if status != kind:
                raise HardeningError(
                    "candidate_status", "non-conversion status mismatch"
                )
        else:
            raise HardeningError("candidate_result", "unsupported Result kind")
        if result["schema"] != "source-native-candidate-result.v1":
            raise HardeningError("execution_result", "candidate Result schema mismatch")
        _hex(
            result.get("artifact_sha256", result.get("evidence_sha256")),
            "executed candidate payload",
        )
        _closed(
            result["target"],
            {
                "declaration",
                "source_archive_sha256",
                "source_commit",
                "source_file_sha256",
                "source_path",
                "source_repository",
                "source_statement",
                "source_statement_sha256",
                "source_tree",
                "statement",
                "statement_sha256",
            },
            "executed candidate target",
        )
    else:
        verdict = _closed(
            value,
            {
                "candidate_result_sha256",
                "reason",
                "schema",
                "source_verification_sha256",
                "target_ordinal",
                "verdict",
            },
            "evaluator verdict",
        )
        if verdict["schema"] != "source-native-evaluator-verdict.v1" or verdict[
            "verdict"
        ] not in {"conversion_ready", "inconclusive", "invalid", "non_conversion"}:
            raise HardeningError("evaluator_result", "invalid evaluator verdict")
        if verdict["target_ordinal"] != permit["target_ordinal"]:
            raise HardeningError("evaluator_result", "evaluator target mismatch")
        if verdict["source_verification_sha256"] != permit.get(
            "source_verification_sha256"
        ):
            raise HardeningError("evaluator_result", "verification binding mismatch")
        if verdict["candidate_result_sha256"] != permit.get("candidate_result_sha256"):
            raise HardeningError(
                "evaluator_result", "candidate Result binding mismatch"
            )
        if not isinstance(verdict["reason"], str) or not verdict["reason"].strip():
            raise HardeningError("evaluator_result", "evaluator reason is required")


def _validate_runner_bundle(
    evidence: pathlib.Path, permit: dict[str, Any]
) -> dict[str, Any]:
    """Validate retained bytes produced by the maintained runner, never assertions."""

    root = runner.canonical_existing_path(evidence, "runner evidence", directory=True)
    common = {
        "assignment.json",
        "codex.stderr",
        "codex.stdout",
        "execution.json",
        "invocation.json",
        "run.json",
    }
    observed = {
        str(path.relative_to(root))
        for path in root.rglob("*")
        if path.is_file() and not path.is_symlink()
    }
    if any(path.is_symlink() for path in root.rglob("*")):
        raise HardeningError("execution_evidence", "runner evidence contains symlink")
    assignment = _regular_file(root / "assignment.json", "assignment")
    run_spec = _regular_file(root / "run.json", "run spec")
    if runner.sha256_file(assignment) != permit["assignment_root"]:
        raise HardeningError("execution_assignment", "assignment root mismatch")
    if runner.sha256_file(run_spec) != permit["run_root"]:
        raise HardeningError("execution_run", "run root mismatch")
    invocation_path = _regular_file(root / "invocation.json", "runner invocation")
    invocation = _closed(
        _load(invocation_path),
        {"argv", "host_argv_sha256", "oauth_read_only", "semantic", "source_read_only"},
        "runner invocation",
    )
    if (
        invocation["oauth_read_only"] is not True
        or invocation["source_read_only"] is not True
    ):
        raise HardeningError("execution_mounts", "runner mounts are not read-only")
    if not isinstance(invocation["argv"], list) or invocation[
        "host_argv_sha256"
    ] != runner.sha256_bytes(runner.canonical_json(invocation["argv"])):
        raise HardeningError("execution_invocation", "runner argv root mismatch")
    semantic = _closed(
        invocation["semantic"],
        {
            "container_cwd",
            "identity_sha256",
            "image",
            "model",
            "oauth_mount",
            "prompt_sha256",
            "reasoning",
            "runner_sha256",
            "schema_sha256",
            "service_tier",
            "source",
            "source_mount",
        },
        "runner semantic invocation",
    )
    image = _closed(
        semantic["image"],
        {"architecture", "os", "requested_digest", "resolved_id"},
        "runner image",
    )
    if (
        image["requested_digest"] != permit["image"]
        or image["resolved_id"] != permit["image"]
    ):
        raise HardeningError("execution_image", "runner image mismatch")
    if semantic["runner_sha256"] != runner.sha256_file(RUNNER_ROOT / "runner.py"):
        raise HardeningError("execution_runner", "runner implementation mismatch")
    source = _validate_source_snapshot(semantic["source"])
    if _source_root(source.as_json()) != permit["source_root"]:
        raise HardeningError("execution_source", "runner source root mismatch")
    expected_semantic = runner.semantic_invocation(
        model=semantic["model"],
        reasoning=semantic["reasoning"],
        image=runner.DockerImage(**image),
        source=source,
        prompt_sha256=semantic["prompt_sha256"],
        schema_sha256=semantic["schema_sha256"],
        runner_sha256=semantic["runner_sha256"],
    )
    if (
        semantic != expected_semantic
        or semantic["identity_sha256"] != permit["config_root"]
    ):
        raise HardeningError("execution_config", "runner configuration root mismatch")
    _validate_cell_inputs(
        assignment,
        run_spec,
        permit=permit,
        semantic=semantic,
    )
    _validate_maintained_runner_argv(invocation["argv"], semantic=semantic)
    execution_path = _regular_file(root / "execution.json", "execution receipt")
    execution = _closed(
        _load(execution_path),
        {
            "elapsed_seconds",
            "exit_code",
            "status",
            "stderr_bytes",
            "stderr_sha256",
            "stdout_bytes",
            "stdout_sha256",
        },
        "execution receipt",
    )
    stdout_path = _regular_file(root / "codex.stdout", "Codex stdout")
    stderr_path = _regular_file(root / "codex.stderr", "Codex stderr")
    for stream, path in (("stdout", stdout_path), ("stderr", stderr_path)):
        if execution[f"{stream}_bytes"] != path.stat().st_size or execution[
            f"{stream}_sha256"
        ] != runner.sha256_file(path):
            raise HardeningError("execution_stream", f"{stream} receipt mismatch")
    if (
        not isinstance(execution["elapsed_seconds"], (int, float))
        or execution["elapsed_seconds"] < 0
        or not isinstance(execution["exit_code"], int)
    ):
        raise HardeningError("execution_receipt", "invalid execution timing/exit")
    completed = execution["status"] == "completed" and execution["exit_code"] == 0
    if not completed:
        expected = common | {"failure-receipt.json"}
        if observed != expected:
            raise HardeningError(
                "execution_evidence", "failure evidence file set mismatch"
            )
        failure = _closed(
            _load(_regular_file(root / "failure-receipt.json", "failure receipt")),
            {"error", "schema", "status"},
            "runner failure receipt",
        )
        error = _closed(failure["error"], {"code", "message"}, "runner failure")
        if (
            failure["schema"] != "vela.result-runner.failure.v1"
            or failure["status"] != "fail"
            or not all(isinstance(error[name], str) and error[name] for name in error)
        ):
            raise HardeningError("execution_failure", "invalid runner failure receipt")
        return {
            "evidence_root": _tree_root(
                [root / name for name in sorted(observed)], root
            ),
            "execution_sha256": runner.sha256_file(execution_path),
            "invocation_sha256": runner.sha256_file(invocation_path),
            "metrics": runner.parse_codex_metrics(stdout_path.read_bytes()),
            "provider_requests": 1,
            "result_sha256": None,
            "runner_receipt_sha256": runner.sha256_file(root / "failure-receipt.json"),
            "status": "timeout"
            if execution["status"] == "timeout"
            else "infrastructure_failure",
        }
    expected = common | {"credential-scan.json", "receipt.json", "result.json"}
    if observed != expected:
        raise HardeningError("execution_evidence", "success evidence file set mismatch")
    result_path = _regular_file(root / "result.json", "runner Result")
    result_value = _load(result_path)
    _validate_execution_result_shape(result_value, permit["role"], permit)
    credential = _closed(
        _load(_regular_file(root / "credential-scan.json", "credential scan")),
        {"findings", "scanned_files", "status"},
        "credential scan",
    )
    if credential != {"findings": [], "scanned_files": 3, "status": "pass"}:
        raise HardeningError("execution_credentials", "credential scan did not pass")
    if runner.credential_findings([stdout_path, stderr_path, result_path]):
        raise HardeningError("execution_credentials", "credential bytes recomputed")
    receipt_path = _regular_file(root / "receipt.json", "runner receipt")
    receipt = _closed(
        _load(receipt_path),
        {
            "docker_image",
            "elapsed_seconds",
            "git_source",
            "invocation_identity_sha256",
            "metrics",
            "output",
            "routes",
            "schema",
            "status",
        },
        "runner receipt",
    )
    if (
        receipt["schema"] != "vela.result-runner.receipt.v2"
        or receipt["status"] != "pass"
    ):
        raise HardeningError("execution_receipt", "runner receipt did not pass")
    if (
        receipt["docker_image"] != image
        or receipt["invocation_identity_sha256"] != semantic["identity_sha256"]
    ):
        raise HardeningError("execution_receipt", "runner receipt identity mismatch")
    git_source = _closed(
        receipt["git_source"],
        {"after", "before", "container_cwd", "read_only"},
        "runner receipt source",
    )
    if (
        git_source["after"] != source.as_json()
        or git_source["before"] != source.as_json()
        or git_source["container_cwd"] != "/repo"
        or git_source["read_only"] is not True
    ):
        raise HardeningError("execution_source", "runner source receipt mismatch")
    result_sha = runner.sha256_file(result_path)
    output = _closed(receipt["output"], {"bytes", "sha256"}, "runner output")
    if output != {"bytes": result_path.stat().st_size, "sha256": result_sha}:
        raise HardeningError("execution_result", "runner output receipt mismatch")
    metrics = runner.parse_codex_metrics(stdout_path.read_bytes())
    if (
        receipt["metrics"] != metrics
        or metrics["input_tokens"] + metrics["output_tokens"] <= 0
    ):
        raise HardeningError("execution_usage", "runner usage receipt mismatch")
    routes = receipt["routes"]
    if not isinstance(routes, dict) or not {"native", "graph"}.issubset(routes):
        raise HardeningError("execution_routes", "required runner routes are absent")
    for route in ("native", "graph"):
        if (
            not isinstance(routes[route], dict)
            or routes[route].get("result_sha256") != result_sha
        ):
            raise HardeningError("execution_routes", f"{route} Result root mismatch")
    return {
        "evidence_root": _tree_root([root / name for name in sorted(observed)], root),
        "execution_sha256": runner.sha256_file(execution_path),
        "invocation_sha256": runner.sha256_file(invocation_path),
        "metrics": metrics,
        "provider_requests": 1,
        "result_sha256": result_sha,
        "runner_receipt_sha256": runner.sha256_file(receipt_path),
        "status": "completed",
    }


def _validate_preflight_directory(
    root: pathlib.Path, *, pin_path: pathlib.Path, source_root: str
) -> dict[str, Any]:
    directory = runner.canonical_existing_path(
        root, "preflight evidence", directory=True
    )
    observed = {
        str(path.relative_to(directory))
        for path in directory.rglob("*")
        if path.is_file()
    }
    if observed != {"receipt.json", "stderr", "stdout"} or any(
        path.is_symlink() for path in directory.rglob("*")
    ):
        raise HardeningError("canary_preflight", "preflight evidence file set mismatch")
    stdout = directory / "stdout"
    stderr = directory / "stderr"
    receipt = _closed(
        _load(directory / "receipt.json"),
        {
            "argv",
            "docker_image",
            "elapsed_seconds",
            "execution_status",
            "exit_code",
            "network",
            "runtime_pin_sha256",
            "source_after",
            "source_before",
            "source_root",
            "status",
            "stderr_sha256",
            "stdout_sha256",
            "type",
            "verifier_sha256",
        },
        "preflight receipt",
    )
    pin = RuntimePin.read(pin_path)
    if (
        receipt["type"] != "next-campaign-runtime-preflight-v1"
        or receipt["status"] != "pass"
        or receipt["execution_status"] != "completed"
        or receipt["exit_code"] != 0
        or receipt["network"] != "none"
        or receipt["runtime_pin_sha256"] != runner.sha256_file(pin_path)
        or receipt["verifier_sha256"] != runner.sha256_file(pathlib.Path(__file__))
        or receipt["source_root"] != source_root
        or receipt["source_before"] != receipt["source_after"]
        or receipt["docker_image"].get("resolved_id") != pin.image
        or receipt["stdout_sha256"] != runner.sha256_file(stdout)
        or receipt["stderr_sha256"] != runner.sha256_file(stderr)
    ):
        raise HardeningError("canary_preflight", "preflight receipt mismatch")
    return {
        "receipt_sha256": runner.sha256_file(directory / "receipt.json"),
        "root": _tree_root([directory / name for name in sorted(observed)], directory),
    }


def _validate_canary_spec(path: pathlib.Path) -> str:
    spec_path = _regular_file(path, "canary spec")
    spec = _closed(
        _load(spec_path),
        {
            "campaign_denominator_effect",
            "candidate_prompt",
            "checks",
            "freeze_binding",
            "inference_authorized",
            "maximum_provider_requests",
            "required_retained_paths",
            "retries",
            "schema",
            "scientific_denominator",
            "scientific_target",
        },
        "neutral canary specification",
    )
    expected_checks = [
        "single-use permit consumed exactly once",
        "ChatGPT OAuth/model access succeeds",
        "pinned image passes network-none exact-source Lean/lake preflight",
        "neutral Lean theorem compiles and produces a complete proof receipt",
        "timeout and usage fields parse",
        "credential scan reports zero retained credential-like bytes",
        "container, temporary output, and permit custody teardown completes",
    ]
    expected_paths = [
        "permit.json",
        "execution/",
        "terminal.json",
        "compile/",
        "preflight/",
        "teardown.json",
        "receipt.json",
    ]
    if (
        spec["schema"] != "result-runner.neutral-canary-spec.v1"
        or spec["candidate_prompt"]
        != "Return the exact neutral structured output and do not make a scientific claim."
        or spec["checks"] != expected_checks
        or not isinstance(spec["freeze_binding"], str)
        or not spec["freeze_binding"].strip()
        or spec["inference_authorized"] is not False
        or spec["maximum_provider_requests"] != 1
        or spec["required_retained_paths"] != expected_paths
        or spec["retries"] != 0
        or spec["scientific_denominator"] is not False
        or spec["scientific_target"] is not None
        or spec["campaign_denominator_effect"] != "excluded"
    ):
        raise HardeningError("canary_spec", "neutral canary specification mismatch")
    return runner.sha256_file(spec_path)


def _validate_candidate_terminal(
    path: pathlib.Path,
    *,
    permit: dict[str, Any],
    execution: dict[str, Any],
) -> dict[str, Any]:
    terminal_path = _regular_file(path, "candidate terminal")
    terminal = _closed(
        _load(terminal_path),
        {
            "assignment_root",
            "campaign_id",
            "cell_id",
            "config_root",
            "execution_evidence_root",
            "execution_receipt_sha256",
            "image",
            "invocation_sha256",
            "metrics",
            "permit_root",
            "provider_requests",
            "result_sha256",
            "role",
            "run_root",
            "runner_receipt_sha256",
            "source_root",
            "status",
            "target_ordinal",
            "terminal",
            "type",
        },
        "candidate terminal",
    )
    expected = {
        "assignment_root": permit["assignment_root"],
        "campaign_id": permit["campaign_id"],
        "cell_id": permit["cell_id"],
        "config_root": permit["config_root"],
        "execution_evidence_root": execution["evidence_root"],
        "execution_receipt_sha256": execution["execution_sha256"],
        "image": permit["image"],
        "invocation_sha256": execution["invocation_sha256"],
        "metrics": execution["metrics"],
        "permit_root": permit["permit_root"],
        "provider_requests": execution["provider_requests"],
        "result_sha256": execution["result_sha256"],
        "role": "candidate",
        "run_root": permit["run_root"],
        "runner_receipt_sha256": execution["runner_receipt_sha256"],
        "source_root": permit["source_root"],
        "status": execution["status"],
        "target_ordinal": permit["target_ordinal"],
        "terminal": True,
        "type": "result-runner-cell-terminal-v1",
    }
    if terminal != expected or terminal["status"] != "completed":
        raise HardeningError("terminal_evidence", "candidate terminal mismatch")
    return {
        "receipt_sha256": runner.sha256_file(terminal_path),
        "protocol_root": runner.sha256_bytes(runner.canonical_json(terminal)),
    }


def record_canary_receipt(
    root: pathlib.Path,
    *,
    canary_spec: pathlib.Path,
    runtime_pin: pathlib.Path,
    config_root: str,
    image: str,
    source_root: str,
    source_repo: pathlib.Path,
    producer_repo: pathlib.Path,
) -> dict[str, Any]:
    """Generate the canary receipt from exact linked runner/control evidence."""

    directory = runner.canonical_existing_path(root, "canary evidence", directory=True)
    receipt_path = directory / "receipt.json"
    if receipt_path.exists() or receipt_path.is_symlink():
        raise HardeningError("canary_receipt", "canary receipt already exists")
    spec_sha = _validate_canary_spec(canary_spec)
    pin_sha = runner.sha256_file(_regular_file(runtime_pin, "runtime pin"))
    runtime_commit, runtime_tree = _git_identity(producer_repo, "producer")
    permit_path = _regular_file(directory / "permit.json", "canary permit")
    permit = _load(permit_path)
    execution = _validate_runner_bundle(directory / "execution", permit)
    terminal = _validate_candidate_terminal(
        directory / "terminal.json", permit=permit, execution=execution
    )
    verification = _validate_source_verification_directory(
        directory / "compile",
        plan={
            "image": image,
            "runtime_pin_sha256": pin_sha,
            "source_root": source_root,
        },
        pin_path=runtime_pin,
        repo=source_repo,
        replay_proof=True,
    )
    if verification["candidate_result_sha256"] != execution["result_sha256"]:
        raise HardeningError("canary_compile", "canary compile does not bind output")
    preflight = _validate_preflight_directory(
        directory / "preflight", pin_path=runtime_pin, source_root=source_root
    )
    teardown_path = _regular_file(directory / "teardown.json", "canary teardown")
    teardown = _closed(
        _load(teardown_path),
        {
            "container_removed",
            "credential_retained",
            "permit_consumed_once",
            "schema",
            "status",
            "temporary_state_removed",
        },
        "canary teardown",
    )
    if teardown != {
        "container_removed": True,
        "credential_retained": False,
        "permit_consumed_once": True,
        "schema": "result-runner.neutral-canary-teardown.v1",
        "status": "pass",
        "temporary_state_removed": True,
    }:
        raise HardeningError("canary_teardown", "neutral canary teardown mismatch")
    protocol = {
        "canary_spec_sha256": spec_sha,
        "compile_receipt_sha256": verification["receipt_sha256"],
        "compile_verification_root": verification["verification_root"],
        "config_root": config_root,
        "execution_root": execution["evidence_root"],
        "image": image,
        "permit_sha256": runner.sha256_file(permit_path),
        "preflight_receipt_sha256": preflight["receipt_sha256"],
        "preflight_root": preflight["root"],
        "runtime_commit": runtime_commit,
        "runtime_pin_sha256": pin_sha,
        "runtime_tree": runtime_tree,
        "runtime_verifier_sha256": runner.sha256_file(pathlib.Path(__file__)),
        "source_root": source_root,
        "teardown_sha256": runner.sha256_file(teardown_path),
        "terminal_protocol_root": terminal["protocol_root"],
        "terminal_receipt_sha256": terminal["receipt_sha256"],
    }
    receipt = {
        "campaign_denominator_effect": "excluded",
        "credential_findings": 0,
        "generator_sha256": runner.sha256_file(pathlib.Path(__file__)),
        "protocol_root": runner.sha256_bytes(runner.canonical_json(protocol)),
        "provider_requests": 1,
        "schema": "result-runner.neutral-canary-receipt.v2",
        "status": "pass",
    } | protocol
    runner.write_json(receipt_path, receipt)
    return receipt


def validate_canary(
    receipt_path: pathlib.Path,
    *,
    canary_spec: pathlib.Path,
    runtime_pin: pathlib.Path,
    config_root: str,
    image: str,
    source_root: str,
    source_repo: pathlib.Path,
    producer_repo: pathlib.Path,
    canary_repo: pathlib.Path,
) -> dict[str, Any]:
    """Open and recompute the neutral canary's complete retained evidence."""

    path = _regular_file(receipt_path, "canary receipt")
    root = path.parent
    value = _closed(
        _load(path),
        {
            "campaign_denominator_effect",
            "canary_spec_sha256",
            "compile_receipt_sha256",
            "compile_verification_root",
            "config_root",
            "credential_findings",
            "execution_root",
            "generator_sha256",
            "image",
            "permit_sha256",
            "preflight_receipt_sha256",
            "preflight_root",
            "protocol_root",
            "provider_requests",
            "runtime_commit",
            "runtime_pin_sha256",
            "runtime_tree",
            "runtime_verifier_sha256",
            "schema",
            "source_root",
            "status",
            "teardown_sha256",
            "terminal_protocol_root",
            "terminal_receipt_sha256",
        },
        "canary receipt",
    )
    pin_sha = runner.sha256_file(_regular_file(runtime_pin, "runtime pin"))
    spec_sha = _validate_canary_spec(canary_spec)
    runtime_commit, runtime_tree = _git_identity(producer_repo, "producer")
    canary_commit, canary_tree = _git_identity(canary_repo, "canary evidence")
    _tracked_blob_matches(canary_repo, path, canary_commit, "canary receipt")
    expected = {
        "campaign_denominator_effect": "excluded",
        "canary_spec_sha256": spec_sha,
        "config_root": config_root,
        "credential_findings": 0,
        "generator_sha256": runner.sha256_file(pathlib.Path(__file__)),
        "image": image,
        "provider_requests": 1,
        "runtime_commit": runtime_commit,
        "runtime_pin_sha256": pin_sha,
        "runtime_tree": runtime_tree,
        "runtime_verifier_sha256": runner.sha256_file(pathlib.Path(__file__)),
        "schema": "result-runner.neutral-canary-receipt.v2",
        "source_root": source_root,
        "status": "pass",
    }
    for name, expected_value in expected.items():
        if value[name] != expected_value:
            raise HardeningError("canary_binding", f"canary mismatches {name}")
    permit_path = _regular_file(root / "permit.json", "canary permit")
    permit = _closed(
        _load(permit_path),
        {
            "assignment_root",
            "campaign_id",
            "cell_id",
            "config_root",
            "image",
            "ordinal",
            "permit_root",
            "plan_sha256",
            "role",
            "run_root",
            "single_use",
            "source_root",
            "target_ordinal",
            "type",
        },
        "neutral canary permit",
    )
    if (
        permit.get("type") != "result-runner-single-use-permit-v1"
        or permit.get("campaign_id") != "RESULT-RUNNER-NEUTRAL-CANARY"
        or permit.get("cell_id") != "CANARY"
        or permit.get("ordinal") != 1
        or permit.get("target_ordinal") != 0
        or permit.get("single_use") is not True
        or permit.get("role") != "candidate"
        or permit.get("config_root") != config_root
        or permit.get("source_root") != source_root
        or permit.get("image") != image
    ):
        raise HardeningError("canary_permit", "neutral canary permit mismatch")
    permit_preimage = dict(permit)
    permit_root = permit_preimage.pop("permit_root", None)
    if permit_root != runner.sha256_bytes(runner.canonical_json(permit_preimage)):
        raise HardeningError("canary_permit", "neutral canary permit root mismatch")
    _hex(permit["plan_sha256"], "canary plan root")
    execution = _validate_runner_bundle(root / "execution", permit)
    if execution["status"] != "completed" or execution["provider_requests"] != 1:
        raise HardeningError("canary_execution", "neutral canary did not complete once")
    terminal = _validate_candidate_terminal(
        root / "terminal.json", permit=permit, execution=execution
    )
    plan_binding = {
        "image": image,
        "runtime_pin_sha256": pin_sha,
        "source_root": source_root,
    }
    verification = _validate_source_verification_directory(
        root / "compile",
        plan=plan_binding,
        pin_path=runtime_pin,
        repo=source_repo,
        replay_proof=True,
    )
    if verification["candidate_result_sha256"] != execution["result_sha256"]:
        raise HardeningError("canary_compile", "canary compile does not bind output")
    preflight = _validate_preflight_directory(
        root / "preflight", pin_path=runtime_pin, source_root=source_root
    )
    teardown_path = _regular_file(root / "teardown.json", "canary teardown")
    teardown = _closed(
        _load(teardown_path),
        {
            "container_removed",
            "credential_retained",
            "permit_consumed_once",
            "schema",
            "status",
            "temporary_state_removed",
        },
        "canary teardown",
    )
    if teardown != {
        "container_removed": True,
        "credential_retained": False,
        "permit_consumed_once": True,
        "schema": "result-runner.neutral-canary-teardown.v1",
        "status": "pass",
        "temporary_state_removed": True,
    }:
        raise HardeningError("canary_teardown", "neutral canary teardown mismatch")
    linked = {
        "compile_receipt_sha256": verification["receipt_sha256"],
        "compile_verification_root": verification["verification_root"],
        "execution_root": execution["evidence_root"],
        "permit_sha256": runner.sha256_file(permit_path),
        "preflight_receipt_sha256": preflight["receipt_sha256"],
        "preflight_root": preflight["root"],
        "teardown_sha256": runner.sha256_file(teardown_path),
        "terminal_protocol_root": terminal["protocol_root"],
        "terminal_receipt_sha256": terminal["receipt_sha256"],
    }
    for name, observed_value in linked.items():
        if value[name] != observed_value:
            raise HardeningError(
                "canary_evidence", f"canary evidence mismatches {name}"
            )
    protocol = {
        "canary_spec_sha256": spec_sha,
        "compile_receipt_sha256": verification["receipt_sha256"],
        "compile_verification_root": verification["verification_root"],
        "config_root": config_root,
        "execution_root": execution["evidence_root"],
        "image": image,
        "permit_sha256": runner.sha256_file(permit_path),
        "preflight_receipt_sha256": preflight["receipt_sha256"],
        "preflight_root": preflight["root"],
        "runtime_commit": runtime_commit,
        "runtime_pin_sha256": pin_sha,
        "runtime_tree": runtime_tree,
        "runtime_verifier_sha256": runner.sha256_file(pathlib.Path(__file__)),
        "source_root": source_root,
        "teardown_sha256": runner.sha256_file(teardown_path),
        "terminal_protocol_root": terminal["protocol_root"],
        "terminal_receipt_sha256": terminal["receipt_sha256"],
    }
    protocol_root = runner.sha256_bytes(runner.canonical_json(protocol))
    if value["protocol_root"] != protocol_root:
        raise HardeningError("canary_evidence", "canary protocol root mismatch")
    return {
        "commit": canary_commit,
        "protocol_root": protocol_root,
        "receipt_sha256": runner.sha256_file(path),
        "receipt": value,
        "tree": canary_tree,
    }


def _review_verdict_expected(
    *,
    producer_commit: str,
    producer_tree: str,
    runtime_pin_sha256: str,
    runtime_verifier_sha256: str,
    image: str,
    config_root: str,
    source_root: str,
    canary_sha256: str,
    canary_commit: str,
    canary_tree: str,
    canary_protocol_root: str,
) -> dict[str, Any]:
    return {
        "canary_commit": canary_commit,
        "canary_protocol_root": canary_protocol_root,
        "canary_receipt_sha256": canary_sha256,
        "canary_tree": canary_tree,
        "config_root": config_root,
        "image": image,
        "producer_commit": producer_commit,
        "producer_tree": producer_tree,
        "runtime_pin_sha256": runtime_pin_sha256,
        "runtime_verifier_sha256": runtime_verifier_sha256,
        "schema": "result-runner-independent-runtime-verdict.v2",
        "scientific_state_changed": False,
        "source_root": source_root,
        "verdict": "PASS",
    }


def record_independent_review_receipt(
    output: pathlib.Path,
    *,
    review_repo: pathlib.Path,
    report: pathlib.Path,
    verdict: pathlib.Path,
    expected_verdict: dict[str, Any],
) -> dict[str, Any]:
    """Generate a review handoff from exact committed report/verdict bytes."""

    output_path = pathlib.Path(output)
    if (
        not output_path.is_absolute()
        or output_path.exists()
        or output_path.is_symlink()
    ):
        raise HardeningError("independent_review", "review receipt output must be new")
    review_commit, review_tree = _git_identity(review_repo, "review")
    report_path = _regular_file(report, "independent review report")
    verdict_path = _regular_file(verdict, "independent review verdict")
    _tracked_blob_matches(review_repo, report_path, review_commit, "review report")
    _tracked_blob_matches(review_repo, verdict_path, review_commit, "review verdict")
    verdict_value = _closed(
        _load(verdict_path), set(expected_verdict), "independent review verdict"
    )
    if verdict_value != expected_verdict:
        raise HardeningError("independent_review", "review verdict bindings mismatch")
    protocol = {
        "report_sha256": runner.sha256_file(report_path),
        "review_commit": review_commit,
        "review_tree": review_tree,
        "verdict_sha256": runner.sha256_file(verdict_path),
    } | expected_verdict
    receipt = {
        "generator_sha256": runner.sha256_file(pathlib.Path(__file__)),
        "report_sha256": protocol["report_sha256"],
        "review_commit": review_commit,
        "review_protocol_root": runner.sha256_bytes(runner.canonical_json(protocol)),
        "review_tree": review_tree,
        "schema": "result-runner-independent-runtime-review.v2",
        "status": "pass",
        "verdict_sha256": protocol["verdict_sha256"],
    } | {
        name: expected_verdict[name]
        for name in expected_verdict
        if name not in {"schema", "verdict"}
    }
    output_path.parent.mkdir(parents=False, exist_ok=True)
    runner.write_json(output_path, receipt)
    return receipt


def _validate_independent_review(
    path: pathlib.Path,
    *,
    producer_commit: str,
    producer_tree: str,
    runtime_pin_sha256: str,
    runtime_verifier_sha256: str,
    image: str,
    config_root: str,
    source_root: str,
    canary_sha256: str,
    canary_commit: str,
    canary_tree: str,
    canary_protocol_root: str,
    review_repo: pathlib.Path,
) -> dict[str, Any]:
    review_path = _regular_file(path, "independent review receipt")
    review_commit, review_tree = _git_identity(review_repo, "review")
    root = review_path.parent
    expected_verdict = _review_verdict_expected(
        producer_commit=producer_commit,
        producer_tree=producer_tree,
        runtime_pin_sha256=runtime_pin_sha256,
        runtime_verifier_sha256=runtime_verifier_sha256,
        image=image,
        config_root=config_root,
        source_root=source_root,
        canary_sha256=canary_sha256,
        canary_commit=canary_commit,
        canary_tree=canary_tree,
        canary_protocol_root=canary_protocol_root,
    )
    review = _closed(
        _load(review_path),
        (set(expected_verdict) - {"schema", "verdict"})
        | {
            "generator_sha256",
            "report_sha256",
            "review_commit",
            "review_protocol_root",
            "review_tree",
            "schema",
            "status",
            "verdict_sha256",
        },
        "independent review receipt",
    )
    expected_receipt = {
        name: expected_verdict[name]
        for name in expected_verdict
        if name not in {"schema", "verdict"}
    } | {
        "generator_sha256": runtime_verifier_sha256,
        "review_commit": review_commit,
        "review_tree": review_tree,
        "schema": "result-runner-independent-runtime-review.v2",
        "status": "pass",
    }
    for name, expected_value in expected_receipt.items():
        if review[name] != expected_value:
            raise HardeningError("independent_review", f"review mismatches {name}")
    report = _regular_file(root / "REPORT.md", "independent review report")
    verdict_path = _regular_file(root / "verdict.json", "independent review verdict")
    _tracked_blob_matches(review_repo, report, review_commit, "review report")
    _tracked_blob_matches(review_repo, verdict_path, review_commit, "review verdict")
    if review["report_sha256"] != runner.sha256_file(report) or review[
        "verdict_sha256"
    ] != runner.sha256_file(verdict_path):
        raise HardeningError("independent_review", "review artifact digest mismatch")
    verdict = _closed(
        _load(verdict_path), set(expected_verdict), "independent review verdict"
    )
    if verdict != expected_verdict:
        raise HardeningError("independent_review", "review verdict does not pass")
    protocol = {
        "report_sha256": review["report_sha256"],
        "review_commit": review_commit,
        "review_tree": review_tree,
        "verdict_sha256": review["verdict_sha256"],
    } | expected_verdict
    protocol_root = runner.sha256_bytes(runner.canonical_json(protocol))
    if review["review_protocol_root"] != protocol_root:
        raise HardeningError("independent_review", "review protocol root mismatch")
    return review | {"review_protocol_root": protocol_root}


def freeze_cell_plan(
    *,
    campaign_id: str,
    config_root: str,
    image: str,
    source_root: str,
    candidate_assignments: list[dict[str, Any]],
    evaluator_assignments: list[dict[str, Any]],
    canary_spec: pathlib.Path,
    canary_receipt: pathlib.Path,
    runtime_pin: pathlib.Path,
    independent_review: pathlib.Path,
    producer_commit: str,
    producer_tree: str,
    producer_repo: pathlib.Path,
    canary_repo: pathlib.Path,
    review_repo: pathlib.Path,
    source_repo: pathlib.Path,
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
    _hex(producer_commit, "producer commit", git=True)
    _hex(producer_tree, "producer tree", git=True)
    if _git_identity(producer_repo, "producer") != (producer_commit, producer_tree):
        raise HardeningError(
            "producer_binding", "producer commit/tree are not the live immutable bytes"
        )
    runtime_verifier_sha = runner.sha256_file(pathlib.Path(__file__))
    canary = validate_canary(
        canary_receipt,
        canary_spec=canary_spec,
        runtime_pin=runtime_pin,
        config_root=config_root,
        image=image,
        source_root=source_root,
        source_repo=source_repo,
        producer_repo=producer_repo,
        canary_repo=canary_repo,
    )
    review = _validate_independent_review(
        independent_review,
        producer_commit=producer_commit,
        producer_tree=producer_tree,
        runtime_pin_sha256=runtime_pin_sha,
        runtime_verifier_sha256=runtime_verifier_sha,
        image=image,
        config_root=config_root,
        source_root=source_root,
        canary_sha256=canary["receipt_sha256"],
        canary_commit=canary["commit"],
        canary_tree=canary["tree"],
        canary_protocol_root=canary["protocol_root"],
        review_repo=review_repo,
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
        "canary_commit": canary["commit"],
        "canary_protocol_root": canary["protocol_root"],
        "canary_tree": canary["tree"],
        "cells": cells,
        "config_root": config_root,
        "evaluator_denominator": EXACT_FIVE,
        "image": image,
        "independent_review_sha256": runner.sha256_file(independent_review),
        "neutral_canary_sha256": runner.sha256_file(canary_receipt),
        "producer_commit": producer_commit,
        "producer_tree": producer_tree,
        "review_commit": review["review_commit"],
        "review_protocol_root": review["review_protocol_root"],
        "review_tree": review["review_tree"],
        "retries": 0,
        "runtime_pin_sha256": runtime_pin_sha,
        "source_root": source_root,
        "type": "result-runner-fixed-cell-plan-v1",
        "verifier_sha256": runtime_verifier_sha,
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
        source_verification_root = verifications[target].get("verification_root")
        proof_artifact_root = verifications[target].get("proof_artifact_root")
        candidate_result_sha256 = verifications[target].get("candidate_result_sha256")
        _hex(source_verification_sha256, "source verification receipt")
        _hex(source_verification_root, "source verification root")
        _hex(candidate_result_sha256, "candidate Result")
        if proof_artifact_root is not None:
            _hex(proof_artifact_root, "proof artifact root")
    else:
        source_verification_sha256 = None
        source_verification_root = None
        proof_artifact_root = None
        candidate_result_sha256 = None
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
        permit["source_verification_root"] = source_verification_root
        permit["candidate_result_sha256"] = candidate_result_sha256
        if proof_artifact_root is not None:
            permit["proof_artifact_root"] = proof_artifact_root
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
    execution_evidence: pathlib.Path,
    output: pathlib.Path,
) -> dict[str, Any]:
    """Generate one terminal receipt from exact maintained-runner evidence."""

    permit = _load(_regular_file(permit_path, "permit"))
    state = _load(_regular_file(state_path, "permit state"))
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
    execution = _validate_runner_bundle(execution_evidence, permit)
    destination = _new_directory(output)
    receipt = {
        "assignment_root": permit["assignment_root"],
        "campaign_id": permit["campaign_id"],
        "cell_id": permit["cell_id"],
        "config_root": permit["config_root"],
        "execution_evidence_root": execution["evidence_root"],
        "execution_receipt_sha256": execution["execution_sha256"],
        "image": permit["image"],
        "invocation_sha256": execution["invocation_sha256"],
        "metrics": execution["metrics"],
        "permit_root": permit["permit_root"],
        "provider_requests": execution["provider_requests"],
        "result_sha256": execution["result_sha256"],
        "role": permit["role"],
        "run_root": permit["run_root"],
        "runner_receipt_sha256": execution["runner_receipt_sha256"],
        "source_root": permit["source_root"],
        "status": execution["status"],
        "target_ordinal": permit["target_ordinal"],
        "terminal": True,
        "type": "result-runner-cell-terminal-v1",
    }
    if permit["role"] == "evaluator":
        receipt["candidate_result_sha256"] = permit["candidate_result_sha256"]
        receipt["source_verification_sha256"] = permit["source_verification_sha256"]
        receipt["source_verification_root"] = permit["source_verification_root"]
        if "proof_artifact_root" in permit:
            receipt["proof_artifact_root"] = permit["proof_artifact_root"]
    terminal_path = destination / "terminal.json"
    runner.write_json(terminal_path, receipt)
    completed = state.get("completed")
    if not isinstance(completed, list):
        raise HardeningError("permit_state", "completed ledger is invalid")
    completed.append(
        {
            "cell_id": permit["cell_id"],
            "execution_evidence_root": execution["evidence_root"],
            "permit_root": permit["permit_root"],
            "receipt_sha256": runner.sha256_file(terminal_path),
            "role": permit["role"],
            "status": execution["status"],
            "target_ordinal": permit.get("target_ordinal"),
        }
    )
    state["active_permit"] = None
    state["next_ordinal"] = permit["ordinal"] + 1
    state["status"] = "operator_hold"
    _write_state(state_path, state)
    return receipt


def _validate_source_verification_directory(
    verification_directory: pathlib.Path,
    *,
    plan: dict[str, Any],
    pin_path: pathlib.Path,
    repo: pathlib.Path,
    replay_proof: bool = False,
) -> dict[str, Any]:
    root = runner.canonical_existing_path(
        verification_directory, "source verification", directory=True
    )
    if any(path.is_symlink() for path in root.rglob("*")):
        raise HardeningError("verification_evidence", "verification contains symlink")
    receipt_path = _regular_file(root / "receipt.json", "verification receipt")
    receipt = _load(receipt_path)
    pin = RuntimePin.read(pin_path)
    if (
        runner.sha256_file(pin_path) != plan["runtime_pin_sha256"]
        or pin.image != plan["image"]
    ):
        raise HardeningError("verification_runtime", "verification runtime mismatch")
    repo = runner.canonical_existing_path(repo, "source repository", directory=True)
    snapshot = _expected_source(pin, repo)
    if _source_root(snapshot.as_json()) != plan["source_root"]:
        raise HardeningError("verification_source", "verification source root mismatch")
    common = {
        "candidate_result_sha256",
        "classification",
        "conversion_ready",
        "runtime_pin_sha256",
        "type",
        "verifier_sha256",
    }
    if not isinstance(receipt, dict) or not common.issubset(receipt):
        raise HardeningError(
            "verification_schema", "verification receipt is incomplete"
        )
    if receipt["runtime_pin_sha256"] != runner.sha256_file(pin_path) or receipt[
        "verifier_sha256"
    ] != runner.sha256_file(pathlib.Path(__file__)):
        raise HardeningError(
            "verification_runtime", "verification implementation mismatch"
        )
    result_path = _regular_file(root / "candidate-result.json", "verified Result")
    if receipt["candidate_result_sha256"] != runner.sha256_file(result_path):
        raise HardeningError("verification_result", "verified Result digest mismatch")
    if receipt["type"] == "source-native-proof-verification-v1":
        expected_keys = {
            "axiom_audit",
            "candidate_artifact_sha256",
            "candidate_result_sha256",
            "candidate_status",
            "classification",
            "clean_worktree_after",
            "clean_worktree_before",
            "command",
            "compiled",
            "conversion_ready",
            "declaration",
            "docker_image",
            "elapsed_seconds",
            "execution_status",
            "exit_code",
            "generated_artifact_root",
            "generated_files",
            "network",
            "placeholder_audit",
            "proof_artifact_root",
            "runtime_pin_sha256",
            "source_after",
            "source_before",
            "source_root",
            "stderr_sha256",
            "stdout_sha256",
            "submitted_audited_sha256",
            "target_statement_sha256",
            "type",
            "verifier_sha256",
        }
        _closed(receipt, expected_keys, "proof verification receipt")
        result = _validate_candidate_result(
            _load(result_path),
            pin=pin,
            repo=repo,
            snapshot=snapshot,
            expected_kind="proof",
        )
        submitted = _regular_file(root / "submitted.lean", "submitted proof")
        statement = _regular_file(root / "target-statement.txt", "target statement")
        audited = _regular_file(root / "submitted-audited.lean", "audited proof")
        stdout = _regular_file(root / "stdout", "verification stdout")
        stderr = _regular_file(root / "stderr", "verification stderr")
        if result["artifact_sha256"] != runner.sha256_file(submitted) or receipt[
            "candidate_artifact_sha256"
        ] != runner.sha256_file(submitted):
            raise HardeningError("verification_artifact", "submitted proof mismatch")
        if result["proof_declaration"] != receipt["declaration"]:
            raise HardeningError(
                "verification_declaration", "proof declaration mismatch"
            )
        if receipt["target_statement_sha256"] != runner.sha256_file(
            statement
        ) or result["target"]["statement_sha256"] != runner.sha256_file(statement):
            raise HardeningError("verification_statement", "target statement mismatch")
        expected_audited = (
            submitted.read_bytes()
            + (
                f"\nexample : {statement.read_text()} := by exact {receipt['declaration']}\n"
                f"#print axioms {receipt['declaration']}\n"
            ).encode()
        )
        if audited.read_bytes() != expected_audited or receipt[
            "submitted_audited_sha256"
        ] != runner.sha256_file(audited):
            raise HardeningError("verification_artifact", "audited proof mismatch")
        if receipt["stdout_sha256"] != runner.sha256_file(stdout) or receipt[
            "stderr_sha256"
        ] != runner.sha256_file(stderr):
            raise HardeningError("verification_stream", "verification stream mismatch")
        runtime_output = runner.canonical_existing_path(
            root / "runtime-output", "verification output", directory=True
        )
        generated = sorted(path for path in runtime_output.rglob("*") if path.is_file())
        olean_path = runtime_output / "Submitted.olean"
        if generated not in ([], [olean_path]) or (
            generated and olean_path.stat().st_size <= 0
        ):
            raise HardeningError(
                "verification_artifact",
                "proof output must be empty or one nonempty Submitted.olean",
            )
        if receipt["generated_files"] != runner.manifest(generated, runtime_output):
            raise HardeningError("verification_artifact", "generated manifest mismatch")
        if receipt["generated_artifact_root"] != _tree_root(generated, runtime_output):
            raise HardeningError("verification_artifact", "generated root mismatch")
        if receipt["command"] != _proof_command(pin, root):
            raise HardeningError(
                "verification_command",
                "verification did not use the approved Lean command",
            )
        proof_artifact_root = _proof_artifact_root(root)
        if receipt["proof_artifact_root"] != proof_artifact_root:
            raise HardeningError(
                "verification_artifact", "proof artifact root mismatch"
            )
        axioms, complete = _parse_axioms(stdout.read_bytes())
        unsupported = sorted(set(axioms) - ALLOWED_AXIOMS)
        placeholders = sorted(
            set(PLACEHOLDER.findall(submitted.read_text(errors="replace")))
        )
        compiled = (
            receipt["execution_status"] == "completed"
            and receipt["exit_code"] == 0
            and generated == [olean_path]
            and olean_path.stat().st_size > 0
        )
        classification, conversion = _proof_classification(
            declared_status=result["result_status"],
            compiled=compiled,
            axiom_audit_complete=complete,
            placeholders=placeholders,
            unsupported_axioms=unsupported,
        )
        if (
            receipt["candidate_status"] != result["result_status"]
            or receipt["compiled"] != compiled
            or receipt["classification"] != classification
            or receipt["conversion_ready"] != conversion
            or receipt["placeholder_audit"] != placeholders
            or receipt["axiom_audit"]
            != {
                "allowed": sorted(ALLOWED_AXIOMS),
                "complete": complete,
                "observed": list(axioms),
                "unsupported": unsupported,
            }
            or receipt["network"] != "none"
            or receipt["docker_image"]
            != runner.DockerImage(
                requested_digest=plan["image"],
                resolved_id=plan["image"],
                os="linux",
                architecture="arm64",
            ).as_json()
            or receipt["source_before"] != snapshot.as_json()
            or receipt["source_after"] != snapshot.as_json()
            or receipt["source_root"] != plan["source_root"]
        ):
            raise HardeningError("verification_invariant", "proof invariants mismatch")
        if replay_proof and compiled:
            _replay_proof_verification(
                root=root,
                pin=pin,
                retained_stdout=stdout.read_bytes(),
                retained_stderr=stderr.read_bytes(),
                retained_olean=olean_path.read_bytes(),
            )
    elif receipt["type"] == "source-native-nonconversion-verification-v1":
        expected_keys = common | {
            "evidence_schema",
            "evidence_sha256",
            "infrastructure_failure",
            "source",
            "source_root",
            "task_outcome_valid",
        }
        _closed(receipt, expected_keys, "non-conversion verification receipt")
        result_value = _load(result_path)
        kind = (
            result_value.get("result_kind") if isinstance(result_value, dict) else None
        )
        if kind not in NONCONVERSION_STATUSES:
            raise HardeningError("verification_result", "invalid non-conversion kind")
        result = _validate_candidate_result(
            result_value, pin=pin, repo=repo, snapshot=snapshot, expected_kind=kind
        )
        evidence = _regular_file(root / "evidence.json", "non-conversion evidence")
        if result["evidence_sha256"] != runner.sha256_file(evidence) or receipt[
            "evidence_sha256"
        ] != runner.sha256_file(evidence):
            raise HardeningError("verification_evidence", "evidence digest mismatch")
        evidence_value = _validate_nonconversion_contract(
            kind=kind,
            result=result,
            evidence=_load(evidence),
            pin=pin,
            repo=repo,
            snapshot=snapshot,
        )
        expected_classification = {
            "duplicate": "duplicate_non_conversion",
            "non_result": "valid_non_result",
        }[kind]
        if (
            receipt["classification"] != expected_classification
            or receipt["conversion_ready"] is not False
            or receipt["infrastructure_failure"] is not False
            or receipt["task_outcome_valid"] is not True
            or receipt["source"] != snapshot.as_json()
            or receipt["source_root"] != plan["source_root"]
        ):
            raise HardeningError(
                "verification_invariant", "non-conversion invariants mismatch"
            )
        expected_schema = {
            "duplicate": "source-native-duplicate-evidence.v1",
            "non_result": "source-native-non-result-evidence.v1",
        }[kind]
        if (
            receipt["evidence_schema"] != expected_schema
            or evidence_value["schema"] != expected_schema
        ):
            raise HardeningError("verification_evidence", "evidence schema mismatch")
    else:
        raise HardeningError("verification_type", "unsupported verification receipt")
    files = sorted(path for path in root.rglob("*") if path.is_file())
    return {
        "candidate_result_sha256": receipt["candidate_result_sha256"],
        "classification": receipt["classification"],
        "proof_artifact_root": receipt.get("proof_artifact_root"),
        "receipt_sha256": runner.sha256_file(receipt_path),
        "verification_root": _tree_root(files, root),
    }


@_state_locked
def bind_source_verification(
    plan_path: pathlib.Path,
    state_path: pathlib.Path,
    candidate_cell_id: str,
    candidate_permit: pathlib.Path,
    execution_evidence: pathlib.Path,
    terminal_receipt: pathlib.Path,
    verification_directory: pathlib.Path,
    runtime_pin: pathlib.Path,
    repo: pathlib.Path,
) -> dict[str, Any]:
    """Bind a deterministic candidate verification before evaluator launch."""

    plan = _load(_regular_file(plan_path, "cell plan"))
    state = _load(_regular_file(state_path, "permit state"))
    terminal_path = _regular_file(terminal_receipt, "candidate terminal receipt")
    terminal = _load(terminal_path)
    permit_path = _regular_file(candidate_permit, "candidate permit")
    permit = _load(permit_path)
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
    permit_preimage = dict(permit) if isinstance(permit, dict) else {}
    permit_root = permit_preimage.pop("permit_root", None)
    expected_permit = {
        "assignment_root": cell["assignment_root"],
        "campaign_id": plan["campaign_id"],
        "cell_id": candidate_cell_id,
        "config_root": plan["config_root"],
        "image": plan["image"],
        "ordinal": cell["ordinal"],
        "plan_sha256": runner.sha256_file(plan_path),
        "role": "candidate",
        "run_root": cell["run_root"],
        "single_use": True,
        "source_root": plan["source_root"],
        "target_ordinal": cell["target_ordinal"],
        "type": "result-runner-single-use-permit-v1",
    }
    if permit_preimage != expected_permit or permit_root != runner.sha256_bytes(
        runner.canonical_json(permit_preimage)
    ):
        raise HardeningError("verification_permit", "candidate permit is invalid")
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
    terminal = _closed(
        terminal,
        {
            "assignment_root",
            "campaign_id",
            "cell_id",
            "config_root",
            "execution_evidence_root",
            "execution_receipt_sha256",
            "image",
            "invocation_sha256",
            "metrics",
            "permit_root",
            "provider_requests",
            "result_sha256",
            "role",
            "run_root",
            "runner_receipt_sha256",
            "source_root",
            "status",
            "target_ordinal",
            "terminal",
            "type",
        },
        "candidate terminal receipt",
    )
    execution = _validate_runner_bundle(execution_evidence, permit)
    if (
        terminal["type"] != "result-runner-cell-terminal-v1"
        or terminal["terminal"] is not True
        or terminal["status"] != "completed"
        or terminal["role"] != "candidate"
        or terminal["provider_requests"] != 1
        or terminal["permit_root"] != completed["permit_root"]
        or terminal["execution_evidence_root"] != completed["execution_evidence_root"]
        or terminal["assignment_root"] != cell["assignment_root"]
        or terminal["campaign_id"] != plan["campaign_id"]
        or terminal["cell_id"] != candidate_cell_id
        or terminal["config_root"] != plan["config_root"]
        or terminal["image"] != plan["image"]
        or terminal["run_root"] != cell["run_root"]
        or terminal["source_root"] != plan["source_root"]
        or terminal["target_ordinal"] != cell["target_ordinal"]
        or terminal["execution_evidence_root"] != execution["evidence_root"]
        or terminal["execution_receipt_sha256"] != execution["execution_sha256"]
        or terminal["invocation_sha256"] != execution["invocation_sha256"]
        or terminal["metrics"] != execution["metrics"]
        or terminal["result_sha256"] != execution["result_sha256"]
        or terminal["runner_receipt_sha256"] != execution["runner_receipt_sha256"]
    ):
        raise HardeningError("verification_terminal", "candidate terminal is invalid")
    verification = _validate_source_verification_directory(
        verification_directory,
        plan=plan,
        pin_path=runtime_pin,
        repo=repo,
        replay_proof=True,
    )
    if terminal["result_sha256"] != verification["candidate_result_sha256"]:
        raise HardeningError(
            "verification_result", "verification does not bind candidate Result"
        )
    verifications = state.setdefault("verifications", {})
    target = str(cell["target_ordinal"])
    if target in verifications:
        raise HardeningError(
            "verification_reuse", "candidate verification already bound"
        )
    verifications[target] = {
        "candidate_cell_id": candidate_cell_id,
        "candidate_result_sha256": verification["candidate_result_sha256"],
        "classification": verification["classification"],
        "execution_evidence_root": execution["evidence_root"],
        "proof_artifact_root": verification["proof_artifact_root"],
        "receipt_sha256": verification["receipt_sha256"],
        "terminal_receipt_sha256": runner.sha256_file(terminal_path),
        "verification_root": verification["verification_root"],
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
    proof.add_argument("--target-statement", type=pathlib.Path, required=True)
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
    canary_record = sub.add_parser("record-canary")
    canary_record.add_argument("--root", type=pathlib.Path, required=True)
    canary_record.add_argument("--canary-spec", type=pathlib.Path, required=True)
    canary_record.add_argument("--pin", type=pathlib.Path, required=True)
    canary_record.add_argument("--config-root", required=True)
    canary_record.add_argument("--image", required=True)
    canary_record.add_argument("--source-root", required=True)
    canary_record.add_argument("--source-repo", type=pathlib.Path, required=True)
    canary_record.add_argument("--producer-repo", type=pathlib.Path, required=True)
    review_record = sub.add_parser("record-runtime-review")
    review_record.add_argument("--output", type=pathlib.Path, required=True)
    review_record.add_argument("--review-repo", type=pathlib.Path, required=True)
    review_record.add_argument("--report", type=pathlib.Path, required=True)
    review_record.add_argument("--verdict", type=pathlib.Path, required=True)
    review_record.add_argument("--binding", type=pathlib.Path, required=True)
    freeze = sub.add_parser("freeze-plan")
    freeze.add_argument("--spec", type=pathlib.Path, required=True)
    freeze.add_argument("--canary-spec", type=pathlib.Path, required=True)
    freeze.add_argument("--canary-receipt", type=pathlib.Path, required=True)
    freeze.add_argument("--pin", type=pathlib.Path, required=True)
    freeze.add_argument("--source-repo", type=pathlib.Path, required=True)
    freeze.add_argument("--producer-repo", type=pathlib.Path, required=True)
    freeze.add_argument("--canary-repo", type=pathlib.Path, required=True)
    freeze.add_argument("--review-repo", type=pathlib.Path, required=True)
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
    terminal.add_argument("--execution-evidence", type=pathlib.Path, required=True)
    terminal.add_argument("--output", type=pathlib.Path, required=True)
    bind = sub.add_parser("bind-verification")
    bind.add_argument("--plan", type=pathlib.Path, required=True)
    bind.add_argument("--state", type=pathlib.Path, required=True)
    bind.add_argument("--candidate-cell-id", required=True)
    bind.add_argument("--candidate-permit", type=pathlib.Path, required=True)
    bind.add_argument("--execution-evidence", type=pathlib.Path, required=True)
    bind.add_argument("--terminal-receipt", type=pathlib.Path, required=True)
    bind.add_argument("--verification-directory", type=pathlib.Path, required=True)
    bind.add_argument("--pin", type=pathlib.Path, required=True)
    bind.add_argument("--source-repo", type=pathlib.Path, required=True)
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
                target_statement=args.target_statement,
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
        elif args.command == "record-canary":
            record_canary_receipt(
                args.root,
                canary_spec=args.canary_spec,
                runtime_pin=args.pin,
                config_root=args.config_root,
                image=args.image,
                source_root=args.source_root,
                source_repo=args.source_repo,
                producer_repo=args.producer_repo,
            )
        elif args.command == "record-runtime-review":
            record_independent_review_receipt(
                args.output,
                review_repo=args.review_repo,
                report=args.report,
                verdict=args.verdict,
                expected_verdict=_load(_regular_file(args.binding, "review binding")),
            )
        elif args.command == "freeze-plan":
            spec = _load(_regular_file(args.spec, "campaign plan spec"))
            required = {
                "campaign_id",
                "candidate_assignments",
                "config_root",
                "evaluator_assignments",
                "image",
                "producer_commit",
                "producer_tree",
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
                canary_spec=args.canary_spec,
                canary_receipt=args.canary_receipt,
                runtime_pin=args.pin,
                independent_review=args.independent_review,
                producer_commit=spec["producer_commit"],
                producer_tree=spec["producer_tree"],
                producer_repo=args.producer_repo,
                canary_repo=args.canary_repo,
                review_repo=args.review_repo,
                source_repo=args.source_repo,
                output=args.output,
            )
        elif args.command == "mint-permit":
            mint_permit(args.plan, args.state, args.cell_id, args.output)
        elif args.command == "consume-permit":
            consume_permit(args.permit, args.state)
        elif args.command == "record-terminal":
            record_terminal(
                args.permit, args.state, args.execution_evidence, args.output
            )
        elif args.command == "bind-verification":
            bind_source_verification(
                args.plan,
                args.state,
                args.candidate_cell_id,
                args.candidate_permit,
                args.execution_evidence,
                args.terminal_receipt,
                args.verification_directory,
                args.pin,
                args.source_repo,
            )
    except HardeningError as error:
        print(f"{error.code}: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
