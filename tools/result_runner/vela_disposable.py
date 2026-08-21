"""Disposable, rejection-only Vela recorder for Result Runner qualification."""

from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
from typing import Any

from runner import RunnerError, run, sha256_bytes, sha256_file, write_json


PROPERTY = "Qualification establishes scientific truth or independent verification"
NONCLAIMS = (
    "Any scientific claim, mathematical truth, benchmark result, comparative utility, source-owner approval, canonical authority, or Standing.",
    "Organizational, operator, host, provider, model, or source independence.",
)


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise RunnerError("vela_semantics", message)


def _minimal_environment(home: pathlib.Path) -> dict[str, str]:
    home.mkdir()
    return {
        "GIT_CONFIG_NOSYSTEM": "1",
        "HOME": str(home),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PATH": os.environ["PATH"],
        "TZ": "UTC",
    }


def _agent_environment(key: pathlib.Path, home: pathlib.Path) -> dict[str, str]:
    environment = _minimal_environment(home)
    socket = pathlib.Path("/tmp") / (
        "vela-rr-" + sha256_bytes(str(key).encode())[:16] + ".sock"
    )
    socket.unlink(missing_ok=True)
    completed = run(["ssh-agent", "-a", str(socket), "-s"], env=environment)
    values = dict(
        re.findall(
            r"(SSH_AUTH_SOCK|SSH_AGENT_PID)=([^;]+);",
            completed.stdout.decode(),
        )
    )
    if set(values) != {"SSH_AUTH_SOCK", "SSH_AGENT_PID"}:
        raise RunnerError("vela_agent", "ssh-agent omitted its required environment")
    environment.update(values)
    run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)],
        env=environment,
    )
    key.chmod(0o600)
    run(["ssh-add", str(key)], env=environment)
    return environment


def _receipt(
    prefix: pathlib.Path,
    argv: list[str],
    *,
    cwd: pathlib.Path,
    env: dict[str, str],
) -> dict[str, Any]:
    completed = run(
        argv,
        cwd=cwd,
        env=env,
        check=False,
        timeout_seconds=120,
        stdout_limit=2 << 20,
        stderr_limit=2 << 20,
    )
    prefix.parent.mkdir(parents=True, exist_ok=True)
    prefix.with_suffix(".stdout").write_bytes(completed.stdout)
    prefix.with_suffix(".stderr").write_bytes(completed.stderr)
    value = {
        "argv": argv,
        "elapsed_seconds": round(completed.elapsed_seconds, 3),
        "exit_code": completed.returncode,
        "stderr_sha256": sha256_file(prefix.with_suffix(".stderr")),
        "stdout_sha256": sha256_file(prefix.with_suffix(".stdout")),
    }
    write_json(prefix.with_suffix(".json"), value)
    if completed.returncode != 0:
        raise RunnerError("vela_command", f"Vela command failed: {' '.join(argv[1:3])}")
    try:
        parsed = json.loads(completed.stdout) if completed.stdout.strip() else {}
    except json.JSONDecodeError as error:
        raise RunnerError(
            "vela_json", f"Vela command returned invalid JSON: {argv[1]}"
        ) from error
    if not isinstance(parsed, dict):
        raise RunnerError(
            "vela_json", f"Vela command returned non-object JSON: {argv[1]}"
        )
    return parsed


def _prefixed(value: Any, key: str, prefix: str) -> str:
    candidate = value.get(key) if isinstance(value, dict) else None
    if not isinstance(candidate, str) or not candidate.startswith(prefix):
        raise RunnerError("vela_semantics", f"Vela response omitted valid {key}")
    return candidate


def _sha_root(value: Any, key: str) -> str:
    candidate = value.get(key) if isinstance(value, dict) else None
    if not isinstance(candidate, str) or not re.fullmatch(
        r"sha256:[0-9a-f]{64}", candidate
    ):
        raise RunnerError("vela_semantics", f"Vela response omitted valid {key}")
    return candidate


def _find_inbox_entry(value: dict[str, Any], proposal: str) -> dict[str, Any]:
    entries = value.get("entries")
    if not isinstance(entries, list):
        raise RunnerError("vela_semantics", "Vela inbox omitted entries")
    matches = [
        item
        for item in entries
        if isinstance(item, dict) and item.get("proposal_id") == proposal
    ]
    if len(matches) != 1:
        raise RunnerError(
            "vela_semantics",
            "Vela inbox did not contain exactly one current Proposal",
        )
    return matches[0]


def _assert_lifecycle(
    *,
    init: dict[str, Any],
    submit: dict[str, Any],
    verification: dict[str, Any],
    inbox: dict[str, Any],
    decision: dict[str, Any],
    show: dict[str, Any],
    status: dict[str, Any],
    replay: dict[str, Any],
) -> dict[str, Any]:
    _expect(init.get("ok") is True, "Vela init was not ok")
    repository_id = init.get("repository_id")
    _expect(
        isinstance(repository_id, str)
        and re.fullmatch(r"[0-9a-f-]{36}", repository_id) is not None,
        "Vela init omitted repository_id",
    )

    _expect(
        submit.get("schema") == "vela.submit-result.v1" and submit.get("ok") is True,
        "Vela Submission response mismatch",
    )
    _expect(
        submit.get("accepted_state_changed") is False
        and submit.get("accepted_event_delta") == 0,
        "Submission changed accepted state",
    )
    proposal = _prefixed(submit, "proposal_id", "vpr_")
    proposal_root = _sha_root(submit, "proposal_root")
    submission = _prefixed(submit, "submission_id", "vsb_")
    submission_root = _sha_root(submit, "submission_root")
    claim = _prefixed(submit, "claim_id", "vcl_")

    _expect(
        verification.get("schema") == "vela.verification-import-result.v1",
        "Verification schema mismatch",
    )
    _expect(
        verification.get("proposal_id") == proposal
        and verification.get("claim_id") == claim
        and verification.get("outcome") == "fail"
        and verification.get("accepted_event_delta") == 0,
        "Verification was not the truthful failing record",
    )
    verification_id = _prefixed(verification, "verification_record_id", "vvr_")
    verification_root = _sha_root(verification, "verification_record_root")

    _expect(
        inbox.get("schema") == "vela.decision-inbox.v3" and inbox.get("ok") is True,
        "Inbox schema/status mismatch",
    )
    entry = _find_inbox_entry(inbox, proposal)
    entry_root = _sha_root(entry, "entry_root")
    records = entry.get("verification_records")
    _expect(
        isinstance(records, list)
        and len(records) == 1
        and records[0].get("verification_record_id") == verification_id
        and records[0].get("outcome") == "fail",
        "Inbox did not expose the failing Verification",
    )

    _expect(
        decision.get("schema") == "vela.review-decision.v5"
        and decision.get("ok") is True
        and decision.get("action") == "reject"
        and decision.get("proposal_id") == proposal
        and decision.get("proposal_root") == proposal_root
        and decision.get("scientific_state_changed") is False,
        "Rooted reject Decision semantics mismatch",
    )
    event_ids = decision.get("event_ids")
    _expect(
        isinstance(event_ids, list)
        and len(event_ids) == 1
        and isinstance(event_ids[0], str)
        and event_ids[0].startswith("vev_"),
        "Reject Decision omitted its event",
    )

    _expect(
        show.get("schema") == "vela.review.v1"
        and show.get("ok") is True
        and show.get("proposal_id") == proposal
        and show.get("proposal_root") == proposal_root
        and show.get("status") == "rejected",
        "Vela readback did not show rejected Proposal",
    )
    show_decision = show.get("decision")
    _expect(
        isinstance(show_decision, dict)
        and show_decision.get("standing") == "rejected"
        and show_decision.get("event_id") == event_ids[0],
        "Vela readback Decision mismatch",
    )
    decision_event_root = _sha_root(show_decision, "event_root")
    show_records = show.get("verification_records")
    _expect(
        isinstance(show_records, list)
        and len(show_records) == 1
        and show_records[0].get("verification_record_id") == verification_id
        and show_records[0].get("record", {}).get("outcome") == "fail",
        "Vela readback Verification mismatch",
    )

    counts = status.get("counts")
    integrity = status.get("integrity")
    _expect(
        status.get("schema") == "vela.status.v4"
        and status.get("ok") is True
        and isinstance(integrity, dict)
        and integrity.get("replay") == "verified"
        and integrity.get("strict") == "pass"
        and isinstance(counts, dict)
        and counts.get("claims") == 0
        and counts.get("accepted_claims") == 0
        and counts.get("pending_review") == 0
        and counts.get("rejected_review") == 1,
        "Vela strict status/counts mismatch",
    )
    replay_counts = replay.get("counts")
    _expect(
        replay.get("schema") == "vela.repository-verification.v3"
        and replay.get("ok") is True
        and replay.get("repository_id") == repository_id
        and isinstance(replay_counts, dict)
        and replay_counts.get("accepted_claims") == 0
        and replay_counts.get("proposals") == 1
        and replay_counts.get("submissions") == 1
        and replay_counts.get("verifications") == 1,
        "Vela strict replay/counts mismatch",
    )
    repository_root = _sha_root(replay, "repository_root")
    _expect(
        status.get("roots", {}).get("repository") == repository_root
        and show.get("repository_root") == repository_root,
        "Vela repository roots disagree",
    )
    return {
        "accepted_claims": 0,
        "claim_id": claim,
        "decision": "reject",
        "decision_event_id": event_ids[0],
        "decision_event_root": decision_event_root,
        "entry_root": entry_root,
        "proposal_id": proposal,
        "proposal_root": proposal_root,
        "replay_ok": True,
        "repository_id": repository_id,
        "repository_root": repository_root,
        "scientific_state_changed": False,
        "submission_id": submission,
        "submission_root": submission_root,
        "verification_id": verification_id,
        "verification_outcome": "fail",
        "verification_root": verification_root,
    }


def record_disposable(
    *,
    result: pathlib.Path,
    provenance: bytes,
    destination: pathlib.Path,
    vela_bin: pathlib.Path,
    expected_vela_sha256: str,
    method: pathlib.Path,
) -> dict[str, Any]:
    if destination.exists():
        raise RunnerError(
            "vela_destination", "disposable Vela destination already exists"
        )
    binary_digest = sha256_file(vela_bin)
    if binary_digest != expected_vela_sha256:
        raise RunnerError(
            "vela_digest", "Vela binary digest does not match required digest"
        )
    method_digest = sha256_file(method)
    destination.mkdir(parents=True)
    repo = destination / "repo"
    receipts = destination / "receipts"
    private = destination / "private"
    key = private / "authority-key"
    private.mkdir()
    environment = _agent_environment(key, destination / "home")
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
        run(
            [
                "git",
                "-C",
                str(repo),
                "config",
                "user.name",
                "Vela Result Runner",
            ],
            env=environment,
        )
        run(
            [
                "git",
                "-C",
                str(repo),
                "config",
                "user.email",
                "runner@invalid.local",
            ],
            env=environment,
        )
        shutil.copyfile(result, repo / "result.json")
        (repo / "provenance.json").write_bytes(provenance)
        (repo / "methods").mkdir()
        (repo / "evidence").mkdir()
        shutil.copyfile(method, repo / "methods" / "runner.json")
        write_json(
            repo / "evidence" / "verification-output.json",
            {
                "independent_verification": False,
                "output_sha256": sha256_file(result),
                "scientific_claim_established": False,
            },
        )
        run(
            [
                "git",
                "-C",
                str(repo),
                "add",
                "--",
                "result.json",
                "provenance.json",
                "methods/runner.json",
                "evidence/verification-output.json",
            ],
            env=environment,
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
            ],
            env=environment,
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
                "--artifact",
                "provenance.json:qualification-provenance",
                "--caveat",
                "Disposable runner qualification only; no scientific truth, utility, canonical authority, or Standing.",
                "--requires-verification",
                PROPERTY,
                "--source-run",
                "VELA-RESULT-RUNNER",
                "--as",
                "agent:result-runner",
                "--json",
            ],
            cwd=repo,
            env=environment,
        )
        proposal = _prefixed(submit, "proposal_id", "vpr_")
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
            PROPERTY,
            "--outcome",
            "fail",
        ]
        for nonclaim in NONCLAIMS:
            verification_argv.extend(["--does-not-establish", nonclaim])
        verification_argv.extend(
            [
                "--shared-dependency",
                "Same operator and host as candidate execution; no independence claim.",
                "--output",
                "evidence/verification-output.json",
                "--as",
                "verifier:result-runner-qualification",
                "--json",
            ]
        )
        verification = _receipt(
            receipts / "verification",
            verification_argv,
            cwd=repo,
            env=environment,
        )
        inbox = _receipt(
            receipts / "inbox",
            [str(vela_bin), "review", "inbox", ".", "--json"],
            cwd=repo,
            env=environment,
        )
        entry = _find_inbox_entry(inbox, proposal)
        entry_root = _sha_root(entry, "entry_root")
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
        lifecycle = _assert_lifecycle(
            init=init,
            submit=submit,
            verification=verification,
            inbox=inbox,
            decision=decision,
            show=show,
            status=status,
            replay=replay,
        )
        return lifecycle | {
            "method_sha256": method_digest,
            "vela_binary_sha256": binary_digest,
        }
    finally:
        for candidate in (key, key.with_suffix(".pub")):
            candidate.unlink(missing_ok=True)
        run(["ssh-agent", "-k"], env=environment, check=False)
        if key.exists() or key.with_suffix(".pub").exists():
            raise RunnerError(
                "vela_key_delete",
                "disposable authority private/public key was not deleted",
            )
