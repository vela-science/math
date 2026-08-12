#!/usr/bin/env python3
"""Offline integrity and boundary checks for the Phase 0 FC audit packet."""

from __future__ import annotations

import copy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import unittest


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SOURCE_DIR = HERE / "source-snapshots"
SELECTION_PATH = HERE / "phase-0-fixture-selection.v0.1.json"
OBSERVATIONS_PATH = HERE / "phase-0-baseline-observations.v0.1.json"
MANIFEST_PATH = HERE / "phase-0-packet-manifest.v0.1.json"
METHOD_PATH = REPO / "methods/formal-conjectures/audit-baseline.v0.1.json"
EXECUTION_MEMO_SHA256 = (
    "4dfef11f56497fe029204919e810dcfb9d8a9597a767681bd17155c57f1f6fda"
)
def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_json(text: str) -> object:
    return json.loads(text, object_pairs_hook=reject_duplicate_keys)


def load_json(path: Path) -> object:
    return parse_json(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def one_mechanical_observation(fixture: dict[str, object]) -> dict[str, object]:
    observations = [
        item
        for item in fixture["source_observations"]
        if item["kind"] == "github_check_run_observation"
    ]
    if len(observations) != 1:
        raise ValueError("fixture must bind exactly one GitHub Check Run observation")
    return observations[0]


def validate_mechanical_evidence(
    fixture: dict[str, object],
    observation: dict[str, object],
    document: dict[str, object],
    actual_sha256: str,
) -> None:
    pull_request = fixture["pull_request"]
    retained = observation["retained_evidence"]
    if retained["sha256"] != actual_sha256:
        raise ValueError("retained Check Run observation root drift")
    if observation["observed_at"] != document["observed_at"]:
        raise ValueError("Check Run observation time drift")
    if pull_request["number"] != document["pull_request_number"]:
        raise ValueError("Check Run pull-request identity drift")
    if pull_request["head_commit"] != document["head_commit"]:
        raise ValueError("Check Run document head drift")
    if observation["head_commit"] != document["head_commit"]:
        raise ValueError("fixture Check Run head drift")
    if observation["property"] != "exact_head_repository_build_check":
        raise ValueError("mechanical property drift")
    if fixture["expected_checks"]["mechanical_scope"] != observation["property"]:
        raise ValueError("mechanical scope drift")
    if observation["mechanical_result"] != "pass":
        raise ValueError("fixture mechanical result drift")
    claim = document["mechanical_claim"]
    if claim["result"] != "pass":
        raise ValueError("retained mechanical result drift")
    if claim["scope"] != observation["property"]:
        raise ValueError("retained mechanical scope drift")
    if claim["evidence_check_run_ids"] != [retained["check_run_id"]]:
        raise ValueError("referenced Check Run id drift")
    runs = {item["id"]: item for item in document["sources"]["check_runs"]["records"]}
    run = runs.get(retained["check_run_id"])
    if run is None:
        raise ValueError("referenced Check Run is missing")
    if run["head_sha"] != pull_request["head_commit"]:
        raise ValueError("referenced Check Run head drift")
    if run["name"] != "Build project":
        raise ValueError("referenced Check Run property drift")
    if run["status"] != "completed" or run["conclusion"] != "success":
        raise ValueError("referenced Check Run result drift")


def validate_semantic_witness(
    fixture: dict[str, object],
    observation: dict[str, object],
    witness: dict[str, object],
    files_observation: dict[str, object],
    actual_sha256: str,
) -> None:
    pull_request = fixture["pull_request"]
    if observation["sha256"] != actual_sha256:
        raise ValueError("semantic witness root drift")
    if witness["pull_request_number"] != pull_request["number"]:
        raise ValueError("semantic witness pull-request drift")
    if witness["base_commit"] != pull_request["base_commit"]:
        raise ValueError("semantic witness base drift")
    if witness["head_commit"] != pull_request["head_commit"]:
        raise ValueError("semantic witness head drift")
    file_by_path = {item["filename"]: item for item in files_observation["files"]}
    source_file = witness["source_file"]
    file_record = file_by_path.get(source_file["path"])
    if file_record is None:
        raise ValueError("semantic witness path drift")
    if source_file["git_blob_sha"] != file_record["sha"]:
        raise ValueError("semantic witness source blob drift")
    if observation["source_git_blob_sha"] != file_record["sha"]:
        raise ValueError("fixture semantic source blob drift")
    if witness["semantic_fidelity_result"] != "fail":
        raise ValueError("semantic witness result drift")


def validate_packet_relationships(
    selection: dict[str, object],
    method: dict[str, object],
    observations: dict[str, object],
    manifest: dict[str, object],
) -> None:
    components = {item["role"]: item for item in manifest["components"]}
    expected_roles = {"fixture_selection", "evaluation_method", "observation_scaffold"}
    if set(components) != expected_roles:
        raise ValueError("packet component role drift")
    method_selection = method["fixture_selection"]
    if method_selection["path"] != components["fixture_selection"]["path"]:
        raise ValueError("method-to-selection path drift")
    if method_selection["sha256"] != components["fixture_selection"]["sha256"]:
        raise ValueError("method-to-selection root drift")
    if method_selection["required_fixture_count"] != 5:
        raise ValueError("method-to-selection fixture-count drift")
    if set(method_selection["required_roles"]) != {
        fixture["required_role"] for fixture in selection["fixtures"]
    }:
        raise ValueError("method-to-selection role drift")
    if observations["method"] != {
        "path": components["evaluation_method"]["path"],
        "sha256": components["evaluation_method"]["sha256"],
    }:
        raise ValueError("observation-to-method relationship drift")
    if observations["fixture_selection"] != {
        "path": components["fixture_selection"]["path"],
        "sha256": components["fixture_selection"]["sha256"],
    }:
        raise ValueError("observation-to-selection relationship drift")
    if selection["program_contract"]["sha256"] != manifest["program_contract"]["sha256"]:
        raise ValueError("selection-to-program relationship drift")
    if manifest["retained_source_artifacts"] != selection["retained_source_snapshots"]["artifacts"]:
        raise ValueError("manifest-to-source-artifact relationship drift")


def utc_instant(value: str) -> datetime:
    try:
        instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as error:
        raise ValueError("handoff timestamp is not ISO-8601") from error
    if instant.utcoffset() is None:
        raise ValueError("handoff timestamp lacks timezone")
    return instant


def require_fields(record: dict[str, object], required: list[str], label: str) -> None:
    missing = set(required) - set(record)
    if missing:
        raise ValueError(f"{label} fields missing: {sorted(missing)}")


def validate_h5_handoff(
    pair: dict[str, object],
    sender: dict[str, object],
    receiver: dict[str, object],
    declaration: dict[str, object],
) -> None:
    require_fields(pair, declaration["handoff_pair_required_fields"], "handoff pair")
    require_fields(sender, declaration["h5_sender_review_required_fields"], "sender review")
    require_fields(
        receiver,
        declaration["receiver_continuation_observation_required_fields"],
        "receiver continuation",
    )
    if pair["source_review_observation_id"] != sender["observation_id"]:
        raise ValueError("handoff source observation id drift")
    if pair["receiver_continuation_observation_id"] != receiver["observation_id"]:
        raise ValueError("handoff receiver observation id drift")
    if sender["observation_id"] == receiver["observation_id"]:
        raise ValueError("sender and receiver observation ids must differ")
    for field in ["handoff_id", "fixture_id", "condition", "condition_packet_root"]:
        if not (pair[field] == sender[field] == receiver[field]):
            raise ValueError(f"handoff cross-record {field} drift")
    if re.fullmatch(r"sha256:[0-9a-f]{64}", str(pair["condition_packet_root"])) is None:
        raise ValueError("handoff condition packet root is not typed")
    if pair["sender_participant_id_pseudonym"] != sender["participant_id_pseudonym"]:
        raise ValueError("handoff sender pseudonym drift")
    if pair["receiver_participant_id_pseudonym"] != receiver["participant_id_pseudonym"]:
        raise ValueError("handoff receiver pseudonym drift")
    if pair["sender_participant_id_pseudonym"] == pair["receiver_participant_id_pseudonym"]:
        raise ValueError("H5 requires a distinct second participant")
    receiver_copies = {
        "receiver_role": "role",
        "receiver_formal_conjectures_experience": "formal_conjectures_experience",
        "receiver_lean_experience": "lean_experience",
        "receiver_prior_fixture_exposure": "prior_fixture_exposure",
        "receiver_condition_order": "condition_order",
        "receiver_operator_overlap": "operator_overlap",
        "receiver_access_limits": "access_limits",
        "receiver_prepared_fixture_or_audit": "prepared_fixture_or_audit",
        "receiver_used_only_condition_packet": "used_only_condition_packet",
        "independence_classification": "independence_classification",
        "independence_basis": "independence_basis",
    }
    for pair_field, receiver_field in receiver_copies.items():
        if pair[pair_field] != receiver[receiver_field]:
            raise ValueError(f"handoff receiver context drift: {pair_field}")
    timestamp_copies = {
        "sender_completed_at": sender["completed_at"],
        "receiver_started_at": receiver["started_at"],
        "receiver_completed_at": receiver["completed_at"],
    }
    for field, value in timestamp_copies.items():
        if pair[field] != value:
            raise ValueError(f"handoff timestamp copy drift: {field}")
    sender_started = utc_instant(sender["started_at"])
    sender_completed = utc_instant(sender["completed_at"])
    receiver_started = utc_instant(receiver["started_at"])
    receiver_completed = utc_instant(receiver["completed_at"])
    if not sender_started <= sender_completed <= receiver_started <= receiver_completed:
        raise ValueError("handoff timestamp ordering drift")
    if not receiver["used_only_condition_packet"]:
        raise ValueError("receiver used private operator context")
    if receiver["independence_classification"] != "independent":
        raise ValueError("H5 independent handoff basis not established")
    if not receiver["independence_basis"]:
        raise ValueError("receiver independence cannot be inferred")
    if receiver["prepared_fixture_or_audit"]:
        raise ValueError("receiver prepared fixture or audit")


class PhaseZeroPacketTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.selection = load_json(SELECTION_PATH)
        cls.observations = load_json(OBSERVATIONS_PATH)
        cls.manifest = load_json(MANIFEST_PATH)
        cls.method = load_json(METHOD_PATH)

    def test_json_parser_rejects_duplicate_keys(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            parse_json('{"result": "pass", "result": "fail"}')
        for path in [SELECTION_PATH, OBSERVATIONS_PATH, MANIFEST_PATH, METHOD_PATH, *SOURCE_DIR.glob("*.json")]:
            with self.subTest(path=path):
                load_json(path)

    def test_five_selected_roles_include_explicit_unfulfilled_clean_target(self) -> None:
        required_ids = {
            "clean-candidate-dean-4878",
            "conditional-erdos-427-4884",
            "fidelity-erdos-887-1237",
            "vacuity-erdos-80-4830",
            "unavailable-rupert-3959",
        }
        selected_roles = {
            "clean_control_candidate_pending_review",
            "conditional_proof",
            "mechanical_pass_semantic_fail",
            "vacuous_or_boundary_defect",
            "unavailable_tool_or_missing_artifact",
        }
        fixtures = self.selection["fixtures"]
        self.assertEqual(required_ids, {fixture["id"] for fixture in fixtures})
        self.assertEqual(selected_roles, {fixture["required_role"] for fixture in fixtures})
        self.assertEqual(5, self.selection["completion_state"]["selected_case_count"])
        self.assertEqual(4, self.selection["completion_state"]["frozen_source_grounded_fixture_count"])
        self.assertEqual("clean_source_faithful", self.selection["completion_state"]["unfulfilled_target_role"])
        self.assertFalse(self.selection["completion_state"]["fc_03_exit_met"])

    def test_snapshots_match_frozen_pull_request_identities(self) -> None:
        for fixture in self.selection["fixtures"]:
            pull_request = fixture["pull_request"]
            snapshot = load_json(SOURCE_DIR / f"github-pr-{pull_request['number']}.json")
            self.assertEqual(pull_request["number"], snapshot["number"])
            self.assertEqual(pull_request["base_commit"], snapshot["base"]["sha"])
            self.assertEqual(pull_request["head_commit"], snapshot["head"]["sha"])

    def test_changed_paths_match_retained_pr_files_observations(self) -> None:
        retained_roots = {
            item["path"]: item["sha256"]
            for item in self.selection["retained_source_snapshots"]["artifacts"]
        }
        for fixture in self.selection["fixtures"]:
            with self.subTest(fixture=fixture["id"]):
                pull_request = fixture["pull_request"]
                retained = pull_request["files_observation"]
                path = REPO / retained["path"]
                document = load_json(path)
                self.assertEqual(retained["sha256"], sha256_file(path))
                self.assertEqual(retained["sha256"], retained_roots[retained["path"]])
                self.assertEqual(pull_request["number"], document["pull_request_number"])
                self.assertEqual(pull_request["head_commit"], document["expected_head_commit"])
                self.assertEqual(pull_request["changed_paths"], [item["filename"] for item in document["files"]])
                self.assertTrue(all(item["sha"] for item in document["files"]))

    def test_retained_snapshot_roots_and_inventory_are_exact(self) -> None:
        artifacts = self.selection["retained_source_snapshots"]["artifacts"]
        declared_paths = {item["path"] for item in artifacts}
        actual_paths = {str(path.relative_to(REPO)) for path in SOURCE_DIR.glob("*.json")}
        self.assertEqual(declared_paths, actual_paths)
        self.assertEqual(len(artifacts), len(declared_paths))
        for artifact in artifacts:
            path = REPO / artifact["path"]
            self.assertEqual(artifact["sha256"], sha256_file(path), path)

    def test_every_mechanical_pass_binds_exact_head_primary_evidence(self) -> None:
        retained_roots = {
            item["path"]: item["sha256"]
            for item in self.selection["retained_source_snapshots"]["artifacts"]
        }
        for fixture in self.selection["fixtures"]:
            with self.subTest(fixture=fixture["id"]):
                observation = one_mechanical_observation(fixture)
                retained = observation["retained_evidence"]
                path = REPO / retained["path"]
                document = load_json(path)
                self.assertEqual(retained["sha256"], retained_roots[retained["path"]])
                validate_mechanical_evidence(fixture, observation, document, sha256_file(path))
                self.assertTrue(document["sources"]["check_runs"]["endpoint"].endswith(
                    f"/{fixture['pull_request']['head_commit']}/check-runs?per_page=100"
                ))
                self.assertEqual("2022-11-28", document["normalization"]["api_version"])

    def test_wrong_check_head_result_and_root_are_falsified(self) -> None:
        fixture = self.selection["fixtures"][0]
        observation = one_mechanical_observation(fixture)
        path = REPO / observation["retained_evidence"]["path"]
        document = load_json(path)
        actual_root = sha256_file(path)
        check_id = observation["retained_evidence"]["check_run_id"]

        wrong_head = copy.deepcopy(document)
        next(item for item in wrong_head["sources"]["check_runs"]["records"] if item["id"] == check_id)["head_sha"] = "0" * 40
        with self.assertRaisesRegex(ValueError, "Check Run head drift"):
            validate_mechanical_evidence(fixture, observation, wrong_head, actual_root)

        wrong_result = copy.deepcopy(document)
        wrong_result["mechanical_claim"]["result"] = "fail"
        with self.assertRaisesRegex(ValueError, "mechanical result drift"):
            validate_mechanical_evidence(fixture, observation, wrong_result, actual_root)

        wrong_root = copy.deepcopy(observation)
        wrong_root["retained_evidence"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "root drift"):
            validate_mechanical_evidence(fixture, wrong_root, document, actual_root)

    def test_semantic_failures_bind_exact_fixture_head_source_blobs(self) -> None:
        fixtures = {fixture["id"]: fixture for fixture in self.selection["fixtures"]}
        for fixture_id in ["fidelity-erdos-887-1237", "vacuity-erdos-80-4830"]:
            with self.subTest(fixture=fixture_id):
                fixture = fixtures[fixture_id]
                observations = [item for item in fixture["source_observations"] if item["kind"] == "exact_head_semantic_fidelity_witness"]
                self.assertEqual(1, len(observations))
                observation = observations[0]
                witness_path = REPO / observation["path"]
                witness = load_json(witness_path)
                files_document = load_json(REPO / fixture["pull_request"]["files_observation"]["path"])
                validate_semantic_witness(fixture, observation, witness, files_document, sha256_file(witness_path))

                wrong_head = copy.deepcopy(witness)
                wrong_head["head_commit"] = "0" * 40
                with self.assertRaisesRegex(ValueError, "semantic witness head drift"):
                    validate_semantic_witness(fixture, observation, wrong_head, files_document, sha256_file(witness_path))

        packet_text = SELECTION_PATH.read_text(encoding="utf-8")
        self.assertNotIn("fidelity-erdos-522-351", packet_text)
        self.assertNotIn("5cbe3d57171b0a9f733e5052e041ee40c1e98fac", packet_text)
        self.assertNotIn("59f30aa314ba225fcd9268723ce8291616df1ab0", packet_text)

    def test_unavailable_fixture_is_narrow_exact_artifact_identity_claim(self) -> None:
        fixture = next(item for item in self.selection["fixtures"] if item["id"] == "unavailable-rupert-3959")
        expected = fixture["expected_checks"]
        self.assertEqual("unavailable_exact_file_and_revision_at_fixture_head", expected["formal_proof_artifact_resolution"])
        self.assertNotEqual("fail", expected["formal_proof_artifact_resolution"])
        artifact_ref = next(item for item in fixture["source_observations"] if item["kind"] == "exact_head_formal_proof_artifact_observation")
        artifact = load_json(REPO / artifact_ref["path"])
        self.assertEqual(fixture["pull_request"]["head_commit"], artifact["head_commit"])
        self.assertEqual("mutable_repository_root_without_file_or_revision", artifact["locator_class"])
        self.assertEqual("48c343f0d12c1dffb7953a5d2426e0d13a914bad", artifact["source_file"]["git_blob_sha"])
        correction = load_json(SOURCE_DIR / "github-pr-4895-correction-observation.json")
        self.assertEqual("de55e8708b89b2cb5c3d8a910169bf3e71fc3ac0", correction["pull_request"]["head_commit"])
        self.assertIn("/blob/1ee88118097acc9db768b44b3c6ea9f60a4e4b67/", correction["affected_file"]["pinned_locator"])
        self.assertFalse(correction["pull_request"]["merged"])

    def test_rejected_candidate_regressions_are_truthful(self) -> None:
        guard = load_json(SOURCE_DIR / "rejected-candidate-classification-observation.json")
        candidates = {item["candidate"]: item for item in guard["candidates"]}
        erdos_38 = candidates["formal-conjectures-pr-3941-erdos-38"]
        self.assertEqual("resolvable_to_immutable_raw_gist_proof_bytes", erdos_38["resolution"])
        self.assertEqual(200, erdos_38["observed_http_status"])
        self.assertIn("/raw/481e3c35de8dce7af70ec440e4e121f084a61860/Erdos38.lean", erdos_38["immutable_proof_url"])
        in_source = candidates["formal-conjectures-pr-4883-erdos-316-and-399"]
        self.assertEqual("intentional_in_source_proof_semantics_not_missing_artifact", in_source["resolution"])
        self.assertEqual(2, len(in_source["exact_source_observations"]))
        selection_text = SELECTION_PATH.read_text(encoding="utf-8")
        self.assertNotIn("unavailable-erdos-38-3941", selection_text)

    def test_packet_manifest_binds_components_and_relationships(self) -> None:
        validate_packet_relationships(self.selection, self.method, self.observations, self.manifest)
        for component in self.manifest["components"]:
            self.assertEqual(component["sha256"], sha256_file(REPO / component["path"]))

    def test_packet_relation_drift_is_falsified(self) -> None:
        wrong_method = copy.deepcopy(self.method)
        wrong_method["fixture_selection"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "method-to-selection root drift"):
            validate_packet_relationships(self.selection, wrong_method, self.observations, self.manifest)

        wrong_observations = copy.deepcopy(self.observations)
        wrong_observations["method"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "observation-to-method relationship drift"):
            validate_packet_relationships(self.selection, self.method, wrong_observations, self.manifest)

        wrong_selection = copy.deepcopy(self.selection)
        wrong_selection["program_contract"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "selection-to-program relationship drift"):
            validate_packet_relationships(wrong_selection, self.method, self.observations, self.manifest)

    def test_program_contract_binds_final_reviewed_memo_root(self) -> None:
        self.assertEqual(EXECUTION_MEMO_SHA256, self.selection["program_contract"]["sha256"])
        self.assertEqual(EXECUTION_MEMO_SHA256, self.manifest["program_contract"]["sha256"])
        self.assertEqual(["FC-03", "EVAL-01"], self.selection["program_contract"]["work_packages"])

    def test_authority_and_failure_axes_remain_separate(self) -> None:
        fixtures = {fixture["id"]: fixture for fixture in self.selection["fixtures"]}
        clean = fixtures["clean-candidate-dean-4878"]
        self.assertEqual("clean_control_candidate_pending_review", clean["required_role"])
        self.assertEqual("pending_human_ground_truth", clean["expected_checks"]["semantic_fidelity"])
        conditional = fixtures["conditional-erdos-427-4884"]["expected_checks"]
        self.assertEqual("conditional_pass", conditional["proof_artifact"])
        self.assertEqual("erdos_427.variants.shiu", conditional["required_condition"])
        fidelity = fixtures["fidelity-erdos-887-1237"]["expected_checks"]
        self.assertEqual("pass", fidelity["mechanical"])
        self.assertEqual("fail", fidelity["semantic_fidelity"])
        self.assertEqual("none", self.selection["authority_effect"])
        self.assertEqual("none", self.method["authority_effect"])
        self.assertEqual("none", self.observations["authority_effect"])
        ground_truth = self.method["ground_truth"]
        self.assertIn("advisory observation by default", ground_truth["ai_review"])
        self.assertIn("never mints a Vela Verification", ground_truth["ai_review"])
        self.assertIn("external observation for Math", ground_truth["community"])
        self.assertIn("authorized human Math Repository Decision", ground_truth["vela"])

    def test_semantic_witnesses_separate_ai_preparation_from_human_basis(self) -> None:
        for name in ["github-pr-1237-fidelity-witness.json", "github-pr-4830-fidelity-witness.json"]:
            with self.subTest(name=name):
                witness = load_json(SOURCE_DIR / name)
                provenance = witness["provenance"]
                self.assertIn("Codex AI agent", provenance["record_preparer"])
                self.assertEqual("advisory_record_preparation_only", provenance["preparer_authority"])
                self.assertTrue(provenance["human_source_local_basis"])
                self.assertTrue(provenance["exact_head_application"])
                self.assertEqual("none", provenance["authority_effect"])
                limits = " ".join(witness["limitations"])
                self.assertIn("AI packet preparation does not itself supply human ground truth", limits)
                self.assertIn("Math Repository Decision", limits)

    def test_hypothesis_plan_and_phase_scope_are_explicitly_incomplete(self) -> None:
        hypotheses = self.method["hypothesis_plan"]
        self.assertEqual("planned_not_fully_preregistered", hypotheses["registration_status"])
        self.assertEqual({"H2_verification_efficiency", "H5_retained_packet_handoff"}, {item["id"] for item in hypotheses["primary_phase_0"]})
        self.assertEqual({"H1_promotion", "H3_correction_propagation", "H6_portability"}, {item["id"] for item in hypotheses["later_integrated_pilot"]})
        self.assertEqual({"not_tested"}, {item["phase_0_status"] for item in hypotheses["later_integrated_pilot"]})

    def test_precollection_design_gate_blocks_inference(self) -> None:
        gate = self.method["precollection_design_gate"]
        self.assertEqual("incomplete_blocking_inference", gate["status"])
        self.assertEqual(
            {
                "target_sample_and_recruitment_frame",
                "participant_and_session_eligibility",
                "exclusion_and_missing-session_rules",
                "fixture_by_condition_allocation",
                "counterbalance_schedule",
                "stopping_rule",
                "primary_estimands",
                "estimator_and_uncertainty_method",
                "claim_thresholds_and_multiplicity_rule",
                "deviation_and_amendment_policy",
            },
            set(gate["required_rooted_supplement_fields"]),
        )
        self.assertIn("do not claim H2 or H5 support", gate["claim_rule"])
        self.assertEqual("blocked_protocol_design_incomplete", self.observations["collection_status"])
        self.assertIn("No H2 or H5 support", " ".join(self.observations["limits"]))

    def test_h5_requires_linked_distinct_receiver_and_explicit_independence(self) -> None:
        required_shape = self.observations["required_result_shape"]
        declaration = self.method["participant_declaration"]
        for field in [
            "review_observation_required_fields",
            "h5_sender_review_required_fields",
            "receiver_continuation_observation_required_fields",
            "handoff_pair_required_fields",
        ]:
            self.assertEqual(declaration[field], required_shape[field])
        sender = {
            "observation_id": "review-1",
            "handoff_id": "handoff-random-1",
            "fixture_id": "fidelity-erdos-887-1237",
            "condition": "plain-git-and-current-review-artifacts",
            "condition_packet_root": "sha256:" + "a" * 64,
            "participant_id_pseudonym": "p-random-a",
            "started_at": "2026-08-12T19:50:00Z",
            "completed_at": "2026-08-12T20:00:00Z",
            "role": "reviewer_and_sender",
            "formal_conjectures_experience": "declared",
            "lean_experience": "declared",
            "prior_fixture_exposure": "prepared_fixture",
            "condition_order": 1,
            "operator_overlap": "prepared_fixture",
            "access_limits": "matched condition packet",
            "prepared_fixture_or_audit": True,
        }
        receiver = {
            "observation_id": "continuation-1",
            "handoff_id": "handoff-random-1",
            "fixture_id": "fidelity-erdos-887-1237",
            "condition": "plain-git-and-current-review-artifacts",
            "condition_packet_root": "sha256:" + "a" * 64,
            "participant_id_pseudonym": "p-random-b",
            "started_at": "2026-08-12T20:01:00Z",
            "completed_at": "2026-08-12T20:10:00Z",
            "role": "receiver_reviewer",
            "formal_conjectures_experience": "declared",
            "lean_experience": "declared",
            "prior_fixture_exposure": "none",
            "condition_order": 1,
            "operator_overlap": "none",
            "access_limits": "rooted public condition packet only",
            "prepared_fixture_or_audit": False,
            "used_only_condition_packet": True,
            "independence_classification": "independent",
            "independence_basis": "Receiver did not prepare the fixture, audit, or source review and used only the rooted packet.",
        }
        pair = {
            "handoff_id": "handoff-random-1",
            "fixture_id": "fidelity-erdos-887-1237",
            "condition": "plain-git-and-current-review-artifacts",
            "condition_packet_root": "sha256:" + "a" * 64,
            "source_review_observation_id": "review-1",
            "receiver_continuation_observation_id": "continuation-1",
            "sender_participant_id_pseudonym": "p-random-a",
            "receiver_participant_id_pseudonym": "p-random-b",
            "receiver_role": "receiver_reviewer",
            "receiver_formal_conjectures_experience": "declared",
            "receiver_lean_experience": "declared",
            "receiver_prior_fixture_exposure": "none",
            "receiver_condition_order": 1,
            "receiver_operator_overlap": "none",
            "receiver_access_limits": "rooted public condition packet only",
            "receiver_prepared_fixture_or_audit": False,
            "receiver_used_only_condition_packet": True,
            "independence_classification": "independent",
            "independence_basis": "Receiver did not prepare the fixture, audit, or source review and used only the rooted packet.",
            "sender_completed_at": "2026-08-12T20:00:00Z",
            "receiver_started_at": "2026-08-12T20:01:00Z",
            "receiver_completed_at": "2026-08-12T20:10:00Z",
        }
        validate_h5_handoff(pair, sender, receiver, declaration)

        missing_receiver_role = copy.deepcopy(pair)
        missing_receiver_role.pop("receiver_role")
        with self.assertRaisesRegex(ValueError, "handoff pair fields missing"):
            validate_h5_handoff(missing_receiver_role, sender, receiver, declaration)

        same_participant = copy.deepcopy(pair)
        same_participant["receiver_participant_id_pseudonym"] = same_participant["sender_participant_id_pseudonym"]
        same_participant_receiver = copy.deepcopy(receiver)
        same_participant_receiver["participant_id_pseudonym"] = same_participant["sender_participant_id_pseudonym"]
        with self.assertRaisesRegex(ValueError, "distinct second participant"):
            validate_h5_handoff(same_participant, sender, same_participant_receiver, declaration)

        same_observation = copy.deepcopy(pair)
        same_observation["receiver_continuation_observation_id"] = "review-1"
        same_receiver_observation = copy.deepcopy(receiver)
        same_receiver_observation["observation_id"] = "review-1"
        with self.assertRaisesRegex(ValueError, "observation ids must differ"):
            validate_h5_handoff(same_observation, sender, same_receiver_observation, declaration)

        wrong_receiver_id = copy.deepcopy(pair)
        wrong_receiver_id["receiver_continuation_observation_id"] = "missing-continuation"
        with self.assertRaisesRegex(ValueError, "receiver observation id drift"):
            validate_h5_handoff(wrong_receiver_id, sender, receiver, declaration)

        wrong_fixture = copy.deepcopy(receiver)
        wrong_fixture["fixture_id"] = "different-fixture"
        with self.assertRaisesRegex(ValueError, "fixture_id drift"):
            validate_h5_handoff(pair, sender, wrong_fixture, declaration)

        for field, value in [
            ("condition", "different-condition"),
            ("condition_packet_root", "sha256:" + "b" * 64),
        ]:
            wrong_receiver_identity = copy.deepcopy(receiver)
            wrong_receiver_identity[field] = value
            with self.assertRaisesRegex(ValueError, f"{field} drift"):
                validate_h5_handoff(pair, sender, wrong_receiver_identity, declaration)

        malformed_root_pair = copy.deepcopy(pair)
        malformed_root_sender = copy.deepcopy(sender)
        malformed_root_receiver = copy.deepcopy(receiver)
        for record in [malformed_root_pair, malformed_root_sender, malformed_root_receiver]:
            record["condition_packet_root"] = "sha256:not-a-digest"
        with self.assertRaisesRegex(ValueError, "root is not typed"):
            validate_h5_handoff(malformed_root_pair, malformed_root_sender, malformed_root_receiver, declaration)

        wrong_receiver_pseudonym = copy.deepcopy(receiver)
        wrong_receiver_pseudonym["participant_id_pseudonym"] = "p-random-c"
        with self.assertRaisesRegex(ValueError, "receiver pseudonym drift"):
            validate_h5_handoff(pair, sender, wrong_receiver_pseudonym, declaration)

        wrong_context = copy.deepcopy(receiver)
        wrong_context["lean_experience"] = "different"
        with self.assertRaisesRegex(ValueError, "receiver context drift"):
            validate_h5_handoff(pair, sender, wrong_context, declaration)

        wrong_order = copy.deepcopy(receiver)
        wrong_order["started_at"] = "2026-08-12T19:59:00Z"
        wrong_order_pair = copy.deepcopy(pair)
        wrong_order_pair["receiver_started_at"] = wrong_order["started_at"]
        with self.assertRaisesRegex(ValueError, "timestamp ordering drift"):
            validate_h5_handoff(wrong_order_pair, sender, wrong_order, declaration)

        no_basis = copy.deepcopy(receiver)
        no_basis["independence_basis"] = ""
        no_basis_pair = copy.deepcopy(pair)
        no_basis_pair["independence_basis"] = ""
        with self.assertRaisesRegex(ValueError, "cannot be inferred"):
            validate_h5_handoff(no_basis_pair, sender, no_basis, declaration)

    def test_participant_data_boundary_is_explicit(self) -> None:
        policy = self.method["participant_data_handling"]
        self.assertIn("not derived", policy["pseudonym_policy"])
        self.assertIn("outside Git", policy["private_raw_custody"])
        self.assertIn("Delete private raw material", policy["retention_and_deletion"])
        self.assertIn("aggregates", policy["public_release"])
        prohibitions = " ".join(policy["public_packet_prohibitions"])
        for word in ["names", "email", "private pull-request comments", "credentials"]:
            self.assertIn(word, prohibitions)
        public_rule = self.observations["public_data_rule"]
        for word in ["pseudonyms", "names", "emails", "credentials", "private raw data"]:
            self.assertIn(word, public_rule)

    def test_memo_delta_measures_and_kill_criteria_are_retained(self) -> None:
        measure_ids = {item["id"] for item in self.method["measures"]}
        self.assertTrue({
            "reviewer_minutes_per_consequential_issue",
            "metadata_burden_seconds",
            "participant_abandonment",
            "unsupported_claims_reaching_expert_review",
            "affected_descendants_reassessed_fraction",
            "correction_false_alarm_count",
            "manual_semantic_repair_seconds",
            "manual_semantic_repair_count",
        } <= measure_ids)
        self.assertEqual({"continue", "revise", "retain_source_locally", "retire"}, set(self.method["interface_disposition"]["allowed"]))
        self.assertEqual({
            "hides_or_collapses_known_result",
            "burden_without_scientific_benefit",
            "unsupported_claim_triage_failure",
            "manual_semantic_repair",
            "metadata_abandonment_or_bypass",
            "semantic_or_authority_loss",
            "simpler_transport_performs_as_well",
        }, {item["id"] for item in self.method["kill_criteria"]})

    def test_results_are_not_fabricated(self) -> None:
        self.assertEqual("blocked_protocol_design_incomplete", self.observations["collection_status"])
        self.assertEqual([], self.observations["review_observations"])
        self.assertEqual([], self.observations["receiver_continuation_observations"])
        self.assertEqual([], self.observations["handoff_pairs"])
        self.assertEqual({"blocked_pending_rooted_precollection_design_supplement"}, {stage["status"] for stage in self.method["collection_stages"]})


if __name__ == "__main__":
    unittest.main()
