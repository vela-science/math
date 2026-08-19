import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("far_probxiv_evaluate", BASE / "evaluate.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class EvaluationTests(unittest.TestCase):
    def fixture(self):
        return MODULE.load_inputs(BASE)

    def copied(self, values):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        for name, value in values.items():
            (root / name).write_text(json.dumps(value))
        # Local evidence locators resolve against the evaluation directory, so
        # mutation tests replace them with a stable public locator.
        for row in values["comparison.json"]["systems"]["vela_math_repository"]:
            row["evidence"] = ["https://github.com/vela-science/math"]
        (root / "comparison.json").write_text(json.dumps(values["comparison.json"]))
        return temp, root

    def test_frozen_inputs_and_committed_report(self):
        result = MODULE.verify_files(BASE)
        self.assertEqual(5, len(result["values"]["candidates.json"]["candidates"]))
        expected = json.loads((BASE / "report.json").read_text())
        self.assertEqual(expected, MODULE.build_report(BASE))

    def test_external_authority_effect_is_rejected(self):
        values = copy.deepcopy(self.fixture())
        values["candidates.json"]["candidates"][0]["vela_mapping"]["authority_effect"] = "standing"
        temp, root = self.copied(values)
        self.addCleanup(temp.cleanup)
        with self.assertRaisesRegex(MODULE.InvalidComparison, "authority drift"):
            MODULE.verify_files(root)

    def test_external_body_copy_is_rejected(self):
        values = copy.deepcopy(self.fixture())
        values["candidates.json"]["candidates"][0]["proof_text"] = "forbidden"
        temp, root = self.copied(values)
        self.addCleanup(temp.cleanup)
        with self.assertRaisesRegex(MODULE.InvalidComparison, "body field forbidden"):
            MODULE.verify_files(root)

    def test_oversized_external_copy_under_arbitrary_key_is_rejected(self):
        values = copy.deepcopy(self.fixture())
        values["candidates.json"]["candidates"][0]["external_copy"] = "x" * 50_000
        temp, root = self.copied(values)
        self.addCleanup(temp.cleanup)
        with self.assertRaisesRegex(MODULE.InvalidComparison, "oversized retained external text"):
            MODULE.verify_files(root)

    def test_split_external_copy_cannot_bypass_record_limit(self):
        values = copy.deepcopy(self.fixture())
        values["candidates.json"]["candidates"][0]["external_fragments"] = ["x" * 500] * 20
        temp, root = self.copied(values)
        self.addCleanup(temp.cleanup)
        with self.assertRaisesRegex(MODULE.InvalidComparison, "oversized retained candidate record"):
            MODULE.verify_files(root)

    def test_missing_dimension_is_rejected(self):
        values = copy.deepcopy(self.fixture())
        values["comparison.json"]["systems"]["far_git_pipeline"].pop()
        temp, root = self.copied(values)
        self.addCleanup(temp.cleanup)
        with self.assertRaisesRegex(MODULE.InvalidComparison, "dimension coverage drift"):
            MODULE.verify_files(root)

    def test_aggregate_score_is_rejected(self):
        values = copy.deepcopy(self.fixture())
        values["comparison.json"]["score"] = 9
        temp, root = self.copied(values)
        self.addCleanup(temp.cleanup)
        with self.assertRaisesRegex(MODULE.InvalidComparison, "aggregate scoring field forbidden"):
            MODULE.verify_files(root)

    def test_reader_identity_is_bound(self):
        values = copy.deepcopy(self.fixture())
        values["vela-baseline.json"]["reader"]["version"] = "0.977.2"
        temp, root = self.copied(values)
        self.addCleanup(temp.cleanup)
        with self.assertRaisesRegex(MODULE.InvalidComparison, "reader identity drift"):
            MODULE.verify_files(root)

    def test_review_identity_is_bound(self):
        values = copy.deepcopy(self.fixture())
        values["vela-baseline.json"]["correction_transition"]["review_event"]["proposal_id"] = "vpr_wrong"
        temp, root = self.copied(values)
        self.addCleanup(temp.cleanup)
        with self.assertRaisesRegex(MODULE.InvalidComparison, "proposal baseline drift"):
            MODULE.verify_files(root)

    def test_findings_are_derived_from_closed_rubric(self):
        values = copy.deepcopy(self.fixture())
        values["rubric.json"]["dimensions"][0]["assessments"]["far_git_pipeline"]["evaluates_allocation"] = False
        temp, root = self.copied(values)
        self.addCleanup(temp.cleanup)
        with self.assertRaisesRegex(MODULE.InvalidComparison, "finding not derived from rubric"):
            MODULE.verify_files(root)


if __name__ == "__main__":
    unittest.main()
