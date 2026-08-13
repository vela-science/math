#!/usr/bin/env python3
"""Focused refusal tests for the terminal bridge disposition."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
SPEC = importlib.util.spec_from_file_location("bridge_disposition", HERE / "build.py")
assert SPEC and SPEC.loader
BUILD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)
LEAN_PROOFS = Path(os.environ.get("VELA_LEAN_PROOFS_REPO", HERE.parents[4] / "lean-proofs"))
FORMAL = Path(os.environ.get("VELA_FORMAL_CONJECTURES_REPO", HERE.parents[4] / "formal-conjectures"))


class RepairDispositionTest(unittest.TestCase):
    def test_review_method_is_canonical(self):
        for name in (
            "terminal-bridge-scope-review-gpt-5.6-sol.v1.json",
            "terminal-bridge-scope-openai-codex-peer.v1.json",
        ):
            path = REPO / "methods/erdos-321" / name
            raw = path.read_bytes()
            value = json.loads(raw)
            canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
            self.assertEqual(raw, canonical + b"\n")

    def test_independent_review_binds_exact_inputs_and_honest_provenance(self):
        path = HERE / "independent-review.v1.json"
        raw = path.read_bytes()
        review = json.loads(raw)
        canonical = json.dumps(review, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(raw, canonical + b"\n")
        method_path = REPO / review["method"]["path"]
        self.assertEqual(
            review["method"]["raw_sha256"],
            "sha256:" + __import__("hashlib").sha256(method_path.read_bytes()).hexdigest(),
        )
        self.assertEqual(review["outcome"], "pass")
        self.assertTrue(review["independence"]["independent"])
        self.assertIn("agent:codex-terminal-bridge-disposition", review["independence"]["declared_independent_of"])
        self.assertEqual(review["reviewer"]["identifier"], "codex-subagent-unreported-model")
        self.assertIsNone(review["reviewer"]["version"])

    def test_exact_sources_produce_retained_record(self):
        observed = BUILD.build(LEAN_PROOFS.resolve(), FORMAL.resolve())
        retained = json.loads((HERE / "repair-disposition.v1.json").read_text())
        self.assertEqual(observed, retained)
        self.assertEqual(retained["disposition"]["status"], "unsupported_by_retained_basis")
        self.assertEqual(retained["disposition"]["relation_lower"], "unresolved")
        self.assertEqual(retained["disposition"]["relation_upper"], "unresolved")
        self.assertEqual(retained["authority_effect"], "none")

    def test_source_drift_refuses(self):
        with tempfile.TemporaryDirectory() as temporary:
            fake = Path(temporary)
            (fake / ".git").mkdir()
            with self.assertRaises(BUILD.BuildError):
                BUILD.build(fake, FORMAL.resolve())

    def test_claim_is_negative_and_bounded(self):
        retained = json.loads((HERE / "repair-disposition.v1.json").read_text())
        joined = " ".join(retained["does_not_establish"]).lower()
        self.assertIn("no mathematical impossibility", joined)
        self.assertIn("not a vela verification", joined)
        self.assertEqual(len(retained["missing_bridges"]), 4)


if __name__ == "__main__":
    unittest.main()
