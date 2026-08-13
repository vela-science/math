#!/usr/bin/env python3
"""Hostile tests for the reusable source-adapter conformance contract."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

import conformance as contract


def fixture_body() -> dict:
    evidence = {
        requirement_id: [f"test_{requirement_id}"]
        for requirement_id in sorted(contract.REQUIRED_REQUIREMENT_IDS)
    }
    return {
        "schema": contract.PROFILE_SCHEMA,
        "adapter": {
            "adapter_id": "fixture-source-adapter",
            "version": "1.0.0",
            "implementation_path": "adapters/fixture.py",
            "implementation_root": "sha256:" + "1" * 64,
            "output_schema": "fixture.source-projection.v1",
        },
        "native_identity": {
            "source_id": "source:fixture",
            "object_identity": ["repository URL", "native record identifier"],
            "revision_semantics": "An exact commit and tree identify one immutable source revision.",
            "mapping_semantics": "exact_native_identity_only",
        },
        "roots": {
            "content": [{
                "field": "record.content_root",
                "domain": "source_content",
                "meaning": "Exact source bytes.",
            }],
            "observation": [{
                "field": "observation.root",
                "domain": "source_observation",
                "meaning": "Observation-time source state.",
            }],
        },
        "read_contract": {
            "completeness": "complete",
            "scope": "One closed two-record fixture.",
            "pagination": "none",
            "max_records": 2,
            "max_bytes_per_record": 4096,
            "bounded_read_behavior": "refuse",
        },
        "custody": {
            "mode": "copied",
            "source_locator": "https://example.test/source",
            "retained_bytes": True,
            "copied": ["two exact fixture records"],
            "referenced": [],
        },
        "rights": {
            "license": "Apache-2.0",
            "access": "public",
            "redistribution": "full_under_license",
            "public_redaction": "No private fields enter the fixture.",
        },
        "semantics": {
            "preserves": ["native identity"],
            "omits": ["mutable discussion"],
            "unsupported_states": ["unknown schema versions"],
            "fail_closed_behavior": "Unsupported or incomplete input refuses projection.",
            "nonclaims": ["The source result is not a Vela Decision or Standing."],
        },
        "lifecycle": {
            "deletion": "Retain exact historical custody and report later absence.",
            "tombstone": "A new observation may mark a source-native tombstone.",
            "update_detection": "A changed revision or root requires a new projection.",
            "drift_response": "Never rewrite a prior projection.",
        },
        "field_classes": [
            {"path": "native.id", "mutability": "immutable", "meaning": "Source identity."},
            {"path": "observation.state", "mutability": "observation_time_only", "meaning": "Observed state."},
        ],
        "reconstructibility": {
            "possible": ["Inspect retained source bytes."],
            "unavailable": ["Re-run an omitted external service."],
        },
        "writeback": {
            "mode": "none",
            "path": None,
            "nonclaim": "No local result was returned to or accepted by the source.",
        },
        "requirement_evidence": evidence,
        "authority_effect": "none",
        "profile_root_definition": contract.PROFILE_ROOT_DEFINITION,
    }


class ConformanceContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = contract.finalize_profile(fixture_body())

    def test_profile_is_rooted_and_strict(self) -> None:
        self.assertEqual(contract.validate_profile(self.profile), self.profile)
        self.assertEqual(self.profile["profile_root"], contract.profile_root(self.profile))

    def test_canonical_loader_refuses_duplicate_keys_and_framing_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profile.json"
            path.write_bytes(contract.canonical_bytes(self.profile) + b"\n")
            self.assertEqual(contract.load_profile(path), self.profile)
            path.write_bytes(contract.canonical_bytes(self.profile) + b"\n\n")
            with self.assertRaisesRegex(contract.ConformanceError, "exactly one trailing LF"):
                contract.load_profile(path)
            path.write_text('{"schema":"a","schema":"b"}\n', encoding="utf-8")
            with self.assertRaisesRegex(contract.ConformanceError, "duplicate JSON key"):
                contract.load_profile(path)

    def test_root_and_authority_mutations_refuse(self) -> None:
        drifted = copy.deepcopy(self.profile)
        drifted["profile_root"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(contract.ConformanceError, "profile root drift"):
            contract.validate_profile(drifted)
        authoritative = copy.deepcopy(self.profile)
        authoritative["authority_effect"] = "standing"
        authoritative["profile_root"] = contract.profile_root(authoritative)
        with self.assertRaisesRegex(contract.ConformanceError, "cannot carry authority"):
            contract.validate_profile(authoritative)

    def test_rights_custody_bounds_and_paths_fail_closed(self) -> None:
        mutations = (
            (["rights", "license"], None, "full redistribution requires"),
            (["custody", "source_locator"], "http://example.test", "must use HTTPS"),
            (["read_contract", "max_records"], 0, "positive integer"),
            (["read_contract", "max_records"], True, "positive integer"),
            (["adapter", "implementation_path"], "../escape.py", "safe repository-relative"),
        )
        for path, replacement, message in mutations:
            with self.subTest(path=path):
                value = copy.deepcopy(self.profile)
                target = value
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = replacement
                value["profile_root"] = contract.profile_root(value)
                with self.assertRaisesRegex(contract.ConformanceError, message):
                    contract.validate_profile(value)

    def test_requirement_inventory_and_observed_evidence_are_exact(self) -> None:
        missing = copy.deepcopy(self.profile)
        missing["requirement_evidence"].pop("complete_bounded_reads")
        missing["profile_root"] = contract.profile_root(missing)
        with self.assertRaisesRegex(contract.ConformanceError, "requirement inventory drift"):
            contract.validate_profile(missing)

        observed = {
            key: set(value)
            for key, value in self.profile["requirement_evidence"].items()
        }
        contract.assert_requirement_coverage(self.profile, observed)
        observed["complete_bounded_reads"] = {"test_unrelated"}
        with self.assertRaisesRegex(contract.ConformanceError, "evidence drift"):
            contract.assert_requirement_coverage(self.profile, observed)

    def test_unknown_mutability_schema_and_mapping_refuse(self) -> None:
        mutations = (
            (["field_classes", 0, "mutability"], "sometimes", "unsupported source field mutability"),
            (["schema"], "vela.source-adapter-conformance-profile.v2", "unsupported adapter"),
            (["native_identity", "mapping_semantics"], "guess", "unsupported native mapping"),
        )
        for path, replacement, message in mutations:
            with self.subTest(path=path):
                value = copy.deepcopy(self.profile)
                target = value
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = replacement
                value["profile_root"] = contract.profile_root(value)
                with self.assertRaisesRegex(contract.ConformanceError, message):
                    contract.validate_profile(value)


if __name__ == "__main__":
    unittest.main()
