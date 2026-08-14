#!/usr/bin/env python3
"""Hostile and deterministic checks for MATH-CLAIM-01 preparation."""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import unittest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "claim_occurrence_build", HERE / "build.py"
)
assert SPEC and SPEC.loader
BUILD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)


class PacketTest(unittest.TestCase):
    def setUp(self) -> None:
        self.documents = BUILD.expected_documents()

    def assert_refused(self, mutate) -> None:
        documents = copy.deepcopy(self.documents)
        mutate(documents)
        for name in documents:
            documents[name] = BUILD.reroot(documents[name])
        with self.assertRaises(BUILD.PacketError):
            BUILD.validate_documents(documents)

    def occurrence(self, documents):
        return documents[BUILD.OCCURRENCE.name]

    def plan(self, documents):
        return documents[BUILD.PLAN.name]

    def test_retained_documents_are_exact(self) -> None:
        BUILD.main(["--check"])

    def test_workflow_is_non_authoritative_and_complete(self) -> None:
        workflow = (
            BUILD.REPO / ".github/workflows/math-authority-maintenance.yml"
        ).read_text()
        self.assertEqual(
            workflow.count('- "evidence/erdos-321/claim-occurrence-correction/**"'), 2
        )
        self.assertIn(
            "python3 -B evidence/erdos-321/claim-occurrence-correction/build.py --check",
            workflow,
        )
        self.assertIn(
            "python3 -B evidence/erdos-321/claim-occurrence-correction/test_build.py",
            workflow,
        )
        self.assertIn(BUILD.REPOSITORY_ROOT.removeprefix("sha256:"), workflow)
        self.assertIn(
            "actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803", workflow
        )
        for writer in ("vela submit", "vela verification record", "vela review accept"):
            self.assertNotIn(writer, workflow)

    def test_short_revision_refuses(self) -> None:
        self.assert_refused(
            lambda docs: self.occurrence(docs)["resolver"].__setitem__(
                "commit", BUILD.WEB_COMMIT[:8]
            )
        )

    def test_mutable_identity_claimed_immutable_refuses(self) -> None:
        self.assert_refused(
            lambda docs: self.occurrence(docs)["resolver"]["reference"][
                "locator"
            ].__setitem__(
                "uri",
                "https://github.com/vela-science/vela-web/blob/main/packages/observatory-data/config/problem-resolution.v1.json",
            )
        )

    def test_revision_drift_refuses(self) -> None:
        self.assert_refused(
            lambda docs: self.occurrence(docs)["resolver"]["reference"][
                "revision"
            ].__setitem__("value", "0" * 40)
        )

    def test_selector_drift_refuses(self) -> None:
        self.assert_refused(
            lambda docs: self.occurrence(docs)["resolver"]["reference"][
                "selector"
            ].__setitem__("value", "problem:erdos:322")
        )

    def test_path_escape_refuses(self) -> None:
        self.assert_refused(
            lambda docs: self.occurrence(docs)["retained_sources"][0].__setitem__(
                "retained_path", "../../private.lean"
            )
        )

    def test_unsupported_packet_format_refuses(self) -> None:
        self.assert_refused(
            lambda docs: self.occurrence(docs).__setitem__(
                "packet_format", "vela.math.claim-occurrence-resolution.v2"
            )
        )

    def test_wrong_root_domain_refuses(self) -> None:
        documents = copy.deepcopy(self.documents)
        self.occurrence(documents)["content_root"] = "blake3:" + "0" * 64
        with self.assertRaises(BUILD.PacketError):
            BUILD.validate_documents(documents)

    def test_rights_omission_refuses(self) -> None:
        self.assert_refused(lambda docs: self.occurrence(docs).pop("rights"))

    def test_availability_omission_refuses(self) -> None:
        self.assert_refused(lambda docs: self.occurrence(docs).pop("availability"))

    def test_mapping_translation_collapse_refuses(self) -> None:
        def mutate(documents):
            occurrence = self.occurrence(documents)
            occurrence["mappings"][0]["translation"] = "preserved"
            occurrence.pop("translations")

        self.assert_refused(mutate)

    def test_authority_field_refuses(self) -> None:
        self.assert_refused(
            lambda docs: self.occurrence(docs).__setitem__("standing", "accepted")
        )

    def test_build_or_review_as_acceptance_refuses(self) -> None:
        self.assert_refused(
            lambda docs: self.plan(docs)["successor_draft"].__setitem__(
                "standing", "accepted"
            )
        )

    def test_unavailable_converted_to_result_refuses(self) -> None:
        self.assert_refused(
            lambda docs: self.plan(docs)["successor_draft"].__setitem__(
                "availability", "pass"
            )
        )

    def test_wrong_correction_relation_refuses(self) -> None:
        self.assert_refused(
            lambda docs: self.plan(docs)["requested_change"].__setitem__(
                "relation", "supersedes"
            )
        )

    def test_target_root_drift_refuses(self) -> None:
        self.assert_refused(
            lambda docs: self.plan(docs)["target"].__setitem__(
                "claim_root", "sha256:" + "0" * 64
            )
        )

    def test_fabricated_future_identity_refuses(self) -> None:
        self.assert_refused(
            lambda docs: self.plan(docs)["successor_draft"].__setitem__(
                "claim_id", "vcl_" + "0" * 64
            )
        )


if __name__ == "__main__":
    unittest.main()
