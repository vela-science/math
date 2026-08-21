from __future__ import annotations

import hashlib
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import vela_disposable  # noqa: E402
from runner import CommandResult, RunnerError  # noqa: E402


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
            value = vela_disposable.record_disposable(
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

    def test_setup_failures_delete_every_authority_key_file(self) -> None:
        scenarios = {
            "after_first_key": "after first key",
            "after_second_key": "after second key",
            "during_ssh_add": "during ssh-add",
        }
        for name, message in scenarios.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as raw:
                root = pathlib.Path(raw)
                result = root / "result.json"
                binary = root / "vela"
                result.write_bytes(b'{"qualification":"pass"}\n')
                binary.write_bytes(b"not executed")
                digest = hashlib.sha256(binary.read_bytes()).hexdigest()

                def fake_run(argv: list[str], **kwargs: object) -> CommandResult:
                    del kwargs
                    if argv[:2] == ["ssh-agent", "-a"]:
                        return CommandResult(
                            tuple(argv),
                            0,
                            b"SSH_AUTH_SOCK=/tmp/fixture.sock; export SSH_AUTH_SOCK;\n"
                            b"SSH_AGENT_PID=123; export SSH_AGENT_PID;\n",
                            b"",
                            0.0,
                            "completed",
                        )
                    if argv[0] == "ssh-keygen":
                        key = pathlib.Path(argv[-1])
                        key.write_bytes(b"private fixture")
                        if name == "after_first_key":
                            raise RunnerError("vela_agent", "after first key")
                        key.with_suffix(".pub").write_bytes(b"public fixture")
                        if name == "after_second_key":
                            raise RunnerError("vela_agent", "after second key")
                        return CommandResult(tuple(argv), 0, b"", b"", 0.0, "completed")
                    if argv[0] == "ssh-add" and argv[1] != "-k":
                        raise RunnerError("vela_agent", "during ssh-add")
                    if argv == ["ssh-agent", "-k"]:
                        return CommandResult(tuple(argv), 0, b"", b"", 0.0, "completed")
                    raise AssertionError(f"unexpected command: {argv}")

                destination = root / "vela-output"
                with (
                    mock.patch.object(vela_disposable, "run", fake_run),
                    self.assertRaisesRegex(RunnerError, message),
                ):
                    vela_disposable.record_disposable(
                        result=result,
                        provenance=b"{}\n",
                        destination=destination,
                        vela_bin=binary,
                        expected_vela_sha256=digest,
                        method=ROOT / "review-method.json",
                    )
                self.assertFalse((destination / "private" / "authority-key").exists())
                self.assertFalse(
                    (destination / "private" / "authority-key.pub").exists()
                )


if __name__ == "__main__":
    unittest.main()
