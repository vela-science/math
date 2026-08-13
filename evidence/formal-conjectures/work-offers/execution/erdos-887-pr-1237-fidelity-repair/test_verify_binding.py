#!/usr/bin/env python3

import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("verify_execution_binding", HERE / "verify_binding.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class BindingTest(unittest.TestCase):
    def write_json(self, value: dict) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "value.json"
        path.write_bytes(MODULE.canonical(value) + b"\n")
        return path

    def test_frozen_public_binding_verifies(self) -> None:
        binding = MODULE.verify_binding()
        self.assertEqual(binding["schema"], "vela.execution-binding.v1")
        self.assertEqual(len(binding), 5)

    def test_packet_authority_and_binding_substitution_refuse(self) -> None:
        packet, _ = MODULE.load(MODULE.PACKET)
        changed_packet = copy.deepcopy(packet)
        changed_packet["authority_effect"] = "standing"
        changed_packet["packet_root"] = MODULE.rooted(changed_packet, "packet_root")
        with patch.object(MODULE, "PACKET", self.write_json(changed_packet)):
            with self.assertRaisesRegex(MODULE.BindingError, "claims authority"):
                MODULE.verify_binding()

        index, _ = MODULE.load(MODULE.INDEX)
        changed_index = copy.deepcopy(index)
        changed_index["targets"][0]["execution_binding"]["profile_root"] = "sha256:" + "0" * 64
        changed_index["index_root"] = MODULE.rooted(changed_index, "index_root")
        with patch.object(MODULE, "INDEX", self.write_json(changed_index)):
            with self.assertRaisesRegex(MODULE.BindingError, "execution binding drift"):
                MODULE.verify_binding()

    def test_private_component_and_stale_result_refuse(self) -> None:
        packet, _ = MODULE.load(MODULE.PACKET)
        profile_path = MODULE.REPO_ROOT / packet["execution_components"]["producer_profile"]["path"]
        profile, _ = MODULE.load(profile_path)
        private = copy.deepcopy(profile)
        private["custody"]["access"] = "private"
        private["profile_root"] = MODULE.rooted(private, "profile_root")
        private_raw = MODULE.canonical(private) + b"\n"
        original_load = MODULE.load

        def changed_load(path: Path):
            if path == profile_path:
                return private, private_raw
            return original_load(path)

        with patch.object(MODULE, "load", side_effect=changed_load):
            with self.assertRaisesRegex(MODULE.BindingError, "public custody drift"):
                MODULE.verify_binding()

        binding = MODULE.verify_binding()
        old_result = MODULE.WORK_OFFERS / "results/erdos-887-pilot-01/result.v1.json"
        with self.assertRaisesRegex(MODULE.BindingError, "result packet binding drift"):
            MODULE.verify_result(old_result, binding)

        result, _ = MODULE.load(old_result)
        escaping = copy.deepcopy(result)
        escaping["packet_root"] = binding["packet_root"]
        escaping["artifacts"]["source_patch"]["path"] = "../private.txt"
        escaping["result_root"] = MODULE.rooted(escaping, "result_root")
        with self.assertRaisesRegex(MODULE.BindingError, "escapes the result directory"):
            MODULE.verify_result(self.write_json(escaping), binding)


if __name__ == "__main__":
    unittest.main()
