#!/usr/bin/env python3

import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
BUILD_SPEC = importlib.util.spec_from_file_location("build_current_result", HERE / "build_result.py")
assert BUILD_SPEC and BUILD_SPEC.loader
BUILD = importlib.util.module_from_spec(BUILD_SPEC)
BUILD_SPEC.loader.exec_module(BUILD)

CAPSULE_PATH = HERE.parents[1] / "execution/erdos-887-pr-1237-fidelity-repair/verify_binding.py"
CAPSULE_SPEC = importlib.util.spec_from_file_location("verify_current_binding", CAPSULE_PATH)
assert CAPSULE_SPEC and CAPSULE_SPEC.loader
CAPSULE = importlib.util.module_from_spec(CAPSULE_SPEC)
CAPSULE_SPEC.loader.exec_module(CAPSULE)
HUMAN_METHOD = BUILD.REPO_ROOT / "methods/erdos-887/statement-fidelity-review.v1.json"
WORK_OFFER_INDEX = HERE.parents[1] / "index.v1.json"


class CurrentResultTest(unittest.TestCase):
    def retained_capsule_binding(self) -> dict[str, str]:
        original_load = CAPSULE.load

        def retained_load(path: Path):
            if path == CAPSULE.PACKET:
                return original_load(BUILD.PACKET)
            if path == CAPSULE.INDEX:
                return original_load(BUILD.INDEX)
            return original_load(path)

        with patch.object(CAPSULE, "load", side_effect=retained_load):
            return CAPSULE.verify_binding()

    def test_frozen_result_matches_current_binding_and_capsule(self) -> None:
        check, check_raw, result, result_raw = BUILD.build()
        self.assertEqual(BUILD.CHECK.read_bytes(), check_raw)
        self.assertEqual(BUILD.RESULT.read_bytes(), result_raw)
        binding = self.retained_capsule_binding()
        self.assertEqual(result["execution_binding"], binding)
        self.assertEqual(result["packet_root"], binding["packet_root"])
        self.assertEqual(CAPSULE.verify_result(BUILD.RESULT, binding), result["result_root"])
        self.assertEqual(check["execution_binding"], binding)
        self.assertEqual(check["exit_code"], 0)

    def test_human_review_method_binds_the_exact_candidate(self) -> None:
        method = json.loads(HUMAN_METHOD.read_text(), object_pairs_hook=BUILD.unique_object)
        _, _, result, _ = BUILD.build()
        self.assertEqual(method["schema"], "vela.verification-method.v1")
        self.assertEqual(
            method["property"],
            "Attributed human statement-fidelity review of the absolute-K answer-slot repair.",
        )
        self.assertEqual(method["inputs"]["base_commit"], result["source_roots"]["base_commit"])
        self.assertEqual(
            method["inputs"]["repaired_content_root"],
            result["source_roots"]["result_content_root"],
        )
        self.assertEqual(method["inputs"]["repair_raw_sha256"], result["source_patch_root"])
        self.assertEqual(method["inputs"]["execution_result_root"], result["result_root"])
        self.assertIn("human", method["environment"]["independence"])
        self.assertIn("Decision", " ".join(method["does_not_establish"]))

    def test_dependency_inventory_and_public_non_authority_recompute(self) -> None:
        check, _, result, _ = BUILD.build()
        inventory = BUILD.load(BUILD.INVENTORY)
        transcript = BUILD.load(BUILD.TRANSCRIPT)
        self.assertEqual(inventory["inventory_root"], BUILD.root(inventory, "inventory_root"))
        self.assertTrue(inventory["all_heads_match_manifest"])
        self.assertFalse(inventory["prerequisite_build_started_from_source_only"])
        self.assertEqual(inventory["compiled_build_directories_before_prerequisite"], [])
        self.assertEqual(inventory["lake_registry_build_barrels_before_prerequisite"], [])
        self.assertEqual(inventory["lake_registry_network_during_replay"], "denied_by_sandbox-exec_and_global_no_cache")
        cache_snapshot = BUILD.load(BUILD.CACHE_SNAPSHOT)
        self.assertEqual(cache_snapshot["cache_snapshot_root"], BUILD.root(cache_snapshot, "cache_snapshot_root"))
        self.assertNotIn(b"/private/", BUILD.CACHE_SNAPSHOT.read_bytes())
        self.assertNotIn(b"/Users/", BUILD.CACHE_SNAPSHOT.read_bytes())
        self.assertEqual(len(inventory["packages"]), 9)
        self.assertTrue(all(
            item["head_matches_manifest"]
            and item["source_worktree_clean"]
            and item["manifest_revision"] == item["actual_head"]
            for item in inventory["packages"]
        ))
        capture = inventory["capture"]
        capture_script = BUILD.REPO_ROOT / capture["script_path"]
        self.assertEqual(capture["script_raw_sha256"], BUILD.raw_root(capture_script.read_bytes()))
        self.assertEqual(transcript["execution_binding"], result["execution_binding"])
        self.assertEqual(transcript["transcript_root"], BUILD.root(transcript, "transcript_root"))
        self.assertNotIn("attempts", check)
        self.assertEqual(check["authority_effect"], "none")
        self.assertEqual(result["authority_effect"], "none")
        self.assertIn("not a Vela Submission, Verification, Decision, Event", " ".join(result["nonclaims"]))

    def test_asserted_or_changed_dependency_head_refuses(self) -> None:
        inventory = BUILD.load(BUILD.INVENTORY)
        changed = copy.deepcopy(inventory)
        changed["packages"][0]["actual_head"] = "0" * 40
        changed["inventory_root"] = BUILD.root(changed, "inventory_root")
        original_load = BUILD.load

        def changed_load(path: Path):
            return changed if path == BUILD.INVENTORY else original_load(path)

        _, binding = BUILD.retained_execution_binding()
        with patch.object(BUILD, "load", side_effect=changed_load):
            with self.assertRaisesRegex(BUILD.ResultBuildError, "dependency source HEAD evidence drift"):
                BUILD.build_check(binding)

    def test_historical_result_remains_distinct(self) -> None:
        historical = BUILD.load(HERE.parent / "erdos-887-pilot-01/result.v1.json")
        _, _, current, _ = BUILD.build()
        self.assertEqual(historical["result_root"], "sha256:dced277f5c00aa37c54f0a56b6952eba349be85980fbf949e0b7552a6f1cfed2")
        self.assertNotEqual(historical["packet_root"], current["packet_root"])
        self.assertNotEqual(historical["result_root"], current["result_root"])

    def test_retained_result_is_valid_and_offer_is_closed_superseded(self) -> None:
        _, retained_binding = BUILD.retained_execution_binding()
        self.assertEqual(
            CAPSULE.verify_result(BUILD.RESULT, retained_binding),
            BUILD.load(BUILD.RESULT)["result_root"],
        )
        index = BUILD.load(WORK_OFFER_INDEX)
        target = index["targets"][0]
        self.assertEqual(target["execution_binding"], retained_binding)
        self.assertEqual(target["presence"], "superseded")
        self.assertIsNone(target["next_command"])
        lifecycle = BUILD.load(BUILD.REPO_ROOT / target["lifecycle"]["path"])
        self.assertEqual(lifecycle["presence"], "superseded")
        self.assertEqual(lifecycle["completion"]["contract_status"], "not_satisfied")
        self.assertEqual(lifecycle["completion"]["closure_status"], "closed_superseded")
        self.assertEqual(lifecycle["decisions"]["scientific"]["status"], "accepted")

    def test_changed_stage_and_retained_manifest_refuse(self) -> None:
        transcript = BUILD.load(BUILD.TRANSCRIPT)
        changed = copy.deepcopy(transcript)
        changed["stages"][0]["exit_code"] = 1
        changed["transcript_root"] = BUILD.root(changed, "transcript_root")
        original_load = BUILD.load

        def changed_load(path: Path):
            return changed if path == BUILD.TRANSCRIPT else original_load(path)

        _, binding = BUILD.retained_execution_binding()
        with patch.object(BUILD, "load", side_effect=changed_load):
            with self.assertRaisesRegex(BUILD.ResultBuildError, "execution transcript stage binding drift"):
                BUILD.build_check(binding)

        with tempfile.TemporaryDirectory() as directory:
            changed_manifest = Path(directory) / "lake-manifest.json"
            changed_manifest.write_bytes(BUILD.RETAINED_MANIFEST.read_bytes() + b" ")
            with patch.object(BUILD, "RETAINED_MANIFEST", changed_manifest):
                with self.assertRaisesRegex(BUILD.ResultBuildError, "retained lake-manifest binding drift"):
                    BUILD.build_check(binding)

    def test_binding_authority_and_human_review_drift_refuse(self) -> None:
        _, binding = BUILD.retained_execution_binding()
        _, _, result, _ = BUILD.build()
        cases = []
        changed = copy.deepcopy(result)
        changed["execution_binding"]["profile_root"] = "sha256:" + "0" * 64
        changed["result_root"] = BUILD.root(changed, "result_root")
        cases.append(changed)
        changed = copy.deepcopy(result)
        changed["authority_effect"] = "standing"
        changed["result_root"] = BUILD.root(changed, "result_root")
        cases.append(changed)
        for changed in cases:
            with self.assertRaisesRegex(BUILD.ResultBuildError, "authority or execution binding drift"):
                BUILD.validate_result(changed, binding)

        changed = copy.deepcopy(result)
        changed["semantic_review"].update({"status": "pass", "reviewer": "ghost", "independent": True})
        changed["result_root"] = BUILD.root(changed, "result_root")
        with self.assertRaisesRegex(BUILD.ResultBuildError, "human-review boundary drift"):
            BUILD.validate_result(changed, binding)

    def test_duplicate_json_keys_refuse(self) -> None:
        with self.assertRaisesRegex(BUILD.ResultBuildError, "duplicate JSON key"):
            json.loads('{"root":1,"root":2}', object_pairs_hook=BUILD.unique_object)


if __name__ == "__main__":
    unittest.main()
