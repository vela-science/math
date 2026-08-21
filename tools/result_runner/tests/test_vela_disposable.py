from __future__ import annotations

import hashlib
import os
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from vela_disposable import record_disposable  # noqa: E402


class DisposableVelaIntegrationTests(unittest.TestCase):
    def test_signed_disposable_lifecycle_rejects_and_deletes_key(self) -> None:
        binary_value = os.environ.get("VELA_TEST_BIN")
        expected_digest = os.environ.get("VELA_TEST_SHA256")
        if not binary_value or not expected_digest:
            self.skipTest(
                "set VELA_TEST_BIN and VELA_TEST_SHA256 for the signed integration test"
            )
        binary = pathlib.Path(binary_value).resolve(strict=True)
        self.assertEqual(
            hashlib.sha256(binary.read_bytes()).hexdigest(), expected_digest
        )
        with tempfile.TemporaryDirectory() as raw:
            root = pathlib.Path(raw)
            result = root / "result.json"
            result.write_bytes(b'{"message":"integration","qualification":"pass"}\n')
            value = record_disposable(
                result=result,
                provenance=b'{"schema":"vela.result-runner.provenance.v1"}\n',
                destination=root / "vela",
                vela_bin=binary,
                expected_vela_sha256=expected_digest,
                method=ROOT / "review-method.json",
            )
            self.assertEqual(value["decision"], "reject")
            self.assertFalse(value["scientific_state_changed"])
            self.assertTrue(value["proposal_id"].startswith("vpr_"))
            self.assertTrue(value["verification_id"].startswith("vvr_"))
            self.assertEqual(value["verification_outcome"], "fail")
            self.assertEqual(value["accepted_claims"], 0)
            self.assertTrue(value["replay_ok"])
            self.assertEqual(len(value["vela_binary_sha256"]), 64)
            self.assertEqual(len(value["method_sha256"]), 64)
            self.assertFalse((root / "vela/private/authority-key").exists())
            self.assertFalse((root / "vela/private/authority-key.pub").exists())


if __name__ == "__main__":
    unittest.main()
