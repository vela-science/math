#!/usr/bin/env python3
"""Focused integrity tests for the handoff revision."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import unittest

import jsonschema


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]


def load(path: Path):
    return json.loads(path.read_text())


def canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def root(value: dict, field: str) -> str:
    unrooted = dict(value)
    unrooted.pop(field, None)
    return "sha256:" + hashlib.sha256(canonical(unrooted)).hexdigest()


class HandoffRevisionTest(unittest.TestCase):
    def test_builder_is_deterministic(self):
        paths = sorted(HERE.glob("compact-handoffs/*.json")) + [HERE / "compact-handoff-set.v0.2.json", HERE / "handoff-revision-allocation.v0.2.json"]
        before = {path: path.read_bytes() for path in paths}
        subprocess.run(["python3", "-B", str(HERE / "build_handoff_revision.py")], cwd=REPO, check=True)
        self.assertEqual(before, {path: path.read_bytes() for path in paths})

    def test_complete_paired_inventory_and_roots(self):
        allocation = load(HERE / "handoff-revision-allocation.v0.2.json")
        self.assertEqual(allocation["allocation_root"], root(allocation, "allocation_root"))
        self.assertEqual(allocation["assignment_count"], 30)
        pairs = {}
        for item in allocation["assignments"]:
            pairs.setdefault(item["pair_id"], set()).add(item["condition"])
        self.assertEqual(len(pairs), 15)
        self.assertTrue(all(value == {"legacy_full_audit_handoff", "compact_attributed_handoff"} for value in pairs.values()))

    def test_compact_handoffs_bind_required_provenance(self):
        for path in HERE.glob("compact-handoffs/*.json"):
            packet = load(path)
            self.assertEqual(packet["handoff_root"], root(packet, "handoff_root"))
            self.assertEqual(packet["authority_effect"], "none")
            self.assertRegex(packet["source"]["commit"], r"^[0-9a-f]{40}$")
            self.assertRegex(packet["sender"]["output"]["raw_sha256"], r"^sha256:[0-9a-f]{64}$")
            self.assertTrue(packet["sender"]["evidence_locators"])
            self.assertTrue(packet["authority"]["does_not_establish"])

    def test_output_schema_refuses_authority_and_partial_provenance(self):
        schema = load(HERE / "receiver-output.schema.v0.2.json")
        validator = jsonschema.Draft202012Validator(schema)
        base = {
            "schema": "vela.math.fc-audit.agent-handoff-receiver-output.v0.2",
            "fixture_id": "fixture",
            "condition": "compact_attributed_handoff",
            "packet_root": "sha256:" + "1" * 64,
            "sender_output_sha256": "sha256:" + "2" * 64,
            "retained_verdict": "clean",
            "retained_issue_codes": [],
            "provenance_bindings": {"source_commit": "3" * 40, "source_path": "x.lean", "source_raw_sha256": "sha256:" + "4" * 64, "sender_output_sha256": "sha256:" + "2" * 64, "original_packet_root": "sha256:" + "1" * 64, "evidence_locators_retained": True, "authority_effect": "none"},
            "continuation_summary": "bounded",
            "reproduction_terminal_state": "scoped",
            "missing_provenance_fields": [],
            "next_action": None,
            "unsupported_claims": [],
            "authority_effect": "none",
            "does_not_establish": ["acceptance", "Standing"],
            "confidence": "high",
        }
        validator.validate(base)
        forged = json.loads(json.dumps(base))
        forged["authority_effect"] = "standing"
        self.assertRaises(jsonschema.ValidationError, validator.validate, forged)
        partial = json.loads(json.dumps(base))
        del partial["provenance_bindings"]["source_commit"]
        self.assertRaises(jsonschema.ValidationError, validator.validate, partial)

    def test_failed_attempt_is_complete_and_pre_inference(self):
        manifest = load(HERE / "failed-attempt-01-invalid-schema/failure-manifest.v0.2.json")
        self.assertEqual(manifest["observation_count"], 30)
        self.assertEqual(manifest["terminal_states"], {"error": 30})
        self.assertEqual(manifest["model_output_count"], 0)
        self.assertEqual(manifest["failure_root"], root(manifest, "failure_root"))

    def test_program_disposition_preserves_the_negative_threshold_result(self):
        result = load(HERE / "handoff-revision-results.v0.2.json")
        disposition = load(HERE / "program-disposition.v0.2.json")
        self.assertEqual(disposition["content_root"], root(disposition, "content_root"))
        self.assertEqual(disposition["result"]["results_root"], result["results_root"])
        self.assertFalse(disposition["result"]["frozen_hypothesis_supported"])
        self.assertEqual(disposition["result"]["frozen_interface_disposition"], "revise")
        self.assertEqual(
            disposition["decision"]["action"],
            "adopt_compact_handoff_for_receiver_input",
        )
        self.assertEqual(disposition["measured_evidence"]["authority_violations"], 0)


if __name__ == "__main__":
    unittest.main()
