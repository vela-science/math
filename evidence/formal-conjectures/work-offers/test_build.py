#!/usr/bin/env python3
"""Hostile and positive tests for the current FC source-local work offer."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
from unittest import TestCase, main, mock


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("fc_work_offer_build", HERE / "build.py")
assert SPEC is not None and SPEC.loader is not None
BUILD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)


class WorkOfferTests(TestCase):
    def test_generated_bytes_are_frozen_and_non_authoritative(self) -> None:
        packet, packet_raw, index, index_raw = BUILD.build()
        self.assertEqual(BUILD.PACKET_PATH.read_bytes(), packet_raw)
        self.assertEqual(BUILD.INDEX_PATH.read_bytes(), index_raw)
        self.assertEqual(packet["authority_effect"], "none")
        self.assertEqual(index["authority_effect"], "none")
        self.assertEqual(index["claim_boundary"], {"derived": True, "authoritative": False, "deletable": True})
        self.assertIn("not a Vela protocol object", " ".join(packet["nonclaims"]))
        self.assertIn("not a Vela Proposal", " ".join(index["nonclaims"]))

    def test_roots_and_packet_custody_recompute(self) -> None:
        packet, packet_raw, index, _ = BUILD.build()
        self.assertEqual(packet["packet_root"], BUILD._root_without(packet, "packet_root"))
        self.assertEqual(index["index_root"], BUILD._root_without(index, "index_root"))
        descriptor = index["targets"][0]["packet"]
        self.assertEqual(descriptor["size"], len(packet_raw))
        self.assertEqual(descriptor["raw_sha256"], BUILD._raw_root(packet_raw))
        self.assertEqual(descriptor["packet_root"], packet["packet_root"])

    def test_target_is_grounded_in_the_exact_adverse_source_record(self) -> None:
        packet, _, index, _ = BUILD.build()
        self.assertEqual(packet["target"]["source_fixture_id"], BUILD.FIXTURE_ID)
        self.assertEqual(packet["source"]["observed_disposition"], "needs_revision")
        self.assertEqual(packet["source"]["basis_check_id"], "answer-slot-scope")
        self.assertEqual(index["source"]["record_root"], packet["source"]["record_root"])
        self.assertEqual(index["source"]["projection_root"], packet["source"]["projection_root"])
        self.assertIn("despite a successful exact-head build", " ".join(packet["nonclaims"]))

    def test_upstream_write_and_authority_actions_are_forbidden(self) -> None:
        packet, _, _, _ = BUILD.build()
        forbidden = " ".join(packet["completion_contract"]["forbidden"])
        self.assertIn("Posting or editing any upstream comment", forbidden)
        self.assertIn("Repository authority credentials", forbidden)
        self.assertIn("Vela Verification, Decision, Event, or Standing", forbidden)

    def test_source_authority_or_disposition_drift_is_refused(self) -> None:
        projection = BUILD._load(BUILD.PROJECTION_PATH)
        original_load = BUILD._load
        authoritative = copy.deepcopy(projection)
        authoritative["authority_effect"] = "standing"
        with mock.patch.object(BUILD, "_load", side_effect=lambda path, **kwargs: authoritative if path == BUILD.PROJECTION_PATH else original_load(path, **kwargs)):
            with self.assertRaisesRegex(BUILD.WorkOfferError, "cannot carry authority"):
                BUILD.build()

        changed = copy.deepcopy(projection)
        record = next(item for item in changed["records"] if item["fixture_id"] == BUILD.FIXTURE_ID)
        record["source_axis"]["advisory_disposition"] = "inconclusive"
        changed["root"]["value"] = BUILD._root_without(changed, "root")
        with mock.patch.object(BUILD, "_load", side_effect=lambda path, **kwargs: changed if path == BUILD.PROJECTION_PATH else original_load(path, **kwargs)):
            with self.assertRaisesRegex(BUILD.WorkOfferError, "must remain grounded in the adverse"):
                BUILD.build()

    def test_duplicate_json_keys_are_refused(self) -> None:
        with self.assertRaisesRegex(BUILD.WorkOfferError, "duplicate JSON key"):
            json.loads('{"a":1,"a":2}', object_pairs_hook=BUILD._reject_duplicate_keys)


if __name__ == "__main__":
    main()
