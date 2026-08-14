#!/usr/bin/env python3
"""Hostile and positive tests for immutable source Work Offer lifecycle."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
from unittest import TestCase, main, mock


SPEC = importlib.util.spec_from_file_location(
    "fc_work_offer_build",
    Path(__file__).resolve().parent / "build.py",
)
assert SPEC is not None and SPEC.loader is not None
BUILD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)


class WorkOfferLifecycleTests(TestCase):
    def test_generated_bytes_are_frozen_and_non_authoritative(self) -> None:
        packet, packet_raw, lifecycle, lifecycle_raw, index, index_raw = BUILD.build()
        self.assertEqual(BUILD.PACKET_PATH.read_bytes(), packet_raw)
        self.assertEqual(BUILD.LIFECYCLE_PATH.read_bytes(), lifecycle_raw)
        self.assertEqual(BUILD.INDEX_PATH.read_bytes(), index_raw)
        self.assertEqual(packet["authority_effect"], "none")
        self.assertEqual(lifecycle["authority_effect"], "none")
        self.assertEqual(index["authority_effect"], "none")
        self.assertEqual(index["targets"][0]["presence"], "superseded")
        self.assertIsNone(index["targets"][0]["next_command"])
        self.assertEqual(index["targets"][1]["id"], BUILD.PROOF_TARGET_ID)
        self.assertEqual(index["targets"][1]["presence"], "open")
        self.assertIsInstance(index["targets"][1]["next_command"], str)
        self.assertNotIn("lifecycle", index["targets"][1])
        self.assertEqual(len(index["targets"][1]["attempts"]), 1)
        self.assertEqual(index["targets"][1]["attempts"][0]["terminal_state"], "not_proved_within_declared_bounds")
        self.assertEqual(index["targets"][1]["attempts"][0]["performer"]["actor_class"], "agent")

    def test_exact_issued_packet_is_restored_instead_of_rebound(self) -> None:
        packet, packet_raw, lifecycle, _, index, _ = BUILD.build()
        self.assertEqual(packet_raw, BUILD.ISSUED_PACKET_SOURCE_PATH.read_bytes())
        self.assertEqual(packet_raw, BUILD._git_bytes(BUILD.ISSUANCE_COMMIT, BUILD.PACKET_PATH))
        self.assertEqual(packet["packet_root"], "sha256:a2cfe3df8cf15559a5fd06bf51329fff89243dc361356b96c268a52ef5bfd057")
        self.assertEqual(lifecycle["issued_offer"]["packet"]["packet_root"], packet["packet_root"])
        self.assertEqual(index["targets"][0]["execution_binding"]["packet_root"], packet["packet_root"])
        retired = {entry["packet_root"] for entry in lifecycle["retired_rebindings"]}
        self.assertIn("sha256:bcbcc9d4f90603df5e83af462b02076d0c50d850b10b38297231aef4eab95429", retired)
        self.assertNotIn(packet["packet_root"], retired)

    def test_closure_binds_contract_gap_result_review_and_scientific_decision(self) -> None:
        _, _, lifecycle, _, _, _ = BUILD.build()
        completion = lifecycle["completion"]
        self.assertEqual(completion["contract_status"], "not_satisfied")
        self.assertEqual(completion["closure_status"], "closed_superseded")
        self.assertIn("required an independent human review", completion["contract_gap"])
        self.assertEqual(completion["result"]["result_root"], "sha256:9902098245a52f67dedeefe06b4353a530ef251b93bb80465c6aafa6fca1865c")
        self.assertEqual(completion["review"]["outcome"], "pass")
        self.assertEqual(completion["review"]["reviewer"]["kind"], "ai_model")
        self.assertTrue(completion["review"]["independence"]["independent"])
        scientific = lifecycle["decisions"]["scientific"]
        self.assertEqual(scientific["status"], "accepted")
        self.assertEqual(scientific["proposal_id"], "vpr_44ff50ca8cf1bd6e")
        self.assertEqual(scientific["performer"]["class"], "human")
        self.assertEqual(scientific["claim_root"], lifecycle["remap"]["next_obligation"]["basis_claim_root"])

    def test_decision_domains_and_remap_do_not_collapse(self) -> None:
        _, _, lifecycle, _, _, _ = BUILD.build()
        decisions = lifecycle["decisions"]
        self.assertEqual(set(decisions), {"scientific", "program", "deployment"})
        self.assertEqual(decisions["program"]["status"], "not_applicable")
        self.assertEqual(decisions["deployment"]["status"], "not_applicable")
        self.assertEqual(decisions["program"]["authority_effect"], "none")
        self.assertEqual(lifecycle["remap"]["state"], "offered")
        self.assertEqual(lifecycle["remap"]["work_offer"]["presence"], "open")
        self.assertEqual(lifecycle["remap"]["work_offer"]["execution_binding"]["schema"], "vela.execution-binding.v1")
        self.assertIn("carries no scientific authority", " ".join(lifecycle["nonclaims"]))

    def test_repository_root_advancement_cannot_reissue_packet(self) -> None:
        packet, packet_raw, lifecycle, _, index, _ = BUILD.build()
        proof_packet, proof_packet_raw = BUILD.load_proof_packet()
        advanced = copy.deepcopy(index["repository"])
        advanced["repository_root"] = "sha256:" + "9" * 64
        with mock.patch.object(BUILD, "_repository_binding", return_value=advanced):
            with self.assertRaisesRegex(BUILD.WorkOfferError, "proof-discharge packet Repository root drift"):
                BUILD.build()
        rebuilt_lifecycle = BUILD.build_lifecycle(packet, packet_raw, proof_packet, proof_packet_raw)
        self.assertEqual(rebuilt_lifecycle["lifecycle_root"], lifecycle["lifecycle_root"])
        self.assertEqual(index["targets"][0]["packet"]["packet_root"], packet["packet_root"])
        self.assertEqual(index["targets"][0]["presence"], "superseded")

    def test_review_or_decision_binding_drift_is_refused(self) -> None:
        original_load = BUILD._load
        review = original_load(BUILD.REVIEW_PATH)
        changed_review = copy.deepcopy(review)
        changed_review["outcome"] = "fail"
        with mock.patch.object(
            BUILD,
            "_load",
            side_effect=lambda path, **kwargs: changed_review if path == BUILD.REVIEW_PATH else original_load(path, **kwargs),
        ):
            with self.assertRaisesRegex(BUILD.WorkOfferError, "not a passing review"):
                BUILD.build()

        decision = original_load(BUILD.DECISION_EVENT_PATH, require_framed_lf=False)
        changed_decision = copy.deepcopy(decision)
        changed_decision["content"]["payload"]["proposal_id"] = "vpr_wrong"
        with mock.patch.object(
            BUILD,
            "_load",
            side_effect=lambda path, **kwargs: changed_decision if path == BUILD.DECISION_EVENT_PATH else original_load(path, **kwargs),
        ):
            with self.assertRaisesRegex(BUILD.WorkOfferError, "does not accept the reviewed Proposal"):
                BUILD.build()

    def test_duplicate_json_keys_are_refused(self) -> None:
        with self.assertRaisesRegex(BUILD.WorkOfferError, "duplicate JSON key"):
            json.loads('{"a":1,"a":2}', object_pairs_hook=BUILD._reject_duplicate_keys)

    def test_proof_attempt_binding_drift_is_refused(self) -> None:
        packet, _ = BUILD.load_proof_packet()
        original_load = BUILD._load
        result = original_load(BUILD.PROOF_RESULT_PATH)
        changed = copy.deepcopy(result)
        changed["execution_binding"]["profile_root"] = "sha256:" + "0" * 64
        changed["result_root"] = BUILD._root_without(changed, "result_root")
        with mock.patch.object(
            BUILD,
            "_load",
            side_effect=lambda path, **kwargs: changed if path == BUILD.PROOF_RESULT_PATH else original_load(path, **kwargs),
        ):
            with self.assertRaisesRegex(BUILD.WorkOfferError, "attempt binding or root drift"):
                BUILD.load_proof_attempt(packet)


if __name__ == "__main__":
    main()
