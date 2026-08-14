#!/usr/bin/env python3
"""Contract tests for the bounded Erdős 887 proof-discharge Work Offer."""

from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main, mock


HERE = Path(__file__).resolve().parent


def _module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BUILD = _module("proof_discharge_build", HERE / "build.py")
RUN = _module("proof_discharge_run", HERE / "run_attempt.py")


class ProofDischargeOfferTests(TestCase):
    def test_generated_bytes_are_canonical_rooted_and_frozen(self) -> None:
        for path, value, root_field in BUILD.build():
            raw = BUILD._canonical_bytes(value) + b"\n"
            self.assertEqual(path.read_bytes(), raw)
            self.assertEqual(value[root_field], BUILD._root_without(value, root_field))
            self.assertEqual(json.loads(raw), value)

    def test_current_exact_source_and_open_problem_scope_are_bound(self) -> None:
        packet = BUILD.build()[-1][1]
        self.assertEqual(packet["target"]["id"], "erdos:887:proof-discharge")
        self.assertEqual(packet["source"]["head_commit"], BUILD.SOURCE_COMMIT)
        self.assertEqual(packet["source"]["git_blob_oid"], BUILD.SOURCE_BLOB)
        self.assertEqual(packet["source"]["raw_sha256"], BUILD.SOURCE_RAW_SHA256)
        self.assertEqual(packet["source"]["declaration"], "Erdos887.erdos_887.parts.ii")
        self.assertEqual(packet["source"]["source_status"], "research_open")
        self.assertIn("problem is open", " ".join(packet["nonclaims"]))

    def test_performer_classes_are_peer_provenance_not_quality_ranks(self) -> None:
        profile = BUILD.build_profile()
        policy = profile["performer_policy"]
        self.assertEqual(policy["eligible_classes"], ["agent", "human", "organization", "tool"])
        self.assertFalse(policy["class_is_quality_rank"])
        self.assertIn("model, provider, runtime, and tool versions when applicable", policy["required_provenance"])

    def test_terminal_states_distinguish_proof_partial_negative_and_error(self) -> None:
        contract = BUILD.build_contract()
        self.assertEqual(
            set(contract["terminal_states"]),
            {
                "proved_candidate",
                "bounded_partial_result",
                "bounded_obstruction_or_counterexample_candidate",
                "not_proved_within_declared_bounds",
                "execution_error",
            },
        )
        proof_requirements = " ".join(contract["terminal_states"]["proved_candidate"]["requirements"])
        self.assertIn("#print axioms", proof_requirements)
        self.assertIn("no sorryAx", proof_requirements)
        negative_requirements = " ".join(
            contract["terminal_states"]["not_proved_within_declared_bounds"]["requirements"]
        )
        self.assertIn("Do not claim impossibility", negative_requirements)

    def test_preparation_uses_exact_public_source_and_writes_no_authority(self) -> None:
        packet = BUILD.build()[-1][1]
        offer = {
            "presence": "open",
            "execution_binding": {
                "schema": "vela.execution-binding.v1",
                "packet_root": packet["packet_root"],
                "profile_root": packet["execution_components"]["producer_profile"]["root"],
                "verifier_capsule_root": packet["execution_components"]["verifier_capsule"]["root"],
                "result_contract_root": packet["execution_components"]["result_contract"]["root"],
            },
            "packet": {"path": str(BUILD.PACKET_PATH.relative_to(BUILD.REPO_ROOT)), "packet_root": packet["packet_root"]},
        }

        with TemporaryDirectory() as temporary:
            destination = Path(temporary) / "attempt"
            source_raw = b"exact source fixture\n"

            def fake_run(*args: str, cwd: Path | None = None) -> str:
                if args[:4] == ("git", "-c", "credential.helper=", "clone"):
                    source = Path(args[-1])
                    (source / RUN.SOURCE_PATH).parent.mkdir(parents=True)
                    (source / RUN.SOURCE_PATH).write_bytes(source_raw)
                    return ""
                if args == ("git", "rev-parse", "HEAD"):
                    return RUN.SOURCE_COMMIT
                if args == ("git", "show", "-s", "--format=%T", "HEAD"):
                    return RUN.SOURCE_TREE
                if args == ("git", "rev-parse", f"HEAD:{RUN.SOURCE_PATH}"):
                    return RUN.SOURCE_BLOB
                if args == ("git", "status", "--porcelain"):
                    return ""
                if args[:2] == ("git", "checkout"):
                    return ""
                raise AssertionError(args)

            with (
                mock.patch.object(RUN, "_load_offer", return_value=offer),
                mock.patch.object(RUN, "_run", side_effect=fake_run),
                mock.patch.object(RUN, "_sha256", return_value=RUN.SOURCE_RAW_SHA256),
            ):
                context = RUN.prepare(destination)
            self.assertEqual(context["authority_effect"], "none")
            self.assertFalse(context["declared_bounds"]["upstream_writes"])
            self.assertEqual(context["source"]["commit"], RUN.SOURCE_COMMIT)
            self.assertEqual(context["execution_binding"], offer["execution_binding"])
            self.assertEqual((destination / "source" / RUN.SOURCE_PATH).read_bytes(), source_raw)

    def test_existing_preparation_destination_is_refused(self) -> None:
        with TemporaryDirectory() as temporary, mock.patch.object(RUN, "_load_offer", return_value={}):
            with self.assertRaisesRegex(RUN.AttemptPreparationError, "destination already exists"):
                RUN.prepare(Path(temporary))

    def test_retained_result_and_artifact_custody_are_verified(self) -> None:
        result_dir = HERE.parent / "results/erdos-887-proof-discharge-attempt-01"
        result = _module("proof_discharge_capture", HERE / "capture_result.py")._check(result_dir)
        self.assertEqual(result["terminal_state"], "not_proved_within_declared_bounds")
        self.assertEqual(result["producer"]["actor_class"], "agent")
        with TemporaryDirectory() as temporary:
            changed_dir = Path(temporary) / "result"
            shutil.copytree(result_dir, changed_dir)
            changed = json.loads((changed_dir / "result.v1.json").read_bytes())
            changed["artifacts"]["axiom-probe.lean"]["path"] = "../escape"
            capture = _module("proof_discharge_capture_changed", HERE / "capture_result.py")
            changed["result_root"] = capture._root_without(changed, "result_root")
            (changed_dir / "result.v1.json").write_bytes(capture._canonical_bytes(changed) + b"\n")
            with self.assertRaisesRegex(capture.CaptureError, "escapes result custody"):
                capture._check(changed_dir)


if __name__ == "__main__":
    main()
