#!/usr/bin/env python3
"""Hostile, offline tests for the Math FC audit source adapter."""

from __future__ import annotations

import copy
import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("math_fc_adapter", HERE / "adapter.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load adapter")
ADAPTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ADAPTER)

REQUIRED_ADAPTER_REQUIREMENTS = set(ADAPTER.CONFORMANCE.REQUIRED_REQUIREMENT_IDS)


class SourceAdapterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.method = ADAPTER.load_method()
        cls.projection = ADAPTER.build_projection()

    def test_exact_projection_rebuilds_and_validates(self) -> None:
        raw, retained = ADAPTER._strict_file(ADAPTER.PROJECTION_PATH, "projection")
        self.assertEqual(raw, ADAPTER.SOURCE.canonical_bytes(self.projection) + b"\n")
        self.assertEqual(retained, self.projection)
        self.assertEqual(ADAPTER.validate_projection(retained), retained)
        self.assertEqual(
            retained["root"]["value"],
            "sha256:1a90cbe1732e21e730753a12e6b3b1ecbd3e0019a287a5ba001c9a9fdccf881b",
        )

    def test_source_inventory_is_complete_and_byte_exact(self) -> None:
        roots = ADAPTER._verify_retained_inventory(self.method)
        self.assertEqual(len(roots), 15)
        self.assertEqual(len(self.projection["records"]), 5)
        self.assertEqual(
            [record["fixture_id"] for record in self.projection["records"]],
            [fixture["id"] for fixture in self.method["fixtures"]],
        )
        for fixture in self.method["fixtures"]:
            record = next(
                item for item in self.projection["records"] if item["fixture_id"] == fixture["id"]
            )
            self.assertEqual(
                record["source_records"]["core"]["file_root"]["value"],
                roots[fixture["core_path"]],
            )
            self.assertEqual(
                record["source_records"]["observation"]["file_root"]["value"],
                roots[fixture["observation_path"]],
            )

    def test_schema_version_refusal_uses_real_source_validators(self) -> None:
        fixture = self.method["fixtures"][0]
        for field, path_key, message in (
            ("formal-conjectures.pr-audit.v2", "core_path", "unsupported core schema"),
            ("formal-conjectures.pr-audit-observation.v2", "observation_path", "unsupported observation schema"),
        ):
            with self.subTest(path_key=path_key), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                shutil.copytree(ADAPTER.RETAINED_ROOT, root, dirs_exist_ok=True)
                path = root / fixture[path_key]
                _, value = ADAPTER._strict_file(path, "mutation source")
                value["schema_version"] = field
                path.write_bytes(ADAPTER.SOURCE.canonical_bytes(value) + b"\n")
                roots = ADAPTER._verify_retained_inventory(self.method)
                roots[fixture[path_key]] = ADAPTER._sha256(path.read_bytes())
                with mock.patch.object(ADAPTER, "RETAINED_ROOT", root):
                    with self.assertRaisesRegex(ADAPTER.AdapterError, message):
                        ADAPTER._build_record(fixture, self.method, roots)

    def test_source_root_and_core_observation_binding_refuse_drift(self) -> None:
        fixture = self.method["fixtures"][0]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(ADAPTER.RETAINED_ROOT, root, dirs_exist_ok=True)
            core_path = root / fixture["core_path"]
            _, core = ADAPTER._strict_file(core_path, "mutated core")
            core["root"] = "sha256:" + "0" * 64
            core_path.write_bytes(ADAPTER.SOURCE.canonical_bytes(core) + b"\n")
            roots = ADAPTER._verify_retained_inventory(self.method)
            roots[fixture["core_path"]] = ADAPTER._sha256(core_path.read_bytes())
            with mock.patch.object(ADAPTER, "RETAINED_ROOT", root):
                with self.assertRaisesRegex(ADAPTER.AdapterError, "core root is invalid"):
                    ADAPTER._build_record(fixture, self.method, roots)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(ADAPTER.RETAINED_ROOT, root, dirs_exist_ok=True)
            observation_path = root / fixture["observation_path"]
            _, observation = ADAPTER._strict_file(observation_path, "mutated observation")
            observation["core"]["root"] = "sha256:" + "1" * 64
            without_root = copy.deepcopy(observation)
            without_root.pop("root")
            observation["root"] = ADAPTER.SOURCE.content_root(without_root)
            observation_path.write_bytes(ADAPTER.SOURCE.canonical_bytes(observation) + b"\n")
            roots = ADAPTER._verify_retained_inventory(self.method)
            roots[fixture["observation_path"]] = ADAPTER._sha256(observation_path.read_bytes())
            with mock.patch.object(ADAPTER, "RETAINED_ROOT", root):
                with self.assertRaisesRegex(ADAPTER.AdapterError, "observation does not bind exact core"):
                    ADAPTER._build_record(fixture, self.method, roots)

    def test_mutable_locator_substitution_is_refused(self) -> None:
        fixture = next(
            item for item in self.method["fixtures"]
            if item["id"] == "conditional-erdos-427-4884"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(ADAPTER.RETAINED_ROOT, root, dirs_exist_ok=True)
            core_path = root / fixture["core_path"]
            _, core = ADAPTER._strict_file(core_path, "mutable-locator mutation")
            core["checks"][0]["proofs"][0]["locator"] = "https://github.com/example/mutable-proof"
            core_path.write_bytes(ADAPTER.SOURCE.canonical_bytes(core) + b"\n")
            roots = ADAPTER._verify_retained_inventory(self.method)
            roots[fixture["core_path"]] = ADAPTER._sha256(core_path.read_bytes())
            with mock.patch.object(ADAPTER, "RETAINED_ROOT", root):
                with self.assertRaisesRegex(ADAPTER.AdapterError, "does not match retained descriptor"):
                    ADAPTER._build_record(fixture, self.method, roots)

    def test_closed_read_refuses_missing_extra_duplicate_and_over_limit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(ADAPTER.RETAINED_ROOT, root, dirs_exist_ok=True)
            (root / "LICENSE").unlink()
            with mock.patch.object(ADAPTER, "RETAINED_ROOT", root):
                with self.assertRaisesRegex(ADAPTER.AdapterError, "directory inventory drift"):
                    ADAPTER._verify_retained_inventory(self.method)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(ADAPTER.RETAINED_ROOT, root, dirs_exist_ok=True)
            (root / "undeclared.txt").write_text("extra\n", encoding="utf-8")
            with mock.patch.object(ADAPTER, "RETAINED_ROOT", root):
                with self.assertRaisesRegex(ADAPTER.AdapterError, "directory inventory drift"):
                    ADAPTER._verify_retained_inventory(self.method)
        duplicate = copy.deepcopy(self.method)
        duplicate["fixtures"][1]["id"] = duplicate["fixtures"][0]["id"]
        with mock.patch.object(ADAPTER, "load_method", return_value=duplicate):
            with mock.patch.object(ADAPTER, "_verify_retained_inventory", return_value={}):
                with self.assertRaisesRegex(ADAPTER.AdapterError, "duplicate fixture"):
                    ADAPTER.build_projection()
        over_limit = copy.deepcopy(self.method)
        over_limit["fixtures"].append(copy.deepcopy(over_limit["fixtures"][0]))
        with mock.patch.object(ADAPTER, "load_method", return_value=over_limit):
            with mock.patch.object(ADAPTER, "_verify_retained_inventory", return_value={}):
                with self.assertRaisesRegex(ADAPTER.AdapterError, "truncated or over bound"):
                    ADAPTER.build_projection()

    def test_root_domains_are_explicit_and_cross_domain_substitution_refuses(self) -> None:
        expected_domains = {
            "projection",
            "source_content",
            "fc_audit_core",
            "fc_audit_observation",
            "artifact",
        }
        seen: set[str] = set()

        def walk(value: object) -> None:
            if isinstance(value, dict):
                if set(value) == {"domain", "value"}:
                    seen.add(value["domain"])
                    ADAPTER._typed_root(value["domain"], value["value"])
                for item in value.values():
                    walk(item)
            elif isinstance(value, list):
                for item in value:
                    walk(item)

        walk(self.projection)
        self.assertEqual(seen, expected_domains)
        mutated = copy.deepcopy(self.projection)
        mutated["records"][0]["source_records"]["core"]["record_root"]["domain"] = "projection"
        mutated["records"][0]["root"] = ADAPTER._record_root(mutated["records"][0])
        mutated["root"] = ADAPTER._record_root(mutated)
        with self.assertRaisesRegex(ADAPTER.AdapterError, "does not match exact retained source"):
            ADAPTER.validate_projection(mutated)
        with self.assertRaisesRegex(ADAPTER.AdapterError, "invalid full SHA-256 root"):
            ADAPTER._typed_root("source_content", "sha256:1234")

    def test_source_revision_custody_interpreter_and_loss_are_explicit(self) -> None:
        source = self.projection["source"]
        self.assertEqual(source["access"], "public")
        self.assertEqual(source["license"], "Apache-2.0")
        self.assertEqual(source["custody"], "copied_exact_bounded_records")
        self.assertRegex(source["commit"], r"^[0-9a-f]{40}$")
        self.assertRegex(source["tree"], r"^[0-9a-f]{40}$")
        self.assertEqual(self.projection["interpreter"]["root"]["domain"], "artifact")
        self.assertEqual(
            self.projection["read_contract"]["mutation_policy"], self.method["mutation_policy"]
        )
        for record in self.projection["records"]:
            self.assertEqual(record["custody"]["mode"], "copied")
            self.assertEqual(record["loss"]["preserves"], self.method["preserves"])
            self.assertEqual(record["loss"]["omits"], self.method["omits"])
            self.assertEqual(
                record["loss"]["unreconstructible_from_projection"],
                self.method["unreconstructible_from_projection"],
            )
        changed = copy.deepcopy(self.projection)
        changed["interpreter"]["root"]["value"] = "sha256:" + "f" * 64
        changed["root"] = ADAPTER._record_root(changed)
        with self.assertRaisesRegex(ADAPTER.AdapterError, "does not match exact retained source"):
            ADAPTER.validate_projection(changed)

    def test_conformance_profile_binds_the_real_adapter_and_projection(self) -> None:
        profile = ADAPTER.load_conformance_profile()
        self.assertEqual(
            profile["adapter"]["implementation_root"],
            ADAPTER._sha256(Path(ADAPTER.__file__).read_bytes()),
        )
        self.assertEqual(profile["authority_effect"], "none")
        self.assertEqual(
            self.projection["conformance"]["profile_root"]["value"],
            profile["profile_root"],
        )
        self.assertEqual(self.projection["conformance"]["authority_effect"], "none")
        drifted = copy.deepcopy(profile)
        drifted["adapter"]["implementation_root"] = "sha256:" + "0" * 64
        drifted["profile_root"] = ADAPTER.CONFORMANCE.profile_root(drifted)
        with mock.patch.object(ADAPTER, "load_conformance_profile", return_value=drifted):
            with self.assertRaisesRegex(ADAPTER.AdapterError, "implementation identity drift"):
                ADAPTER.load_method()

    def test_generated_source_lock_matches_retained_custody(self) -> None:
        _, lock = ADAPTER._strict_file(ADAPTER.REPO_ROOT / "sources.lock.json", "source lock")
        entry = lock["sources"]["formal_conjectures_pr_audit"]
        self.assertEqual(entry["commit"], self.method["source"]["commit"])
        self.assertEqual(entry["tree"], self.method["source"]["tree"])
        self.assertEqual(entry["repo"], "williamjblair/formal-conjectures")
        locked = {
            (item["path"], item["sha256"])
            for item in entry["exact_roots"].values()
        }
        declared = {
            (item["path"], item["sha256"])
            for item in self.method["retained_files"]
        }
        self.assertEqual(locked, declared)
        self.assertTrue(all(item["url"].startswith(
            "https://raw.githubusercontent.com/williamjblair/formal-conjectures/"
            + self.method["source"]["commit"]
        ) for item in entry["exact_roots"].values()))

    def test_no_source_outcome_becomes_verification_or_standing(self) -> None:
        observed_outcomes = set()
        for record in self.projection["records"]:
            self.assertEqual(record["authority_effect"], "none")
            self.assertEqual(record["standing_effect"], "none")
            self.assertIs(record["automatic_verification"], False)
            for check in record["source_axis"]["checks"]:
                observed_outcomes.add(check["outcome"])
                self.assertIs(check["protocol_conversion"]["automatic"], False)
                self.assertIsNone(check["protocol_conversion"]["outcome"])
        self.assertEqual(observed_outcomes, {"pass", "fail", "unavailable"})
        unavailable = next(
            record for record in self.projection["records"]
            if record["fixture_id"] == "unavailable-rupert-3959"
        )
        self.assertIn("unavailable", [check["outcome"] for check in unavailable["source_axis"]["checks"]])
        missing_tool = next(
            check for check in unavailable["source_axis"]["checks"]
            if check["property"] == "comparator-tool-availability"
        )
        self.assertEqual(missing_tool["outcome"], "unavailable")
        self.assertIs(missing_tool["protocol_conversion"]["automatic"], False)
        self.assertIsNone(missing_tool["protocol_conversion"]["outcome"])
        self.assertIn(
            "a source-level clean disposition is a Vela Verification or Standing",
            self.projection["does_not_establish"],
        )

    def test_all_five_source_outcomes_are_lossless_and_nonconverting(self) -> None:
        template = copy.deepcopy(self.projection["records"][0]["source_axis"]["checks"][0])
        native_template = copy.deepcopy(
            ADAPTER.SOURCE.validate_core(
                ADAPTER._strict_file(
                    ADAPTER.RETAINED_ROOT / self.method["fixtures"][0]["core_path"],
                    "source outcome template",
                )[1]
            )["checks"][0]
        )
        for outcome in ("pass", "fail", "inconclusive", "error", "unavailable"):
            with self.subTest(outcome=outcome):
                native = copy.deepcopy(native_template)
                native["outcome"] = outcome
                projected = ADAPTER._project_check(native)
                self.assertEqual(projected["outcome"], outcome)
                self.assertIs(projected["protocol_conversion"]["automatic"], False)
                self.assertIsNone(projected["protocol_conversion"]["outcome"])
        self.assertEqual(template["protocol_conversion"]["outcome"], None)

    def test_real_adapter_covers_every_conformance_requirement(self) -> None:
        coverage = {
            "unsupported_schema_and_version_refusal": {
                "test_schema_version_refusal_uses_real_source_validators",
            },
            "field_and_schema_typed_roots": {
                "test_root_domains_are_explicit_and_cross_domain_substitution_refuses",
            },
            "exact_source_revision_and_drift": {
                "test_mutable_locator_substitution_is_refused",
                "test_source_root_and_core_observation_binding_refuse_drift",
            },
            "complete_bounded_reads": {
                "test_closed_read_refuses_missing_extra_duplicate_and_over_limit",
            },
            "copied_or_referenced_custody": {
                "test_source_revision_custody_interpreter_and_loss_are_explicit",
            },
            "interpreting_implementation_identity": {
                "test_source_revision_custody_interpreter_and_loss_are_explicit",
            },
            "license_access_and_public_redaction": {
                "test_source_revision_custody_interpreter_and_loss_are_explicit",
            },
            "reconstructibility_and_loss": {
                "test_source_revision_custody_interpreter_and_loss_are_explicit",
            },
            "deletion_tombstone_and_mutability": {
                "test_source_revision_custody_interpreter_and_loss_are_explicit",
            },
        }
        self.assertEqual(set(coverage), REQUIRED_ADAPTER_REQUIREMENTS)
        ADAPTER.CONFORMANCE.assert_requirement_coverage(
            ADAPTER.load_conformance_profile(),
            coverage,
        )
        matrix_path = HERE.parent / "conformance/do-not-collapse.v0.1.json"
        _, matrix = ADAPTER._strict_file(matrix_path, "do-not-collapse matrix")
        self.assertEqual(
            set(matrix["acceptance"]["required_adapter_requirement_ids"]),
            set(coverage),
        )


if __name__ == "__main__":
    unittest.main()
