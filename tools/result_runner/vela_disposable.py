"""Disposable, rejection-only Vela recorder used by Result Runner qualification."""

from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
from typing import Any

from runner import RunnerError, run, sha256_file, write_json


NONCLAIMS = (
    "Any scientific claim, mathematical truth, benchmark result, comparative utility, source-owner approval, canonical authority, or Standing.",
    "Organizational, operator, host, provider, model, or source independence.",
)


def _agent_environment(key: pathlib.Path) -> tuple[dict[str, str], str]:
    completed = run(["ssh-agent", "-s"])
    output = completed.stdout.decode()
    values = dict(re.findall(r"(SSH_AUTH_SOCK|SSH_AGENT_PID)=([^;]+);", output))
    if set(values) != {"SSH_AUTH_SOCK", "SSH_AGENT_PID"}:
        raise RunnerError("ssh-agent did not expose its required environment")
    environment = os.environ.copy()
    environment.update(values)
    run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)])
    key.chmod(0o600)
    run(["ssh-add", str(key)], env=environment)
    return environment, values["SSH_AGENT_PID"]


def _receipt(
    prefix: pathlib.Path,
    argv: list[str],
    *,
    cwd: pathlib.Path,
    env: dict[str, str],
) -> dict[str, Any]:
    completed = run(argv, cwd=cwd, env=env, check=False)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    prefix.with_suffix(".stdout").write_bytes(completed.stdout)
    prefix.with_suffix(".stderr").write_bytes(completed.stderr)
    value = {
        "argv": argv,
        "exit_code": completed.returncode,
        "stderr_sha256": sha256_file(prefix.with_suffix(".stderr")),
        "stdout_sha256": sha256_file(prefix.with_suffix(".stdout")),
    }
    write_json(prefix.with_suffix(".json"), value)
    if completed.returncode != 0:
        raise RunnerError(f"Vela command failed: {' '.join(argv[:3])}")
    return json.loads(completed.stdout) if completed.stdout.strip() else {}


def _find_prefixed(value: Any, prefix: str) -> str:
    if isinstance(value, dict):
        for child in value.values():
            found = _find_prefixed(child, prefix)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_prefixed(child, prefix)
            if found:
                return found
    elif isinstance(value, str) and value.startswith(prefix):
        return value
    return ""


def _find_uuid(value: Any) -> str:
    if isinstance(value, dict):
        for key in ("repository_id", "id"):
            candidate = value.get(key)
            if isinstance(candidate, str) and re.fullmatch(r"[0-9a-f-]{36}", candidate):
                return candidate
        for child in value.values():
            found = _find_uuid(child)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_uuid(child)
            if found:
                return found
    return ""


def _entry_root(value: Any, proposal: str) -> str:
    if isinstance(value, dict):
        if proposal in value.values():
            for name in ("entry_root", "root"):
                candidate = value.get(name)
                if isinstance(candidate, str) and candidate.startswith("sha256:"):
                    return candidate
        for child in value.values():
            found = _entry_root(child, proposal)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _entry_root(child, proposal)
            if found:
                return found
    return ""


def record_disposable(
    *,
    result: pathlib.Path,
    destination: pathlib.Path,
    vela_bin: pathlib.Path,
    expected_vela_sha256: str,
    method: pathlib.Path,
) -> dict[str, Any]:
    if destination.exists():
        raise RunnerError("disposable Vela destination already exists")
    if sha256_file(vela_bin) != expected_vela_sha256:
        raise RunnerError("Vela binary digest does not match the required digest")
    destination.mkdir(parents=True)
    repo = destination / "repo"
    receipts = destination / "receipts"
    private = destination / "private"
    key = private / "authority-key"
    private.mkdir()
    environment, agent_pid = _agent_environment(key)
    try:
        repo.mkdir()
        init = _receipt(
            receipts / "init",
            [
                str(vela_bin),
                "init",
                ".",
                "--name",
                "Result Runner disposable qualification",
                "--scope",
                "Retain one non-scientific execution fixture",
                "--json",
            ],
            cwd=repo,
            env=environment,
        )
        run(["git", "-C", str(repo), "config", "user.name", "Vela Result Runner"])
        run(["git", "-C", str(repo), "config", "user.email", "runner@invalid.local"])
        shutil.copyfile(result, repo / "result.json")
        (repo / "methods").mkdir()
        (repo / "evidence").mkdir()
        shutil.copyfile(method, repo / "methods" / "runner.json")
        verification_output = {
            "output_sha256": sha256_file(result),
            "qualification": "pass",
            "scientific_claim": False,
        }
        write_json(repo / "evidence" / "verification-output.json", verification_output)
        run(
            [
                "git",
                "-C",
                str(repo),
                "add",
                "--",
                "result.json",
                "methods/runner.json",
                "evidence/verification-output.json",
            ]
        )
        run(
            [
                "git",
                "-C",
                str(repo),
                "commit",
                "-q",
                "-m",
                "Retain disposable runner qualification bytes",
            ]
        )

        submit = _receipt(
            receipts / "submit",
            [
                str(vela_bin),
                "submit",
                "--repo",
                ".",
                "--claim",
                "Disposable Result Runner qualification completed; no scientific assertion.",
                "--type",
                "theoretical",
                "--replayability",
                "exact",
                "--artifact",
                "result.json:qualification-output",
                "--caveat",
                "Disposable runner qualification only; no scientific truth, utility, canonical authority, or Standing.",
                "--requires-verification",
                "Exact disposable Result Runner output retention",
                "--source-run",
                "VELA-RESULT-RUNNER",
                "--as",
                "agent:result-runner",
                "--json",
            ],
            cwd=repo,
            env=environment,
        )
        proposal = _find_prefixed(submit, "vpr_")
        if not proposal:
            raise RunnerError("Vela submit response omitted the Proposal id")
        verification_argv = [
            str(vela_bin),
            "verification",
            "record",
            ".",
            proposal,
            "--profile",
            "result-runner-qualification",
            "--method",
            "methods/runner.json",
            "--property",
            "Exact disposable Result Runner output retention",
            "--outcome",
            "pass",
        ]
        for nonclaim in NONCLAIMS:
            verification_argv.extend(["--does-not-establish", nonclaim])
        verification_argv.extend(
            [
                "--shared-dependency",
                "Same operator and host as candidate execution; this is an end-to-end path check, not an independence claim.",
                "--output",
                "evidence/verification-output.json",
                "--as",
                "verifier:result-runner-qualification",
                "--json",
            ]
        )
        verification = _receipt(
            receipts / "verification", verification_argv, cwd=repo, env=environment
        )
        inbox = _receipt(
            receipts / "inbox",
            [str(vela_bin), "review", "inbox", ".", "--json"],
            cwd=repo,
            env=environment,
        )
        entry_root = _entry_root(inbox, proposal)
        if not entry_root:
            raise RunnerError("Vela inbox omitted the current entry root")
        decision = _receipt(
            receipts / "decision",
            [
                str(vela_bin),
                "review",
                "reject",
                ".",
                proposal,
                "--if-entry-root",
                entry_root,
                "--reason",
                "Qualification fixture only; rejection prevents scientific or Standing interpretation.",
                "--as",
                "agent:result-runner-qualification-owner",
                "--session-ref",
                "VELA-RESULT-RUNNER",
                "--json",
            ],
            cwd=repo,
            env=environment,
        )
        show = _receipt(
            receipts / "show",
            [str(vela_bin), "review", "show", ".", proposal, "--json"],
            cwd=repo,
            env=environment,
        )
        status = _receipt(
            receipts / "status",
            [str(vela_bin), "status", ".", "--json"],
            cwd=repo,
            env=environment,
        )
        replay = _receipt(
            receipts / "replay",
            [str(vela_bin), "replay", ".", "--json"],
            cwd=repo,
            env=environment,
        )
        return {
            "decision": "reject",
            "decision_event_id": _find_prefixed(decision, "vev_"),
            "proposal_id": proposal,
            "replay": replay,
            "repository_id": _find_uuid(init),
            "scientific_state_changed": False,
            "status": status,
            "verification_id": _find_prefixed(verification, "vvr_"),
            "show": show,
        }
    finally:
        for candidate in (key, key.with_suffix(".pub")):
            candidate.unlink(missing_ok=True)
        run(["ssh-agent", "-k"], env=environment, check=False)
        if key.exists() or key.with_suffix(".pub").exists():
            raise RunnerError("disposable authority key was not deleted")
