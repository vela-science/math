#!/usr/bin/env python3
"""Offline integrity tests for the attributed agent evaluation package."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import unittest


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]


def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_keys)


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def semantic_root(value: dict[str, object], field: str) -> str:
    unrooted = dict(value)
    unrooted.pop(field, None)
    return "sha256:" + hashlib.sha256(canonical_bytes(unrooted)).hexdigest()


class AgentEvaluationTest(unittest.TestCase):
    def test_design_is_separate_and_frozen_before_outcomes(self) -> None:
        design = load_json(HERE / "agent-evaluation-design.v0.1.json")
        self.assertEqual(design["status"], "design_frozen_before_agent_outcomes")
        self.assertIn("does not amend", design["relationship_to_human_design"]["rule"])
        self.assertEqual(design["reviewer_policy"]["actor_class"], "agent")
        self.assertEqual(design["reviewer_policy"]["quality_rule"], "actor class is provenance, not a quality rank")
        self.assertEqual(design["sample"]["sender_observations"], 30)
        self.assertEqual(design["sample"]["receiver_observations"], 30)

    def test_public_sources_match_git_blob_and_manifest_root(self) -> None:
        manifest = load_json(HERE / "public-source-manifest.v0.1.json")
        self.assertEqual(manifest["manifest_root"], semantic_root(manifest, "manifest_root"))
        self.assertEqual(manifest["artifact_count"], 5)
        for artifact in manifest["artifacts"]:
            data = (REPO / artifact["local_path"]).read_bytes()
            framed = f"blob {len(data)}\0".encode() + data
            self.assertEqual(hashlib.sha1(framed, usedforsecurity=False).hexdigest(), artifact["git_blob_sha1"])
            self.assertEqual("sha256:" + hashlib.sha256(data).hexdigest(), artifact["raw_sha256"])
            self.assertEqual(len(data), artifact["size"])

    def test_bundle_set_and_every_bundle_are_rooted(self) -> None:
        bundle_set = load_json(HERE / "condition-bundle-set.v0.1.json")
        self.assertEqual(bundle_set["bundle_set_root"], semantic_root(bundle_set, "bundle_set_root"))
        self.assertEqual(bundle_set["bundle_count"], 10)
        for descriptor in bundle_set["bundles"]:
            path = REPO / descriptor["path"]
            data = path.read_bytes()
            self.assertEqual(len(data), descriptor["size"])
            self.assertEqual("sha256:" + hashlib.sha256(data).hexdigest(), descriptor["raw_sha256"])
            bundle = load_json(path)
            self.assertEqual(bundle["bundle_root"], semantic_root(bundle, "bundle_root"))
            self.assertEqual(bundle["packet_root"], descriptor["packet_root"])
            self.assertEqual(bundle["condition_packet"]["packet_root"], descriptor["packet_root"])

    def test_matched_pairs_differ_only_by_treatment(self) -> None:
        bundle_set = load_json(HERE / "condition-bundle-set.v0.1.json")
        by_fixture: dict[str, list[dict[str, object]]] = {}
        for descriptor in bundle_set["bundles"]:
            by_fixture.setdefault(descriptor["fixture_id"], []).append(load_json(REPO / descriptor["path"]))
        self.assertEqual(len(by_fixture), 5)
        for pair in by_fixture.values():
            self.assertEqual(len(pair), 2)
            control = next(item for item in pair if item["condition"].startswith("plain-"))
            treatment = next(item for item in pair if item["condition"].startswith("same-"))
            self.assertEqual(control["public_source"], treatment["public_source"])
            self.assertEqual(control["shared_evidence"], treatment["shared_evidence"])
            self.assertEqual(control["access_limits"], treatment["access_limits"])
            self.assertEqual(control["treatment_evidence"], [])
            self.assertEqual(len(treatment["treatment_evidence"]), 2)

    def test_counterbalance_has_thirty_balanced_assignments(self) -> None:
        human_design = load_json(REPO / "evidence/formal-conjectures/audit-pilot/precollection-design.v0.1.json")
        fixtures = human_design["fixture_by_condition_allocation"]["fixture_ids"]
        slots = human_design["counterbalance_schedule"]["slots"]
        self.assertEqual(len(slots) * len(fixtures), 30)
        for fixture_index, _fixture in enumerate(fixtures):
            conditions = [slot["conditions"][fixture_index] for slot in slots]
            self.assertEqual(conditions.count("C"), 3)
            self.assertEqual(conditions.count("T"), 3)

    def test_allocation_is_rooted_unique_and_predeclared(self) -> None:
        allocation = load_json(HERE / "agent-allocation.v0.1.json")
        self.assertEqual(allocation["allocation_root"], semantic_root(allocation, "allocation_root"))
        self.assertEqual(allocation["assignment_count"], 30)
        assignments = allocation["assignments"]
        self.assertEqual(len({item["handoff_id"] for item in assignments}), 30)
        self.assertEqual(len({item["sender_task_context_id"] for item in assignments}), 30)
        self.assertEqual(len({item["receiver_task_context_id"] for item in assignments}), 30)
        self.assertEqual({item["slot"] for item in assignments}, set(range(1, 7)))
        for item in assignments:
            data = (REPO / item["bundle"]["path"]).read_bytes()
            self.assertEqual(len(data), item["bundle"]["size"])
            self.assertEqual("sha256:" + hashlib.sha256(data).hexdigest(), item["bundle"]["raw_sha256"])

    def test_bundle_root_refuses_semantic_mutation(self) -> None:
        bundle_set = load_json(HERE / "condition-bundle-set.v0.1.json")
        bundle = load_json(REPO / bundle_set["bundles"][0]["path"])
        original = bundle["bundle_root"]
        mutated = copy.deepcopy(bundle)
        mutated["condition"] = "same-inputs-plus-fc-pr-audit"
        self.assertNotEqual(original, semantic_root(mutated, "bundle_root"))

    def test_output_schemas_enforce_agent_authority_none(self) -> None:
        for name in ["sender-output.schema.v0.1.json", "receiver-output.schema.v0.1.json"]:
            schema = load_json(HERE / name)
            self.assertFalse(schema["additionalProperties"])
            self.assertEqual(schema["properties"]["authority_effect"]["const"], "none")
            self.assertEqual(schema["properties"]["authority_effect"]["type"], "string")
            self.assertEqual(schema["properties"]["schema"]["type"], "string")
            self.assertIn("does_not_establish", schema["required"])

    def test_failed_harness_attempt_is_retained_before_amended_run(self) -> None:
        amendment = load_json(HERE / "execution-amendment.v0.1.json")
        failed = amendment["failed_attempt"]
        data = (REPO / failed["path"]).read_bytes()
        self.assertEqual(len(data), failed["size"])
        self.assertEqual("sha256:" + hashlib.sha256(data).hexdigest(), failed["raw_sha256"])
        result = json.loads(data, object_pairs_hook=reject_duplicate_keys)
        self.assertEqual(result["results_root"], failed["results_root"])
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["sender_H2"]["totals"]["terminal_states"], {"error": 30})
        self.assertEqual(result["receiver_H5"]["totals"]["terminal_states"], {"blocked_sender_failure": 30})
        self.assertEqual(failed["model_review_outputs"], 0)

    def test_completed_observations_and_result_are_exactly_rooted(self) -> None:
        index = load_json(HERE / "agent-observation-index.v0.1.json")
        result = load_json(HERE / "agent-evaluation-results.v0.1.json")
        self.assertEqual(index["index_root"], semantic_root(index, "index_root"))
        self.assertEqual(result["results_root"], semantic_root(result, "results_root"))
        self.assertEqual(index["observation_count"], 60)
        self.assertEqual(len(index["rows"]), 60)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["hypothesis_support"], {"H2": True, "H5": False})
        self.assertEqual(result["interface_disposition"]["value"], "revise")
        self.assertEqual(result["sender_H2"]["totals"]["successful"], 30)
        self.assertEqual(result["receiver_H5"]["totals"]["successful"], 30)
        for descriptor in [
            index["execution_implementation"]["runner"],
            index["execution_implementation"]["sender_output_schema"],
            index["execution_implementation"]["receiver_output_schema"],
            index["execution_implementation"]["amendment"],
            result["analysis_implementation"],
        ]:
            implementation = REPO / descriptor["path"]
            implementation_bytes = implementation.read_bytes()
            self.assertEqual(len(implementation_bytes), descriptor["size"])
            self.assertEqual("sha256:" + hashlib.sha256(implementation_bytes).hexdigest(), descriptor["raw_sha256"])
        for descriptor in index["observations"]:
            path = REPO / descriptor["path"]
            data = path.read_bytes()
            self.assertEqual(len(data), descriptor["size"])
            self.assertEqual("sha256:" + hashlib.sha256(data).hexdigest(), descriptor["raw_sha256"])
            observation = json.loads(data, object_pairs_hook=reject_duplicate_keys)
            self.assertEqual(observation["observation_root"], descriptor["observation_root"])
            self.assertEqual(observation["observation_root"], semantic_root(observation, "observation_root"))
            self.assertEqual(observation["authority_effect"], "none")

    def test_receiver_outputs_bind_exact_sender_outputs(self) -> None:
        allocation = load_json(HERE / "agent-allocation.v0.1.json")
        for assignment in allocation["assignments"]:
            stem = f"slot-{assignment['slot']:02d}--task-{assignment['task_order']:02d}--fixture-{assignment['fixture_position']:02d}"
            sender = load_json(HERE / "runs/sender" / f"{stem}.observation.json")
            receiver = load_json(HERE / "runs/receiver" / f"{stem}.observation.json")
            sender_bytes = (REPO / sender["output"]["path"]).read_bytes()
            receiver_output = load_json(REPO / receiver["output"]["path"])
            self.assertEqual(receiver_output["sender_output_sha256"], "sha256:" + hashlib.sha256(sender_bytes).hexdigest())
            self.assertEqual(sender["task_context_id"], assignment["sender_task_context_id"])
            self.assertEqual(receiver["task_context_id"], assignment["receiver_task_context_id"])
            self.assertNotEqual(sender["task_context_id"], receiver["task_context_id"])

    def test_public_package_contains_no_private_machine_paths(self) -> None:
        prohibited = [b"/Users/williamblair", b"/var/folders/", b"ghp_", b"sk-proj-", b"sk-svcacct-"]
        for path in HERE.rglob("*"):
            if not path.is_file() or path.resolve() == Path(__file__).resolve() or "__pycache__" in path.parts:
                continue
            data = path.read_bytes()
            for pattern in prohibited:
                self.assertNotIn(pattern, data, f"private or secret-looking material in {path}")


if __name__ == "__main__":
    unittest.main()
