#!/usr/bin/env python3

import copy
import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "verify_execution_binding",
    HERE / "verify_binding.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
# The verifier implementation is part of the immutable historical packet. Test
# it against the retained issued index, not the evolving current offer index.
MODULE.INDEX = MODULE.WORK_OFFERS / "results/erdos-887-pilot-02-current-binding/work-offer-index.v1.json"


class BindingTest(unittest.TestCase):
    def write_json(self, value: dict) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "value.json"
        path.write_bytes(MODULE.canonical(value) + b"\n")
        return path

    def synthetic_current_result(self, binding: dict[str, str]) -> Path:
        source = MODULE.WORK_OFFERS / "results/erdos-887-pilot-02-current-binding"
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        destination = Path(directory.name) / "result"
        shutil.copytree(source, destination, copy_function=shutil.copy2)

        transcript_path = destination / "execution-transcript.v1.json"
        transcript, _ = MODULE.load(transcript_path)
        transcript["execution_binding"] = binding
        transcript["transcript_root"] = MODULE.rooted(transcript, "transcript_root")
        transcript_path.write_bytes(MODULE.canonical(transcript) + b"\n")

        check_path = destination / "lean-check.v1.json"
        check, _ = MODULE.load(check_path)
        check["execution_binding"] = binding
        check["execution_transcript"]["root"] = transcript["transcript_root"]
        check["check_result_root"] = MODULE.rooted(check, "check_result_root")
        check_path.write_bytes(MODULE.canonical(check) + b"\n")

        result_path = destination / "result.v1.json"
        result, _ = MODULE.load(result_path)
        result["packet_root"] = binding["packet_root"]
        result["execution_binding"] = binding
        result["result_status"] = "candidate_ready_for_human_review"
        result["artifacts"]["execution_transcript"]["root"] = transcript["transcript_root"]
        result["artifacts"]["lean_check"]["root"] = check["check_result_root"]
        result["check_result_root"] = check["check_result_root"]
        result["result_root"] = MODULE.rooted(result, "result_root")
        result_path.write_bytes(MODULE.canonical(result) + b"\n")
        return result_path

    def test_frozen_public_binding_verifies(self) -> None:
        binding = MODULE.verify_binding()
        self.assertEqual(binding["schema"], "vela.execution-binding.v1")
        self.assertEqual(len(binding), 5)

    def test_result_artifact_path_allows_nested_and_refuses_escape(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        result_dir = root / "result"
        result_dir.mkdir()
        result_path = result_dir / "result.v1.json"
        result_path.write_text("{}\n")
        nested = result_dir / "public-cache-snapshots"
        nested.mkdir()
        snapshot = nested / "cache.barrel"
        snapshot.write_bytes(b"cache")
        self.assertEqual(
            MODULE.result_artifact_path(result_path, "public-cache-snapshots/cache.barrel"),
            snapshot.resolve(),
        )

        sibling = root / "result-sibling"
        sibling.mkdir()
        (sibling / "cache.barrel").write_bytes(b"cache")
        for locator in ("../result-sibling/cache.barrel", "../outside.barrel"):
            with self.assertRaisesRegex(MODULE.BindingError, "escapes the result directory"):
                MODULE.result_artifact_path(result_path, locator)

        symlink = result_dir / "linked-cache"
        symlink.symlink_to(sibling, target_is_directory=True)
        with self.assertRaisesRegex(MODULE.BindingError, "escapes the result directory"):
            MODULE.result_artifact_path(result_path, "linked-cache/cache.barrel")

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
        with self.assertRaisesRegex(MODULE.BindingError, "missing required fields.*execution_binding"):
            MODULE.verify_result(old_result, binding)

        current_result = self.synthetic_current_result(binding)
        result, _ = MODULE.load(current_result)
        escaping = copy.deepcopy(result)
        escaping["artifacts"]["source_patch"]["path"] = "../private.txt"
        escaping["result_root"] = MODULE.rooted(escaping, "result_root")
        escaping_raw = MODULE.canonical(escaping) + b"\n"
        original_load = MODULE.load

        def escaping_load(path: Path):
            return (escaping, escaping_raw) if path == current_result else original_load(path)

        with patch.object(MODULE, "load", side_effect=escaping_load):
            with self.assertRaisesRegex(MODULE.BindingError, "escapes the result directory"):
                MODULE.verify_result(current_result, binding)

    def test_result_and_check_execution_root_substitutions_refuse(self) -> None:
        binding = MODULE.verify_binding()
        result_path = self.synthetic_current_result(binding)
        result, _ = MODULE.load(result_path)
        original_load = MODULE.load
        for field in ("profile_root", "verifier_capsule_root", "result_contract_root"):
            changed = copy.deepcopy(result)
            changed["execution_binding"][field] = "sha256:" + "0" * 64
            changed["result_root"] = MODULE.rooted(changed, "result_root")
            changed_raw = MODULE.canonical(changed) + b"\n"

            def changed_result_load(path: Path, *, value=changed, raw=changed_raw):
                return (value, raw) if path == result_path else original_load(path)

            with patch.object(MODULE, "load", side_effect=changed_result_load):
                with self.assertRaisesRegex(MODULE.BindingError, "result execution binding drift"):
                    MODULE.verify_result(result_path, binding)

        check_path = (result_path.parent / result["artifacts"]["lean_check"]["path"]).resolve()
        check, _ = MODULE.load(check_path)
        for field in ("profile_root", "verifier_capsule_root", "result_contract_root"):
            changed = copy.deepcopy(check)
            changed["execution_binding"][field] = "sha256:" + "0" * 64
            changed["check_result_root"] = MODULE.rooted(changed, "check_result_root")
            changed_raw = MODULE.canonical(changed) + b"\n"

            def changed_check_load(path: Path, *, value=changed, raw=changed_raw):
                return (value, raw) if path == check_path else original_load(path)

            with patch.object(MODULE, "load", side_effect=changed_check_load):
                with self.assertRaisesRegex(MODULE.BindingError, "Lean check execution binding drift"):
                    MODULE.verify_result(result_path, binding)

    def test_consistent_capture_implementation_substitution_refuses(self) -> None:
        binding = MODULE.verify_binding()
        result_path = self.synthetic_current_result(binding)
        result_dir = result_path.parent
        substituted_root = "sha256:" + "0" * 64

        inventory_path = result_dir / "dependency-inventory.v1.json"
        inventory, _ = MODULE.load(inventory_path)
        inventory["capture"]["script_raw_sha256"] = substituted_root
        inventory["inventory_root"] = MODULE.rooted(inventory, "inventory_root")
        inventory_path.write_bytes(MODULE.canonical(inventory) + b"\n")

        transcript_path = result_dir / "execution-transcript.v1.json"
        transcript, _ = MODULE.load(transcript_path)
        transcript["runner"]["script_raw_sha256"] = substituted_root
        transcript["dependency_inventory"]["root"] = inventory["inventory_root"]
        transcript["transcript_root"] = MODULE.rooted(transcript, "transcript_root")
        transcript_path.write_bytes(MODULE.canonical(transcript) + b"\n")

        check_path = result_dir / "lean-check.v1.json"
        check, _ = MODULE.load(check_path)
        check["dependency_inventory"]["root"] = inventory["inventory_root"]
        check["execution_transcript"]["root"] = transcript["transcript_root"]
        check["check_result_root"] = MODULE.rooted(check, "check_result_root")
        check_path.write_bytes(MODULE.canonical(check) + b"\n")

        result, _ = MODULE.load(result_path)
        result["artifacts"]["dependency_inventory"]["root"] = inventory["inventory_root"]
        result["artifacts"]["execution_transcript"]["root"] = transcript["transcript_root"]
        result["artifacts"]["lean_check"]["root"] = check["check_result_root"]
        result["check_result_root"] = check["check_result_root"]
        result["result_root"] = MODULE.rooted(result, "result_root")
        result_path.write_bytes(MODULE.canonical(result) + b"\n")

        with self.assertRaisesRegex(MODULE.BindingError, "execution capture implementation root drift"):
            MODULE.verify_result(result_path, binding)


if __name__ == "__main__":
    unittest.main()
