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
SPEC = importlib.util.spec_from_file_location("bridge_disposition", HERE / "build.py")
assert SPEC and SPEC.loader
BUILD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)
LEAN_PROOFS = Path(os.environ.get("VELA_LEAN_PROOFS_REPO", HERE.parents[4] / "lean-proofs"))
FORMAL = Path(os.environ.get("VELA_FORMAL_CONJECTURES_REPO", HERE.parents[4] / "formal-conjectures"))


class RepairDispositionTest(unittest.TestCase):
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
