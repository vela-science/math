from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import runner  # noqa: E402
from next_campaign_v1 import runtime  # noqa: E402

REAL_RUN_BOUNDED = runner.run_bounded
IMAGE = "sha256:" + "a" * 64


def make_repo(parent: pathlib.Path) -> pathlib.Path:
    repo = (parent / "source").resolve()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "test@invalid.local"],
        check=True,
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "remote",
            "add",
            "origin",
            "https://example.invalid/fc.git",
        ],
        check=True,
    )
    (repo / "lean-toolchain").write_text("leanprover/lean4:v4.27.0\n")
    (repo / "lake-manifest.json").write_text("{}\n")
    (repo / "Source.lean").write_text(
        "namespace Source\ntheorem source_ok : True := by trivial\n"
        "theorem source_duplicate : True := by trivial\nend Source\n"
    )
    subprocess.run(["git", "-C", str(repo), "add", "--all"], check=True)
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_AUTHOR_DATE": "2001-01-01T00:00:00Z",
            "GIT_COMMITTER_DATE": "2001-01-01T00:00:00Z",
        }
    )
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-q", "-m", "source"],
        check=True,
        env=environment,
    )
    return repo


def make_pin(root: pathlib.Path, repo: pathlib.Path) -> pathlib.Path:
    snapshot = runner.git_snapshot(repo)
    path = root / "PIN.json"
    runner.write_json(
        path,
        {
            "codex_version": "codex-cli 0.145.0",
            "embedded_source": "/opt/formal-conjectures",
            "image": IMAGE,
            "lake_manifest_sha256": runner.sha256_file(repo / "lake-manifest.json"),
            "lean_toolchain_sha256": runner.sha256_file(repo / "lean-toolchain"),
            "lean_version": "4.27.0",
            "platform": "linux/arm64",
            "schema": "result-runner.next-campaign-runtime.v1",
            "source_archive_sha256": snapshot.archive_sha256,
            "source_commit": snapshot.commit,
            "source_repository": snapshot.repository_id,
            "source_tree": snapshot.tree,
        },
    )
    return path


def target(repo: pathlib.Path, declaration: str = "Source.source_ok") -> dict:
    snapshot = runner.git_snapshot(repo)
    statement = "True"
    return {
        "declaration": declaration,
        "source_archive_sha256": snapshot.archive_sha256,
        "source_commit": snapshot.commit,
        "source_file_sha256": runner.sha256_file(repo / "Source.lean"),
        "source_path": "Source.lean",
        "source_repository": snapshot.repository_id,
        "source_statement": statement,
        "source_statement_sha256": runner.sha256_bytes(statement.encode()),
        "source_tree": snapshot.tree,
        "statement": statement,
        "statement_sha256": runner.sha256_bytes(statement.encode()),
    }


def proof_result(repo: pathlib.Path, artifact: pathlib.Path, status: str) -> dict:
    return {
        "artifact_sha256": runner.sha256_file(artifact),
        "proof_declaration": "Candidate.result",
        "result_kind": "proof",
        "result_status": status,
        "schema": "source-native-candidate-result.v1",
        "target": target(repo),
    }


def completed_command(
    returncode: int = 0,
    stdout: bytes = b"'Candidate.result' does not depend on any axioms\n",
) -> runner.CommandResult:
    return runner.CommandResult(("docker",), returncode, stdout, b"", 0.1, "completed")


class NextCampaignTests(unittest.TestCase):
    def test_preflight_fails_closed_when_lean_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = pathlib.Path(raw).resolve()
            repo = make_repo(root)
            pin = make_pin(root, repo)
            image = runner.DockerImage(IMAGE, IMAGE, "linux", "arm64")

            def run_bounded(argv, **kwargs):
                if argv[0] == "docker":
                    return completed_command(127, b"")
                return REAL_RUN_BOUNDED(argv, **kwargs)

            with (
                mock.patch.object(runtime, "_docker_context"),
                mock.patch.object(runner, "inspect_docker_image", return_value=image),
                mock.patch.object(runner, "run_bounded", side_effect=run_bounded),
                self.assertRaisesRegex(
                    runtime.HardeningError, "runtime preflight failed"
                ),
            ):
                runtime.preflight_runtime(pin, repo, root / "preflight")

    def proof_fixture(
        self,
        root: pathlib.Path,
        repo: pathlib.Path,
        pin: pathlib.Path,
        status="checked_proof",
    ) -> dict:
        artifact = root / "Candidate.lean"
        artifact.write_text("theorem result : True := by trivial\n")
        statement = root / "statement.txt"
        statement.write_text("True")
        result = root / "result.json"
        runner.write_json(result, proof_result(repo, artifact, status))
        return {
            "root": root,
            "repo": repo,
            "pin": pin,
            "artifact": artifact,
            "statement": statement,
            "result": result,
        }

    def verify(
        self, fixture: dict, output: pathlib.Path, command: runner.CommandResult
    ) -> dict:
        def run_bounded(argv, **kwargs):
            if argv[0] != "docker":
                return REAL_RUN_BOUNDED(argv, **kwargs)
            if command.returncode == 0:
                (output / "runtime-output" / "Submitted.olean").write_bytes(b"olean")
            return command

        image = runner.DockerImage(IMAGE, IMAGE, "linux", "arm64")
        with (
            mock.patch.object(runtime, "_docker_context"),
            mock.patch.object(runner, "inspect_docker_image", return_value=image),
            mock.patch.object(runner, "run_bounded", side_effect=run_bounded),
        ):
            return runtime.verify_proof(
                pin_path=fixture["pin"],
                repo=fixture["repo"],
                candidate_result=fixture["result"],
                candidate_artifact=fixture["artifact"],
                target_statement=fixture["statement"],
                declaration="Candidate.result",
                output=output,
            )

    @staticmethod
    def semantic(repo: pathlib.Path) -> dict:
        return runner.semantic_invocation(
            model="gpt-5.6-sol",
            reasoning="high",
            image=runner.DockerImage(IMAGE, IMAGE, "linux", "arm64"),
            source=runner.git_snapshot(repo),
            prompt_sha256="1" * 64,
            schema_sha256="2" * 64,
            runner_sha256=runner.sha256_file(ROOT / "runner.py"),
        )

    def control(
        self, root: pathlib.Path, repo: pathlib.Path, pin: pathlib.Path, evaluator=False
    ) -> dict:
        semantic = self.semantic(repo)
        cells, files = [], {}
        for ordinal, (cell_id, role) in enumerate(
            [("C1", "candidate")] + ([("E1", "evaluator")] if evaluator else []), 1
        ):
            assignment = root / f"{cell_id}-assignment.json"
            run_spec = root / f"{cell_id}-run.json"
            runner.write_json(assignment, {"cell_id": cell_id, "objective": "fixed"})
            runner.write_json(run_spec, {"cell_id": cell_id, "run": 1})
            cells.append(
                {
                    "assignment_root": runner.sha256_file(assignment),
                    "cell_id": cell_id,
                    "ordinal": ordinal,
                    "role": role,
                    "run_root": runner.sha256_file(run_spec),
                    "target_ordinal": 1,
                }
            )
            files[cell_id] = (assignment, run_spec)
        plan = root / "plan.json"
        runner.write_json(
            plan,
            {
                "campaign_id": "FUTURE-FIVE",
                "cells": cells,
                "config_root": semantic["identity_sha256"],
                "image": IMAGE,
                "runtime_pin_sha256": runner.sha256_file(pin),
                "source_root": runtime._source_root(
                    runner.git_snapshot(repo).as_json()
                ),
            },
        )
        state = root / "state.json"
        runner.write_json(
            state,
            {
                "active_permit": None,
                "completed": [],
                "next_ordinal": 1,
                "plan_sha256": runner.sha256_file(plan),
                "status": "operator_hold",
                "verifications": {},
            },
        )
        return {"plan": plan, "state": state, "files": files}

    def execution(
        self,
        root: pathlib.Path,
        permit: dict,
        repo: pathlib.Path,
        source_files: tuple[pathlib.Path, pathlib.Path],
        result: dict | None,
        status="completed",
        exit_code=0,
    ) -> pathlib.Path:
        bundle = root / f"execution-{permit['cell_id']}"
        bundle.mkdir()
        shutil.copyfile(source_files[0], bundle / "assignment.json")
        shutil.copyfile(source_files[1], bundle / "run.json")
        semantic = self.semantic(repo)
        argv = ["docker", "run", "--rm", "-i", IMAGE]
        runner.write_json(
            bundle / "invocation.json",
            {
                "argv": argv,
                "host_argv_sha256": runner.sha256_bytes(runner.canonical_json(argv)),
                "oauth_read_only": True,
                "semantic": semantic,
                "source_read_only": True,
            },
        )
        stdout = b'{"usage":{"cached_input_tokens":0,"input_tokens":3,"output_tokens":2,"reasoning_output_tokens":1}}\n'
        stderr = b""
        (bundle / "codex.stdout").write_bytes(stdout)
        (bundle / "codex.stderr").write_bytes(stderr)
        runner.write_json(
            bundle / "execution.json",
            {
                "elapsed_seconds": 1.0,
                "exit_code": exit_code,
                "status": status,
                "stderr_bytes": 0,
                "stderr_sha256": runner.sha256_bytes(stderr),
                "stdout_bytes": len(stdout),
                "stdout_sha256": runner.sha256_bytes(stdout),
            },
        )
        if status != "completed" or exit_code != 0:
            runner.write_json(
                bundle / "failure-receipt.json",
                {
                    "error": {"code": status, "message": "bounded failure"},
                    "schema": "vela.result-runner.failure.v1",
                    "status": "fail",
                },
            )
            return bundle
        assert result is not None
        result_path = bundle / "result.json"
        runner.write_json(result_path, result)
        result_sha = runner.sha256_file(result_path)
        metrics = runner.parse_codex_metrics(stdout)
        runner.write_json(
            bundle / "credential-scan.json",
            {"findings": [], "scanned_files": 3, "status": "pass"},
        )
        runner.write_json(
            bundle / "receipt.json",
            {
                "docker_image": semantic["image"],
                "elapsed_seconds": 1.0,
                "git_source": {
                    "after": semantic["source"],
                    "before": semantic["source"],
                    "container_cwd": "/repo",
                    "read_only": True,
                },
                "invocation_identity_sha256": semantic["identity_sha256"],
                "metrics": metrics,
                "output": {"bytes": result_path.stat().st_size, "sha256": result_sha},
                "routes": {
                    "graph": {"result_sha256": result_sha},
                    "native": {"result_sha256": result_sha},
                },
                "schema": "vela.result-runner.receipt.v2",
                "status": "pass",
            },
        )
        return bundle

    def nonconversion_fixture(self, root: pathlib.Path, kind: str) -> tuple:
        repo = make_repo(root)
        pin = make_pin(root, repo)
        evidence = root / "evidence.json"
        if kind == "duplicate":
            value = {
                "comparison": "exact_statement_bytes",
                "duplicate": target(repo, "Source.source_duplicate"),
                "kind": kind,
                "schema": "source-native-duplicate-evidence.v1",
                "target": target(repo),
            }
        else:
            value = {
                "conclusion": "Exact retained sources do not establish the target.",
                "kind": kind,
                "reason_code": "negative_control",
                "reviewed_sources": [
                    {
                        "file_sha256": runner.sha256_file(repo / "Source.lean"),
                        "source_path": "Source.lean",
                    }
                ],
                "schema": "source-native-non-result-evidence.v1",
                "target": target(repo),
            }
        runner.write_json(evidence, value)
        result = root / "result.json"
        runner.write_json(
            result,
            {
                "evidence_sha256": runner.sha256_file(evidence),
                "result_kind": kind,
                "result_status": kind,
                "schema": "source-native-candidate-result.v1",
                "target": target(repo),
            },
        )
        return repo, pin, result, evidence

    def canary_fixture(
        self, root: pathlib.Path, repo: pathlib.Path, pin: pathlib.Path
    ) -> dict:
        canary = root / "canary"
        canary.mkdir()
        fixture = self.proof_fixture(root, repo, pin)
        compile_dir = canary / "compile"
        self.verify(fixture, compile_dir, completed_command())
        semantic = self.semantic(repo)
        source_root = runtime._source_root(runner.git_snapshot(repo).as_json())
        assignment = root / "canary-assignment.json"
        run_spec = root / "canary-run.json"
        runner.write_json(assignment, {"cell_id": "CANARY", "objective": "neutral"})
        runner.write_json(run_spec, {"cell_id": "CANARY", "run": 1})
        permit = {
            "assignment_root": runner.sha256_file(assignment),
            "campaign_id": "RESULT-RUNNER-NEUTRAL-CANARY",
            "cell_id": "CANARY",
            "config_root": semantic["identity_sha256"],
            "image": IMAGE,
            "ordinal": 1,
            "plan_sha256": "9" * 64,
            "role": "candidate",
            "run_root": runner.sha256_file(run_spec),
            "single_use": True,
            "source_root": source_root,
            "target_ordinal": 0,
            "type": "result-runner-single-use-permit-v1",
        }
        permit["permit_root"] = runner.sha256_bytes(runner.canonical_json(permit))
        runner.write_json(canary / "permit.json", permit)
        execution = self.execution(
            canary,
            permit,
            repo,
            (assignment, run_spec),
            json.loads(fixture["result"].read_text()),
        )
        execution.rename(canary / "execution")
        preflight = canary / "preflight"
        image = runner.DockerImage(IMAGE, IMAGE, "linux", "arm64")

        def preflight_run(argv, **kwargs):
            if argv[0] == "docker":
                return completed_command()
            return REAL_RUN_BOUNDED(argv, **kwargs)

        with (
            mock.patch.object(runtime, "_docker_context"),
            mock.patch.object(runner, "inspect_docker_image", return_value=image),
            mock.patch.object(runner, "run_bounded", side_effect=preflight_run),
        ):
            runtime.preflight_runtime(pin, repo, preflight)
        teardown = canary / "teardown.json"
        runner.write_json(
            teardown,
            {
                "container_removed": True,
                "credential_retained": False,
                "permit_consumed_once": True,
                "schema": "result-runner.neutral-canary-teardown.v1",
                "status": "pass",
                "temporary_state_removed": True,
            },
        )
        spec = root / "canary-spec.json"
        runner.write_json(spec, {"schema": "result-runner.neutral-canary-spec.v1"})
        plan_binding = {
            "image": IMAGE,
            "runtime_pin_sha256": runner.sha256_file(pin),
            "source_root": source_root,
        }
        verification = runtime._validate_source_verification_directory(
            compile_dir, plan=plan_binding, pin_path=pin, repo=repo
        )
        execution_value = runtime._validate_runner_bundle(canary / "execution", permit)
        preflight_value = runtime._validate_preflight_directory(
            preflight, pin_path=pin, source_root=source_root
        )
        receipt = canary / "receipt.json"
        runner.write_json(
            receipt,
            {
                "campaign_denominator_effect": "excluded",
                "canary_spec_sha256": runner.sha256_file(spec),
                "compile_receipt_sha256": verification["receipt_sha256"],
                "compile_verification_root": verification["verification_root"],
                "config_root": semantic["identity_sha256"],
                "credential_findings": 0,
                "execution_root": execution_value["evidence_root"],
                "image": IMAGE,
                "permit_sha256": runner.sha256_file(canary / "permit.json"),
                "preflight_receipt_sha256": preflight_value["receipt_sha256"],
                "preflight_root": preflight_value["root"],
                "provider_requests": 1,
                "runtime_pin_sha256": runner.sha256_file(pin),
                "runtime_verifier_sha256": runner.sha256_file(
                    pathlib.Path(runtime.__file__)
                ),
                "schema": "result-runner.neutral-canary-receipt.v1",
                "source_root": source_root,
                "status": "pass",
                "teardown_sha256": runner.sha256_file(teardown),
            },
        )
        return {
            "config_root": semantic["identity_sha256"],
            "receipt": receipt,
            "source_root": source_root,
            "spec": spec,
        }

    def test_proof_status_closed_and_semantics_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = pathlib.Path(raw).resolve()
            repo, pin = make_repo(root), None
            pin = make_pin(root, repo)
            fixture = self.proof_fixture(root, repo, pin)
            value = json.loads(fixture["result"].read_text())
            value["result_status"] = "unsupported"
            runner.write_json(fixture["result"], value)
            with mock.patch.object(
                runtime, "_docker_context"
            ) as docker, self.assertRaisesRegex(
                runtime.HardeningError, "unsupported Result status"
            ):
                runtime.verify_proof(
                    pin_path=pin,
                    repo=repo,
                    candidate_result=fixture["result"],
                    candidate_artifact=fixture["artifact"],
                    target_statement=fixture["statement"],
                    declaration="Candidate.result",
                    output=root / "bad",
                )
            docker.assert_not_called()
        for status, expected, ready in (
            ("proof_sketch", "proof_sketch", False),
            ("checked_proof", "checked_proof", True),
        ):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as raw:
                root = pathlib.Path(raw).resolve()
                repo = make_repo(root)
                pin = make_pin(root, repo)
                fixture = self.proof_fixture(root, repo, pin, status)
                receipt = self.verify(
                    fixture, root / "verification", completed_command()
                )
                self.assertEqual(receipt["candidate_status"], status)
                self.assertEqual(receipt["classification"], expected)
                self.assertEqual(receipt["conversion_ready"], ready)

    def test_invalid_placeholder_and_valid_compile_receipts(self) -> None:
        cases = [
            (1, b"", "invalid", False),
            (0, b"depends on axioms: [hidden]\n", "repairable", False),
            (0, completed_command().stdout, "checked_proof", True),
        ]
        for exit_code, stdout, expected, ready in cases:
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as raw:
                root = pathlib.Path(raw).resolve()
                repo = make_repo(root)
                pin = make_pin(root, repo)
                fixture = self.proof_fixture(root, repo, pin)
                if expected == "repairable":
                    fixture["artifact"].write_text(
                        "axiom hidden : True\ntheorem result : True := hidden\n"
                    )
                    runner.write_json(
                        fixture["result"],
                        proof_result(repo, fixture["artifact"], "checked_proof"),
                    )
                receipt = self.verify(
                    fixture, root / "verification", completed_command(exit_code, stdout)
                )
                self.assertEqual(receipt["classification"], expected)
                self.assertEqual(receipt["conversion_ready"], ready)

    def test_closed_nonconversions_and_adjacent_mutations(self) -> None:
        for kind in ("duplicate", "non_result"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as raw:
                root = pathlib.Path(raw).resolve()
                repo, pin, result, evidence = self.nonconversion_fixture(root, kind)
                receipt = runtime.verify_nonconversion(
                    kind=kind,
                    pin_path=pin,
                    repo=repo,
                    candidate_result=result,
                    evidence=evidence,
                    output=root / "ok",
                )
                self.assertTrue(receipt["task_outcome_valid"])
                self.assertFalse(receipt["conversion_ready"])
            with self.subTest(
                kind=kind, mutation="extra"
            ), tempfile.TemporaryDirectory() as raw:
                root = pathlib.Path(raw).resolve()
                repo, pin, result, evidence = self.nonconversion_fixture(root, kind)
                value = json.loads(evidence.read_text())
                value["unexpected"] = True
                runner.write_json(evidence, value)
                result_value = json.loads(result.read_text())
                result_value["evidence_sha256"] = runner.sha256_file(evidence)
                runner.write_json(result, result_value)
                with self.assertRaisesRegex(
                    runtime.HardeningError, "keys do not match"
                ):
                    runtime.verify_nonconversion(
                        kind=kind,
                        pin_path=pin,
                        repo=repo,
                        candidate_result=result,
                        evidence=evidence,
                        output=root / "bad",
                    )
            with self.subTest(
                kind=kind, mutation="source_hash"
            ), tempfile.TemporaryDirectory() as raw:
                root = pathlib.Path(raw).resolve()
                repo, pin, result, evidence = self.nonconversion_fixture(root, kind)
                value = json.loads(evidence.read_text())
                if kind == "duplicate":
                    value["duplicate"]["source_file_sha256"] = "0" * 64
                else:
                    value["reviewed_sources"][0]["file_sha256"] = "0" * 64
                runner.write_json(evidence, value)
                result_value = json.loads(result.read_text())
                result_value["evidence_sha256"] = runner.sha256_file(evidence)
                runner.write_json(result, result_value)
                with self.assertRaisesRegex(runtime.HardeningError, "source"):
                    runtime.verify_nonconversion(
                        kind=kind,
                        pin_path=pin,
                        repo=repo,
                        candidate_result=result,
                        evidence=evidence,
                        output=root / "bad-source",
                    )

    def test_terminal_requires_actual_runner_bundle_and_retains_timeout(self) -> None:
        for status in ("completed", "timeout"):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as raw:
                root = pathlib.Path(raw).resolve()
                repo = make_repo(root)
                pin = make_pin(root, repo)
                control = self.control(root, repo, pin)
                permit = runtime.mint_permit(
                    control["plan"], control["state"], "C1", root / "permit"
                )
                runtime.consume_permit(
                    root / "permit" / "permit.json", control["state"]
                )
                fake = root / "fake"
                fake.mkdir()
                runner.write_json(fake / "receipt.json", {"status": "pass"})
                with self.assertRaises(runner.RunnerError):
                    runtime.record_terminal(
                        root / "permit" / "permit.json",
                        control["state"],
                        fake,
                        root / "terminal",
                    )
                artifact = root / "candidate.lean"
                artifact.write_text("theorem result : True := by trivial\n")
                result = (
                    proof_result(repo, artifact, "proof_sketch")
                    if status == "completed"
                    else None
                )
                bundle = self.execution(
                    root,
                    permit,
                    repo,
                    control["files"]["C1"],
                    result,
                    status=status,
                    exit_code=0 if status == "completed" else -15,
                )
                original_stdout = (bundle / "codex.stdout").read_bytes()
                (bundle / "codex.stdout").write_bytes(original_stdout + b"mutated")
                with self.assertRaisesRegex(runner.RunnerError, "stdout"):
                    runtime.record_terminal(
                        root / "permit" / "permit.json",
                        control["state"],
                        bundle,
                        root / "terminal-mutated",
                    )
                (bundle / "codex.stdout").write_bytes(original_stdout)
                terminal = runtime.record_terminal(
                    root / "permit" / "permit.json",
                    control["state"],
                    bundle,
                    root / "terminal",
                )
                self.assertEqual(terminal["status"], status)
                with self.assertRaisesRegex(runtime.HardeningError, "no further"):
                    runtime.mint_permit(
                        control["plan"], control["state"], "C1", root / "retry"
                    )

    def test_fabricated_verification_cannot_unlock_evaluator(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = pathlib.Path(raw).resolve()
            repo = make_repo(root)
            pin = make_pin(root, repo)
            control = self.control(root, repo, pin, evaluator=True)
            permit = runtime.mint_permit(
                control["plan"], control["state"], "C1", root / "permit"
            )
            runtime.consume_permit(root / "permit" / "permit.json", control["state"])
            fixture = self.proof_fixture(root, repo, pin)
            bundle = self.execution(
                root,
                permit,
                repo,
                control["files"]["C1"],
                json.loads(fixture["result"].read_text()),
            )
            runtime.record_terminal(
                root / "permit" / "permit.json",
                control["state"],
                bundle,
                root / "terminal",
            )
            fake = root / "fake-verification"
            fake.mkdir()
            runner.write_json(
                fake / "receipt.json",
                {
                    "candidate_result_sha256": runner.sha256_file(
                        bundle / "result.json"
                    ),
                    "classification": "checked_proof",
                    "conversion_ready": True,
                    "runtime_pin_sha256": runner.sha256_file(pin),
                    "type": "source-native-proof-verification-v1",
                    "verifier_sha256": runner.sha256_file(
                        pathlib.Path(runtime.__file__)
                    ),
                },
            )
            with self.assertRaises(runner.RunnerError):
                runtime.bind_source_verification(
                    control["plan"],
                    control["state"],
                    "C1",
                    root / "terminal" / "terminal.json",
                    fake,
                    pin,
                    repo,
                )
            with self.assertRaisesRegex(runtime.HardeningError, "verification"):
                runtime.mint_permit(
                    control["plan"], control["state"], "E1", root / "evaluator"
                )

    def test_exact_verification_roots_unlock_one_evaluator(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = pathlib.Path(raw).resolve()
            repo = make_repo(root)
            pin = make_pin(root, repo)
            control = self.control(root, repo, pin, evaluator=True)
            permit = runtime.mint_permit(
                control["plan"], control["state"], "C1", root / "permit"
            )
            runtime.consume_permit(root / "permit" / "permit.json", control["state"])
            fixture = self.proof_fixture(root, repo, pin)
            bundle = self.execution(
                root,
                permit,
                repo,
                control["files"]["C1"],
                json.loads(fixture["result"].read_text()),
            )
            runtime.record_terminal(
                root / "permit" / "permit.json",
                control["state"],
                bundle,
                root / "terminal",
            )
            self.verify(fixture, root / "verification", completed_command())
            runtime.bind_source_verification(
                control["plan"],
                control["state"],
                "C1",
                root / "terminal" / "terminal.json",
                root / "verification",
                pin,
                repo,
            )
            evaluator = runtime.mint_permit(
                control["plan"], control["state"], "E1", root / "evaluator"
            )
            self.assertEqual(
                evaluator["candidate_result_sha256"],
                runner.sha256_file(root / "verification" / "candidate-result.json"),
            )
            self.assertEqual(len(evaluator["source_verification_root"]), 64)

    def test_synthetic_canary_assertions_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = pathlib.Path(raw).resolve()
            repo = make_repo(root)
            pin = make_pin(root, repo)
            spec = root / "canary-spec.json"
            runner.write_json(spec, {"schema": "result-runner.neutral-canary-spec.v1"})
            receipt = root / "canary.json"
            runner.write_json(
                receipt,
                {
                    "campaign_denominator_effect": "excluded",
                    "provider_requests": 1,
                    "runtime_pin_sha256": runner.sha256_file(pin),
                    "status": "pass",
                },
            )
            with self.assertRaisesRegex(runtime.HardeningError, "keys do not match"):
                runtime.validate_canary(
                    receipt,
                    canary_spec=spec,
                    runtime_pin=pin,
                    config_root="1" * 64,
                    image=IMAGE,
                    source_root=runtime._source_root(
                        runner.git_snapshot(repo).as_json()
                    ),
                    source_repo=repo,
                )

    def test_linked_canary_and_review_are_required_for_exact_five_by_five(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = pathlib.Path(raw).resolve()
            repo = make_repo(root)
            pin = make_pin(root, repo)
            canary = self.canary_fixture(root, repo, pin)
            validated = runtime.validate_canary(
                canary["receipt"],
                canary_spec=canary["spec"],
                runtime_pin=pin,
                config_root=canary["config_root"],
                image=IMAGE,
                source_root=canary["source_root"],
                source_repo=repo,
            )
            self.assertEqual(validated["receipt"]["status"], "pass")
            producer_commit, producer_tree = "1" * 40, "2" * 40
            review_dir = root / "review"
            review_dir.mkdir()
            report = review_dir / "REPORT.md"
            report.write_text("Independent PASS.\n")
            expected = {
                "canary_receipt_sha256": runner.sha256_file(canary["receipt"]),
                "config_root": canary["config_root"],
                "image": IMAGE,
                "producer_commit": producer_commit,
                "producer_tree": producer_tree,
                "runtime_pin_sha256": runner.sha256_file(pin),
                "runtime_verifier_sha256": runner.sha256_file(
                    pathlib.Path(runtime.__file__)
                ),
                "schema": "result-runner-independent-runtime-review.v1",
                "source_root": canary["source_root"],
                "status": "pass",
            }
            verdict = review_dir / "verdict.json"
            runner.write_json(verdict, expected | {"verdict": "PASS"})
            review = review_dir / "review.json"
            runner.write_json(
                review,
                expected
                | {
                    "report_sha256": runner.sha256_file(report),
                    "verdict_sha256": runner.sha256_file(verdict),
                },
            )
            assignments = [
                {
                    "assignment_root": f"{index:x}" * 64,
                    "cell_id": f"C{index}",
                    "run_root": f"{index + 5:x}" * 64,
                }
                for index in range(1, 6)
            ]
            evaluators = [
                value
                | {
                    "cell_id": value["cell_id"].replace("C", "E"),
                    "assignment_root": "abcdef"[index - 1] * 64,
                    "run_root": "fedcba"[index - 1] * 64,
                }
                for index, value in enumerate(assignments, 1)
            ]
            plan = runtime.freeze_cell_plan(
                campaign_id="FUTURE-FIVE",
                config_root=canary["config_root"],
                image=IMAGE,
                source_root=canary["source_root"],
                candidate_assignments=assignments,
                evaluator_assignments=evaluators,
                canary_spec=canary["spec"],
                canary_receipt=canary["receipt"],
                runtime_pin=pin,
                independent_review=review,
                producer_commit=producer_commit,
                producer_tree=producer_tree,
                source_repo=repo,
                output=root / "control",
            )
            self.assertEqual(
                (plan["candidate_denominator"], plan["evaluator_denominator"]), (5, 5)
            )
            self.assertEqual(plan["retries"], 0)
            teardown = canary["receipt"].parent / "teardown.json"
            value = json.loads(teardown.read_text())
            value["credential_retained"] = True
            runner.write_json(teardown, value)
            with self.assertRaises(runtime.HardeningError):
                runtime.validate_canary(
                    canary["receipt"],
                    canary_spec=canary["spec"],
                    runtime_pin=pin,
                    config_root=canary["config_root"],
                    image=IMAGE,
                    source_root=canary["source_root"],
                    source_repo=repo,
                )

    def test_review_receipt_binds_report_verdict_and_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = pathlib.Path(raw).resolve()
            report = root / "REPORT.md"
            report.write_text("Independent PASS.\n")
            expected = {
                "canary_receipt_sha256": "3" * 64,
                "config_root": "4" * 64,
                "image": IMAGE,
                "producer_commit": "1" * 40,
                "producer_tree": "2" * 40,
                "runtime_pin_sha256": "5" * 64,
                "runtime_verifier_sha256": "6" * 64,
                "schema": "result-runner-independent-runtime-review.v1",
                "source_root": "7" * 64,
                "status": "pass",
            }
            verdict = root / "verdict.json"
            runner.write_json(verdict, expected | {"verdict": "PASS"})
            review = root / "review.json"
            runner.write_json(
                review,
                expected
                | {
                    "report_sha256": runner.sha256_file(report),
                    "verdict_sha256": runner.sha256_file(verdict),
                },
            )
            arguments = {
                "producer_commit": "1" * 40,
                "producer_tree": "2" * 40,
                "runtime_pin_sha256": "5" * 64,
                "runtime_verifier_sha256": "6" * 64,
                "image": IMAGE,
                "config_root": "4" * 64,
                "source_root": "7" * 64,
                "canary_sha256": "3" * 64,
            }
            self.assertEqual(
                runtime._validate_independent_review(review, **arguments)["status"],
                "pass",
            )
            report.write_text("mutated\n")
            with self.assertRaisesRegex(runtime.HardeningError, "digest mismatch"):
                runtime._validate_independent_review(review, **arguments)

    def test_reviewer_correction_stays_separate(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = pathlib.Path(raw).resolve()
            submitted = root / "result.json"
            submitted.write_text("{}\n")
            submitted_receipt = root / "receipt.json"
            runner.write_json(
                submitted_receipt,
                {"classification": "invalid", "conversion_ready": False},
            )
            corrected = root / "Correction.lean"
            corrected.write_text("theorem result : True := by trivial\n")
            corrected_receipt = root / "corrected.json"
            runner.write_json(
                corrected_receipt,
                {
                    "candidate_artifact_sha256": runner.sha256_file(corrected),
                    "classification": "checked_proof",
                    "conversion_ready": True,
                },
            )
            before = submitted.read_bytes()
            value = runtime.record_reviewer_correction(
                submitted_result=submitted,
                submitted_receipt=submitted_receipt,
                corrected_artifact=corrected,
                corrected_receipt=corrected_receipt,
                output=root / "reviewer",
            )
            self.assertFalse(value["correction_may_upgrade_submitted_candidate"])
            self.assertEqual(submitted.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
