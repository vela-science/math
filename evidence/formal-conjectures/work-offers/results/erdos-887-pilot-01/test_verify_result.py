#!/usr/bin/env python3

import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("verify_result", HERE / "verify_result.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ResultTest(unittest.TestCase):
    def test_frozen_result_verifies(self) -> None:
        result = MODULE.verify()
        packet = MODULE.load(MODULE.PACKET)
        self.assertEqual(result["target_id"], "erdos:887")
        self.assertEqual(result["authority_effect"], "none")
        self.assertEqual(result["semantic_review"]["status"], "pending")
        self.assertEqual(result["packet_root"], packet["packet_root"])
        self.assertNotIn("execution_components", packet)

    def test_historical_packet_drift_refuses(self) -> None:
        changed = copy.deepcopy(MODULE.load(MODULE.PACKET))
        changed["repository"]["repository_root"] = "sha256:" + "0" * 64
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "packet.json"
            path.write_bytes(MODULE.canonical(changed) + b"\n")
            with patch.object(MODULE, "PACKET", path):
                with self.assertRaisesRegex(MODULE.ResultError, "historical Target packet root drift"):
                    MODULE.verify()

    def test_target_or_authority_drift_refuses(self) -> None:
        original = MODULE.load(MODULE.RESULT)
        for field, value in (("target_id", "erdos:888"), ("authority_effect", "standing")):
            changed = copy.deepcopy(original)
            changed[field] = value
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "result.json"
                path.write_bytes(MODULE.canonical(changed) + b"\n")
                with patch.object(MODULE, "RESULT", path):
                    with self.assertRaises(MODULE.ResultError):
                        MODULE.verify()

    def test_false_human_review_claim_refuses(self) -> None:
        changed = copy.deepcopy(MODULE.load(MODULE.RESULT))
        changed["semantic_review"].update({"status": "pass", "reviewer": "ghost", "independent": True})
        changed["result_root"] = MODULE.root(changed, "result_root")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.json"
            path.write_bytes(MODULE.canonical(changed) + b"\n")
            with patch.object(MODULE, "RESULT", path):
                with self.assertRaisesRegex(MODULE.ResultError, "review boundary"):
                    MODULE.verify()


if __name__ == "__main__":
    unittest.main()
