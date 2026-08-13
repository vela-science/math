#!/usr/bin/env python3

import copy
import hashlib
import importlib.util
from pathlib import Path
import unittest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "build_collection_readiness", HERE / "build_collection_readiness.py"
)
assert SPEC and SPEC.loader
BUILD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)


class CollectionReadinessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.materials = BUILD.load(BUILD.MATERIALS)
        cls.packets = BUILD.load(BUILD.PACKETS)
        cls.readiness = BUILD.load(BUILD.READINESS)

    def assert_descriptor(self, item: dict[str, object]) -> None:
        path = BUILD.REPO / item["path"]
        raw = path.read_bytes()
        self.assertEqual(item["raw_sha256"], "sha256:" + hashlib.sha256(raw).hexdigest())
        self.assertEqual(item["size"], len(raw))

    def test_generated_files_match_the_deterministic_builder(self) -> None:
        for path, (_, raw) in BUILD.build().items():
            self.assertEqual(path.read_bytes(), raw)
        self.assertEqual(
            self.materials["materials_root"],
            BUILD.semantic_root(self.materials, "materials_root"),
        )
        self.assertEqual(
            self.packets["packet_set_root"],
            BUILD.semantic_root(self.packets, "packet_set_root"),
        )
        self.assertEqual(
            self.readiness["readiness_root"],
            BUILD.semantic_root(self.readiness, "readiness_root"),
        )

    def test_five_matched_control_treatment_pairs_are_frozen(self) -> None:
        packets = self.packets["packets"]
        self.assertEqual(len(packets), 10)
        by_fixture: dict[str, list[dict[str, object]]] = {}
        for packet in packets:
            self.assertEqual(packet["packet_root"], BUILD.semantic_root(packet, "packet_root"))
            by_fixture.setdefault(packet["fixture_id"], []).append(packet)
            for item in packet["shared_evidence"] + packet["treatment_evidence"]:
                self.assert_descriptor(item)
        self.assertEqual(len(by_fixture), 5)
        self.assertIn("isolated participant file", self.packets["delivery_rule"])
        shared_fields = (
            "fixture_id",
            "task_wording",
            "pull_request",
            "source_repository_url",
            "source_setup_commands",
            "public_source_command",
            "shared_evidence",
            "access_limits",
        )
        for pair in by_fixture.values():
            self.assertEqual(len(pair), 2)
            control = next(item for item in pair if item["condition"].startswith("plain-git"))
            treatment = next(item for item in pair if item["condition"].startswith("same-inputs"))
            for field in shared_fields:
                self.assertEqual(control[field], treatment[field])
            self.assertEqual(control["treatment_evidence"], [])
            self.assertEqual(len(treatment["treatment_evidence"]), 2)
            self.assertTrue(
                all("expected-" in item["path"] for item in treatment["treatment_evidence"])
            )
            self.assertTrue(
                all("fidelity-witness" not in item["path"] for item in control["shared_evidence"])
            )

    def test_consent_and_custody_materials_are_public_safe(self) -> None:
        consent = self.materials["consent"]
        self.assertIn("voluntary", consent["participation"])
        self.assertIn("180 days", consent["retention"])
        self.assertIn("outside Git", consent["private_custody"])
        self.assertIn("none is assumed", consent["benefits_and_compensation"])
        self.assertEqual(len(consent["affirmations"]), 3)
        joined = (BUILD.MATERIALS.read_bytes() + BUILD.PACKETS.read_bytes()).lower()
        for forbidden in (b"/users/", b"/private/", b"@gmail", b"github_token", b"-----begin"):
            self.assertNotIn(forbidden, joined)

    def test_readiness_remains_closed_until_humans_and_private_custody_exist(self) -> None:
        gates = self.readiness["gates"]
        self.assertTrue(gates["ground_truth_complete"])
        self.assertTrue(gates["consent_materials_frozen"])
        self.assertTrue(gates["condition_packets_frozen"])
        self.assertTrue(gates["allocation_receipt_format_frozen"])
        self.assertTrue(gates["private_custody_plan_frozen"])
        for field in (
            "human_custodian_assigned",
            "participants_recruited",
            "participants_consented",
            "allocation_receipt_instantiated",
            "private_custody_activated",
            "collection_open",
        ):
            self.assertFalse(gates[field])
        self.assertEqual(len(self.readiness["current_blockers"]), 3)
        self.assertEqual(self.readiness["authority_effect"], "none")
        self.assertEqual(len(self.readiness["does_not_establish"]), 2)

    def test_changed_packet_or_material_moves_its_root(self) -> None:
        packet = copy.deepcopy(self.packets["packets"][0])
        original = packet["packet_root"]
        packet["access_limits"] += " changed"
        self.assertNotEqual(original, BUILD.semantic_root(packet, "packet_root"))
        materials = copy.deepcopy(self.materials)
        original = materials["materials_root"]
        materials["consent"]["retention"] += " changed"
        self.assertNotEqual(original, BUILD.semantic_root(materials, "materials_root"))


if __name__ == "__main__":
    unittest.main()
