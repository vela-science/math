from __future__ import annotations

import json
import os
import pathlib
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
    (repo / "Source.lean").write_text("theorem source_ok : True := by trivial\n")
    subprocess.run(["git", "-C", str(repo), "add", "--all"], check=True)
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_DATE": "2001-01-01T00:00:00Z",
            "GIT_COMMITTER_DATE": "2001-01-01T00:00:00Z",
        }
    )
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-q", "-m", "source"], check=True, env=env
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
            "image": "sha256:" + "a" * 64,
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


def command_result(
    returncode: int = 0,
    *,
    stdout: bytes = b"declaration uses 'propext', depends on axioms: [propext, Quot.sound, Classical.choice]\n",
    status: str = "completed",
) -> runner.CommandResult:
    return runner.CommandResult(("docker",), returncode, stdout, b"", 0.1, status)


class NextCampaignTests(unittest.TestCase):
    def _proof_fixture(
        self, raw: str, artifact: str, result_status: str = "checked_proof"
    ) -> dict[str, pathlib.Path]:
        root = pathlib.Path(raw).resolve()
        repo = make_repo(root)
        pin = make_pin(root, repo)
        result = root / "result.json"
        runner.write_json(result, {"result_status": result_status})
        candidate = root / "Candidate.lean"
        candidate.write_text(artifact)
        return {
            "root": root,
            "repo": repo,
            "pin": pin,
            "result": result,
            "candidate": candidate,
        }

    @staticmethod
    def _docker_side_effect(output: pathlib.Path, completed: runner.CommandResult):
        def run_bounded(argv, **kwargs):
            if argv[0] != "docker":
                return REAL_RUN_BOUNDED(argv, **kwargs)
            if completed.returncode == 0:
                runtime_output = output / "runtime-output"
                (runtime_output / "Submitted.olean").write_bytes(b"olean")
            return completed

        return run_bounded

    def _verify(
        self,
        fixture: dict[str, pathlib.Path],
        output: pathlib.Path,
        completed: runner.CommandResult,
    ) -> dict:
        image = runner.DockerImage(
            "sha256:" + "a" * 64, "sha256:" + "a" * 64, "linux", "arm64"
        )
        with (
            mock.patch.object(runtime, "_docker_context"),
            mock.patch.object(runner, "inspect_docker_image", return_value=image),
            mock.patch.object(
                runner,
                "run_bounded",
                side_effect=self._docker_side_effect(output, completed),
            ),
        ):
            return runtime.verify_proof(
                pin_path=fixture["pin"],
                repo=fixture["repo"],
                candidate_result=fixture["result"],
                candidate_artifact=fixture["candidate"],
                declaration="Candidate.result",
                output=output,
            )

    def test_missing_lean_preflight_fails_closed_with_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = pathlib.Path(raw).resolve()
            repo = make_repo(root)
            pin = make_pin(root, repo)
            output = root / "preflight"
            image = runner.DockerImage(
                "sha256:" + "a" * 64, "sha256:" + "a" * 64, "linux", "arm64"
            )

            def missing_lean(argv, **kwargs):
                if argv[0] == "docker":
                    return command_result(127, stdout=b"")
                return REAL_RUN_BOUNDED(argv, **kwargs)

            with (
                mock.patch.object(runtime, "_docker_context"),
                mock.patch.object(runner, "inspect_docker_image", return_value=image),
                mock.patch.object(runner, "run_bounded", side_effect=missing_lean),
                self.assertRaisesRegex(runtime.HardeningError, "preflight failed"),
            ):
                runtime.preflight_runtime(pin, repo, output)
            receipt = json.loads((output / "receipt.json").read_text())
            self.assertEqual(receipt["status"], "infrastructure_failure")
            self.assertEqual(receipt["exit_code"], 127)

    def test_invalid_proof_never_becomes_conversion_ready(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = self._proof_fixture(
                raw, "theorem result : True := by exact False.elim (by contradiction)\n"
            )
            receipt = self._verify(
                fixture, fixture["root"] / "verification", command_result(1, stdout=b"")
            )
            self.assertEqual(receipt["classification"], "invalid")
            self.assertFalse(receipt["compiled"])
            self.assertFalse(receipt["conversion_ready"])

    def test_valid_proof_has_exact_compile_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = self._proof_fixture(raw, "theorem result : True := by trivial\n")
            receipt = self._verify(
                fixture, fixture["root"] / "verification", command_result()
            )
            self.assertEqual(receipt["classification"], "checked_proof")
            self.assertTrue(receipt["compiled"])
            self.assertTrue(receipt["conversion_ready"])
            self.assertEqual(receipt["execution_status"], "completed")
            self.assertEqual(receipt["network"], "none")
            self.assertIn(
                "/opt/formal-conjectures/ResultRunnerSubmitted.lean",
                receipt["command"],
            )
            self.assertTrue(receipt["generated_files"])
            self.assertEqual(len(receipt["generated_artifact_root"]), 64)
            self.assertEqual(receipt["source_before"], receipt["source_after"])

    def test_source_assumption_or_placeholder_is_caveated(self) -> None:
        for artifact, stdout in (
            (
                "axiom hidden : True\ntheorem result : True := hidden\n",
                b"depends on axioms: [hidden]\n",
            ),
            ("theorem result : True := by sorry\n", b"depends on axioms: []\n"),
        ):
            with self.subTest(artifact=artifact), tempfile.TemporaryDirectory() as raw:
                fixture = self._proof_fixture(raw, artifact)
                receipt = self._verify(
                    fixture,
                    fixture["root"] / "verification",
                    command_result(stdout=stdout),
                )
                self.assertEqual(receipt["classification"], "repairable")
                self.assertFalse(receipt["conversion_ready"])

    def test_missing_axiom_audit_output_is_caveated(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = self._proof_fixture(raw, "theorem result : True := by trivial\n")
            receipt = self._verify(
                fixture,
                fixture["root"] / "verification",
                command_result(stdout=b"unexpected evaluator text\n"),
            )
            self.assertFalse(receipt["axiom_audit"]["complete"])
            self.assertEqual(receipt["classification"], "repairable")
            self.assertFalse(receipt["conversion_ready"])

    def test_reviewer_correction_cannot_upgrade_submitted_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = pathlib.Path(raw).resolve()
            submitted = root / "result.json"
            submitted.write_bytes(b'{"result_status":"checked_proof"}\n')
            submitted_receipt = root / "submitted-receipt.json"
            runner.write_json(
                submitted_receipt,
                {"classification": "invalid", "conversion_ready": False},
            )
            correction = root / "Correction.lean"
            correction.write_text("theorem result : True := by trivial\n")
            correction_receipt = root / "correction-receipt.json"
            runner.write_json(
                correction_receipt,
                {
                    "candidate_artifact_sha256": runner.sha256_file(correction),
                    "classification": "checked_proof",
                    "conversion_ready": True,
                },
            )
            before = submitted.read_bytes()
            value = runtime.record_reviewer_correction(
                submitted_result=submitted,
                submitted_receipt=submitted_receipt,
                corrected_artifact=correction,
                corrected_receipt=correction_receipt,
                output=root / "reviewer",
            )
            self.assertEqual(value["submitted_classification"], "invalid")
            self.assertFalse(value["submitted_conversion_ready"])
            self.assertFalse(value["correction_may_upgrade_submitted_candidate"])
            self.assertEqual(submitted.read_bytes(), before)

    def test_duplicate_and_non_result_are_valid_nonconversions(self) -> None:
        for kind, expected in (
            ("duplicate", "duplicate_non_conversion"),
            ("non_result", "valid_non_result"),
        ):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as raw:
                root = pathlib.Path(raw).resolve()
                repo = make_repo(root)
                pin = make_pin(root, repo)
                result = root / "result.json"
                result.write_text("{}\n")
                evidence = root / "evidence.txt"
                evidence.write_text("exact source audit\n")
                receipt = runtime.verify_nonconversion(
                    kind=kind,
                    pin_path=pin,
                    repo=repo,
                    candidate_result=result,
                    evidence=evidence,
                    output=root / "verification",
                )
                self.assertEqual(receipt["classification"], expected)
                self.assertTrue(receipt["task_outcome_valid"])
                self.assertFalse(receipt["infrastructure_failure"])
                self.assertFalse(receipt["conversion_ready"])

    def test_exact_five_by_five_denominator_requires_canary_and_review(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = pathlib.Path(raw).resolve()
            repo = make_repo(root)
            pin = make_pin(root, repo)
            pin_sha = runner.sha256_file(pin)
            canary = root / "canary.json"
            runner.write_json(canary, self._canary(pin_sha))
            review = root / "review.json"
            runner.write_json(review, {"status": "pass", "runtime_pin_sha256": pin_sha})
            candidates = self._assignments("C")
            evaluators = self._assignments("E")
            plan = runtime.freeze_cell_plan(
                campaign_id="FUTURE-FIVE",
                config_root="1" * 64,
                image="sha256:" + "a" * 64,
                source_root="2" * 64,
                candidate_assignments=candidates,
                evaluator_assignments=evaluators,
                canary_receipt=canary,
                runtime_pin=pin,
                independent_review=review,
                output=root / "control",
            )
            self.assertEqual(plan["candidate_denominator"], 5)
            self.assertEqual(plan["evaluator_denominator"], 5)
            self.assertEqual(len(plan["cells"]), 10)
            self.assertEqual(plan["retries"], 0)
            with self.assertRaisesRegex(runtime.HardeningError, "exactly five"):
                runtime.freeze_cell_plan(
                    campaign_id="BAD",
                    config_root="1" * 64,
                    image="sha256:" + "a" * 64,
                    source_root="2" * 64,
                    candidate_assignments=candidates[:4],
                    evaluator_assignments=evaluators,
                    canary_receipt=canary,
                    runtime_pin=pin,
                    independent_review=review,
                    output=root / "bad-control",
                )

    def test_single_use_permit_holds_after_timeout_and_forbids_retry(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = pathlib.Path(raw).resolve()
            plan = root / "plan.json"
            state = root / "state.json"
            cells = [
                {
                    "assignment_root": "1" * 64,
                    "cell_id": "C1",
                    "ordinal": 1,
                    "role": "candidate",
                    "run_root": "2" * 64,
                }
            ]
            runner.write_json(
                plan,
                {
                    "campaign_id": "X",
                    "cells": cells,
                    "config_root": "3" * 64,
                    "image": "sha256:" + "4" * 64,
                    "source_root": "5" * 64,
                },
            )
            runner.write_json(
                state,
                {
                    "active_permit": None,
                    "completed": [],
                    "next_ordinal": 1,
                    "plan_sha256": runner.sha256_file(plan),
                    "status": "operator_hold",
                },
            )
            permit = runtime.mint_permit(plan, state, "C1", root / "permit")
            with self.assertRaisesRegex(runtime.HardeningError, "already active"):
                runtime.mint_permit(plan, state, "C1", root / "retry")
            runtime.consume_permit(root / "permit" / "permit.json", state)
            with self.assertRaisesRegex(runtime.HardeningError, "already consumed"):
                runtime.consume_permit(root / "permit" / "permit.json", state)
            terminal = root / "terminal.json"
            runner.write_json(terminal, self._terminal(permit, status="timeout"))
            final_state = runtime.record_terminal(
                root / "permit" / "permit.json", state, terminal
            )
            self.assertEqual(final_state["status"], "operator_hold")
            self.assertEqual(len(final_state["completed"]), 1)
            with self.assertRaisesRegex(runtime.HardeningError, "no further"):
                runtime.mint_permit(plan, state, "C1", root / "after")

    def test_terminal_receipt_binding_is_immutable(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = pathlib.Path(raw).resolve()
            plan = root / "plan.json"
            state = root / "state.json"
            runner.write_json(
                plan,
                {
                    "campaign_id": "X",
                    "cells": [
                        {
                            "assignment_root": "1" * 64,
                            "cell_id": "C1",
                            "ordinal": 1,
                            "role": "candidate",
                            "run_root": "2" * 64,
                        }
                    ],
                    "config_root": "3" * 64,
                    "image": "sha256:" + "4" * 64,
                    "source_root": "5" * 64,
                },
            )
            runner.write_json(
                state,
                {
                    "active_permit": None,
                    "completed": [],
                    "next_ordinal": 1,
                    "plan_sha256": runner.sha256_file(plan),
                    "status": "operator_hold",
                },
            )
            runtime.mint_permit(plan, state, "C1", root / "permit")
            runtime.consume_permit(root / "permit" / "permit.json", state)
            terminal = root / "terminal.json"
            bad_terminal = self._terminal(
                json.loads((root / "permit" / "permit.json").read_text())
            )
            bad_terminal["assignment_root"] = "9" * 64
            runner.write_json(terminal, bad_terminal)
            with self.assertRaisesRegex(runtime.HardeningError, "assignment_root"):
                runtime.record_terminal(
                    root / "permit" / "permit.json", state, terminal
                )

    def test_evaluator_permit_requires_bound_source_verification(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = pathlib.Path(raw).resolve()
            plan = root / "plan.json"
            state = root / "state.json"
            cells = [
                {
                    "assignment_root": "1" * 64,
                    "cell_id": "C1",
                    "ordinal": 1,
                    "role": "candidate",
                    "run_root": "2" * 64,
                    "target_ordinal": 1,
                },
                {
                    "assignment_root": "3" * 64,
                    "cell_id": "E1",
                    "ordinal": 2,
                    "role": "evaluator",
                    "run_root": "4" * 64,
                    "target_ordinal": 1,
                },
            ]
            runner.write_json(
                plan,
                {
                    "campaign_id": "X",
                    "cells": cells,
                    "config_root": "5" * 64,
                    "image": "sha256:" + "6" * 64,
                    "source_root": "7" * 64,
                },
            )
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
            permit = runtime.mint_permit(plan, state, "C1", root / "candidate-permit")
            runtime.consume_permit(root / "candidate-permit" / "permit.json", state)
            result_sha = "8" * 64
            terminal = root / "candidate-terminal.json"
            candidate_terminal = self._terminal(permit)
            candidate_terminal["result_sha256"] = result_sha
            runner.write_json(terminal, candidate_terminal)
            runtime.record_terminal(
                root / "candidate-permit" / "permit.json", state, terminal
            )
            with self.assertRaisesRegex(runtime.HardeningError, "verification"):
                runtime.mint_permit(plan, state, "E1", root / "evaluator-too-early")
            verification = root / "verification.json"
            runner.write_json(
                verification,
                {
                    "candidate_result_sha256": result_sha,
                    "classification": "valid_non_result",
                    "type": "source-native-nonconversion-verification-v1",
                },
            )
            runtime.bind_source_verification(plan, state, "C1", terminal, verification)
            evaluator = runtime.mint_permit(
                plan, state, "E1", root / "evaluator-permit"
            )
            self.assertEqual(evaluator["role"], "evaluator")
            self.assertEqual(evaluator["target_ordinal"], 1)
            self.assertEqual(
                evaluator["source_verification_sha256"],
                runner.sha256_file(verification),
            )

            runtime.consume_permit(root / "evaluator-permit" / "permit.json", state)
            evaluator_terminal = root / "evaluator-terminal.json"
            runner.write_json(
                evaluator_terminal,
                self._terminal(evaluator, status="timeout"),
            )
            final_state = runtime.record_terminal(
                root / "evaluator-permit" / "permit.json", state, evaluator_terminal
            )
            self.assertEqual(final_state["completed"][1]["role"], "evaluator")
            self.assertEqual(final_state["next_ordinal"], 3)

    @staticmethod
    def _assignments(prefix: str) -> list[dict]:
        return [
            {
                "assignment_root": f"{index:x}" * 64,
                "cell_id": f"{prefix}{index}",
                "run_root": f"{index + 5:x}" * 64,
            }
            for index in range(1, 6)
        ]

    @staticmethod
    def _canary(pin_sha: str) -> dict:
        return {
            "campaign_denominator_effect": "excluded",
            "compile_receipt": "pass",
            "compile_receipt_sha256": "1" * 64,
            "credential_findings": 0,
            "exactly_one_permit_consumed": True,
            "lean_preflight": "pass",
            "model_auth_access": "pass",
            "output_sha256": "2" * 64,
            "permit_sha256": "3" * 64,
            "provider_requests": 1,
            "runtime_pin_sha256": pin_sha,
            "status": "pass",
            "teardown": "pass",
            "timeout_enforced": True,
            "usage_parsed": True,
        }

    @staticmethod
    def _terminal(permit: dict, *, status: str = "completed") -> dict:
        value = {
            name: permit[name]
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
            )
        }
        if "source_verification_sha256" in permit:
            value["source_verification_sha256"] = permit["source_verification_sha256"]
        value.update({"status": status, "terminal": True})
        return value


if __name__ == "__main__":
    unittest.main()
