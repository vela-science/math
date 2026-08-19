import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


MODULE = _load("fc_conditional_evaluate", BASE / "evaluate.py")
ANALYZE = _load("fc_conditional_analyze", BASE / "analyze.py")


class EvaluationTests(unittest.TestCase):
    def fixture(self):
        return MODULE.load_inputs(BASE)

    def copied(self, values):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        for name, value in values.items():
            (root / name).write_text(json.dumps(value))
        # verify_files digests the two scripts alongside the JSON inputs.
        for script in ("evaluate.py", "analyze.py"):
            (root / script).write_bytes((BASE / script).read_bytes())
        return temp, root

    def test_frozen_inputs_and_committed_report(self):
        result = MODULE.verify_files(BASE)
        expected = json.loads((BASE / "report.json").read_text())
        self.assertEqual(expected, MODULE.build_report(BASE))
        self.assertTrue(result["roots"]["evaluation_root"].startswith("sha256:"))

    def test_authority_effect_is_rejected(self):
        values = copy.deepcopy(self.fixture())
        values["results.json"]["authority_effect"] = "standing"
        temp, root = self.copied(values)
        self.addCleanup(temp.cleanup)
        with self.assertRaisesRegex(MODULE.InvalidAudit, "authority_effect none"):
            MODULE.verify_files(root)

    def test_vendored_third_party_source_is_rejected(self):
        values = copy.deepcopy(self.fixture())
        values["results.json"]["links"][0]["lean_source"] = "theorem foo : True := trivial"
        temp, root = self.copied(values)
        self.addCleanup(temp.cleanup)
        with self.assertRaisesRegex(MODULE.InvalidAudit, "third-party source field forbidden"):
            MODULE.verify_files(root)

    def test_oversized_retained_text_under_arbitrary_key_is_rejected(self):
        values = copy.deepcopy(self.fixture())
        values["results.json"]["links"][0]["excerpt"] = "x" * 5_000
        temp, root = self.copied(values)
        self.addCleanup(temp.cleanup)
        with self.assertRaisesRegex(MODULE.InvalidAudit, "oversized retained external text"):
            MODULE.verify_files(root)

    def test_population_drift_is_rejected(self):
        values = copy.deepcopy(self.fixture())
        values["audit.json"]["population"]["formal_proof_attributes"] += 1
        temp, root = self.copied(values)
        self.addCleanup(temp.cleanup)
        with self.assertRaisesRegex(MODULE.InvalidAudit, "population link-count drift"):
            MODULE.verify_files(root)

    def test_revision_pinning_drift_is_rejected(self):
        values = copy.deepcopy(self.fixture())
        key = next(iter(values["audit.json"]["population"]["revision_pinning"]))
        values["audit.json"]["population"]["revision_pinning"][key] += 1
        temp, root = self.copied(values)
        self.addCleanup(temp.cleanup)
        with self.assertRaisesRegex(MODULE.InvalidAudit, "revision pinning drift"):
            MODULE.verify_files(root)

    def test_undetermined_row_may_not_carry_a_verdict(self):
        values = copy.deepcopy(self.fixture())
        row = next(r for r in values["results.json"]["links"] if r["assessment"] != "assessed")
        row["d1"] = "clear"
        temp, root = self.copied(values)
        self.addCleanup(temp.cleanup)
        with self.assertRaisesRegex(MODULE.InvalidAudit, "undetermined row carries a D1 verdict"):
            MODULE.verify_files(root)

    def test_flag_without_a_named_binder_type_is_rejected(self):
        # This audit produced no D1 flag, so the guard is exercised by
        # introducing one. A count with nothing named behind it is the shape
        # this check exists to refuse.
        values = copy.deepcopy(self.fixture())
        row = next(r for r in values["results.json"]["links"] if r.get("d1") == "clear")
        row["d1"] = "flagged_uninhabited"
        row["d1_uninhabited_binder_types"] = []
        temp, root = self.copied(values)
        self.addCleanup(temp.cleanup)
        with self.assertRaisesRegex(MODULE.InvalidAudit, "flag without a named binder type"):
            MODULE.verify_files(root)

    def test_rubric_must_state_error_modes_both_ways(self):
        values = copy.deepcopy(self.fixture())
        values["rubric.json"]["discriminators"][0]["false_positives"] = []
        temp, root = self.copied(values)
        self.addCleanup(temp.cleanup)
        with self.assertRaisesRegex(MODULE.InvalidAudit, "error modes both ways"):
            MODULE.verify_files(root)

    def test_calibration_artifact_may_not_be_in_the_population(self):
        values = copy.deepcopy(self.fixture())
        values["calibration.json"]["artifact"]["repository"] = values["results.json"]["links"][0][
            "target_repo"
        ]
        temp, root = self.copied(values)
        self.addCleanup(temp.cleanup)
        with self.assertRaisesRegex(MODULE.InvalidAudit, "must not be inside the measured"):
            MODULE.verify_files(root)

    def test_calibration_must_still_separate_the_two_cases(self):
        values = copy.deepcopy(self.fixture())
        for row in values["calibration.json"]["declarations"]:
            row["d1"] = "clear"
        temp, root = self.copied(values)
        self.addCleanup(temp.cleanup)
        with self.assertRaisesRegex(MODULE.InvalidAudit, "must flag the known-conditional"):
            MODULE.verify_files(root)

    def test_tier2_may_not_confirm_an_unflagged_case(self):
        values = copy.deepcopy(self.fixture())
        clear = next(r for r in values["results.json"]["links"] if r.get("d1") == "clear")
        values["tier2.json"]["cases"].append(
            {
                "link": f"{clear['fc_file']}:{clear['fc_line']}",
                "outcome": "confirmed_conditional",
                "reason": "invented",
            }
        )
        temp, root = self.copied(values)
        self.addCleanup(temp.cleanup)
        with self.assertRaisesRegex(MODULE.InvalidAudit, "confirms a case Tier 1 did not flag"):
            MODULE.verify_files(root)

    def test_tier2_non_result_needs_an_exact_reason(self):
        # Every Tier-2 case here reached a result, so the guard is exercised by
        # adding one that did not. "The build did not happen" without a reason
        # is the shape this check exists to refuse.
        values = copy.deepcopy(self.fixture())
        first = values["tier2.json"]["cases"][0]
        values["tier2.json"]["cases"].append(
            {"link": first["link"], "outcome": "build_infeasible"}
        )
        temp, root = self.copied(values)
        self.addCleanup(temp.cleanup)
        with self.assertRaisesRegex(MODULE.InvalidAudit, "without an exact reason"):
            MODULE.verify_files(root)


class DiscriminatorTests(unittest.TestCase):
    """D1 is the load-bearing heuristic, so its behaviour is pinned directly.

    These fixtures are written here, not copied from any third-party project.
    """

    def build(self, files: dict[str, str]):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        for name, text in files.items():
            (root / name).parent.mkdir(parents=True, exist_ok=True)
            (root / name).write_text(text)
        index = ANALYZE.RepoIndex(root)
        return temp, index, ANALYZE.inhabitation(index)

    def state_of(self, index, inhab, decl_name):
        decl = next(d for d in index.decls if d["short_name"] == decl_name)
        deps = ANALYZE.binder_local_types(index, decl)
        return {name: inhab[name]["state"] for name in deps}

    def test_never_constructed_assumption_package_is_uninhabited(self):
        temp, index, inhab = self.build(
            {
                "A.lean": (
                    "structure Assumption where\n"
                    "  holds : True\n"
                    "\n"
                    "theorem conjecture (X : Assumption) : 1 = 1 := rfl\n"
                )
            }
        )
        self.addCleanup(temp.cleanup)
        self.assertEqual(
            {"Assumption": "no_construction_found"},
            self.state_of(index, inhab, "conjecture"),
        )

    def test_open_constructor_does_not_count_as_closed_construction(self):
        """The calibration artifact's exact shape: a construction exists, but it
        takes the assumption it is supposed to discharge."""
        temp, index, inhab = self.build(
            {
                "A.lean": (
                    "structure Part where\n"
                    "  holds : True\n"
                    "\n"
                    "structure Package where\n"
                    "  part : Part\n"
                    "\n"
                    "def package_of_part (p : Part) : Package where\n"
                    "  part := p\n"
                    "\n"
                    "theorem conjecture (X : Package) : 1 = 1 := rfl\n"
                )
            }
        )
        self.addCleanup(temp.cleanup)
        self.assertEqual(
            {"Package": "conditional_construction_only"},
            self.state_of(index, inhab, "conjecture"),
        )

    def test_closed_construction_clears_the_type(self):
        temp, index, inhab = self.build(
            {
                "A.lean": (
                    "structure Package where\n"
                    "  holds : True\n"
                    "\n"
                    "def thePackage : Package where\n"
                    "  holds := trivial\n"
                    "\n"
                    "theorem conjecture (X : Package) : 1 = 1 := rfl\n"
                )
            }
        )
        self.addCleanup(temp.cleanup)
        self.assertEqual(
            {"Package": "closed_construction"}, self.state_of(index, inhab, "conjecture")
        )

    def test_mathlib_binders_are_not_treated_as_local_assumptions(self):
        temp, index, inhab = self.build(
            {"A.lean": "theorem conjecture (n : Nat) (s : Finset Nat) : 1 = 1 := rfl\n"}
        )
        self.addCleanup(temp.cleanup)
        self.assertEqual({}, self.state_of(index, inhab, "conjecture"))

    def test_comment_stripping_keeps_offsets_and_hides_prose(self):
        text = "/- theorem ghost : False := sorry -/\ntheorem real : True := trivial\n"
        stripped = ANALYZE.strip_comments(text)
        self.assertEqual(len(text), len(stripped))
        self.assertNotIn("ghost", stripped)
        self.assertIn("theorem real", stripped)
        self.assertEqual(0, len(ANALYZE.GATE_PATTERNS["sorry"].findall(stripped)))

    def test_locator_never_returns_a_whole_file_of_lemmas(self):
        temp, index, _ = self.build(
            {
                "P.lean": (
                    "structure Dev where\n  h : True\n\n"
                    "theorem helper_one (d : Dev) : 1 = 1 := rfl\n"
                    "theorem helper_two (d : Dev) : 2 = 2 := rfl\n"
                    "theorem erdos_problem_42 : 3 = 3 := rfl\n"
                )
            }
        )
        self.addCleanup(temp.cleanup)
        located = ANALYZE.locate_target(index, "P.lean", None, "erdos_42")
        self.assertEqual("file_and_problem_number_match", located["basis"])
        self.assertEqual(
            ["erdos_problem_42"],
            [index.decls[i]["short_name"] for i in located["decl_indexes"]],
        )

    def test_line_anchor_selects_the_declaration_it_points_inside(self):
        """A `#L` anchor lands in the middle of the proof it is about.

        Reading forward from the anchor instead of around it walks past the
        linked proof into whatever comes next, which in this corpus was
        sometimes an unrelated `sorry`.
        """
        temp, index, _ = self.build(
            {
                "L.lean": (
                    "theorem the_linked_one : True := by\n"
                    "  trivial\n"
                    "  -- more proof\n"
                    "\n"
                    "theorem an_unrelated_one : True := by\n"
                    "  sorry\n"
                )
            }
        )
        self.addCleanup(temp.cleanup)
        located = ANALYZE.locate_target(index, "L.lean", 2, "the_linked_one")
        self.assertEqual("line_anchor", located["basis"])
        self.assertEqual(
            ["the_linked_one"],
            [index.decls[i]["short_name"] for i in located["decl_indexes"]],
        )

    def test_line_anchor_on_the_attribute_above_selects_the_declaration_below(self):
        temp, index, _ = self.build(
            {"L.lean": "@[simp]\ntheorem below_the_attribute : True := trivial\n"}
        )
        self.addCleanup(temp.cleanup)
        located = ANALYZE.locate_target(index, "L.lean", 1, "below_the_attribute")
        self.assertEqual(
            ["below_the_attribute"],
            [index.decls[i]["short_name"] for i in located["decl_indexes"]],
        )

    def test_formal_proof_attribute_carries_no_declaration_name(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        (root / "FormalConjectures").mkdir()
        (root / "FormalConjectures" / "X.lean").write_text(
            '@[category research solved, formal_proof using lean4 at "https://github.com/o/r/blob/abc1234/A.lean#L7"]\n'
            "theorem some_conjecture : True := trivial\n"
        )
        rows = ANALYZE.parse_fc(root)
        self.assertEqual(1, len(rows))
        self.assertEqual("lean4", rows[0]["proof_kind"])
        self.assertEqual("some_conjecture", rows[0]["fc_decl"])
        self.assertEqual("pinned_commit", rows[0]["revision_pinning"])
        self.assertEqual(7, rows[0]["target_line"])
        self.assertNotIn("target_declaration_name", rows[0])

    def test_branch_link_is_recorded_as_unpinned(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        (root / "FormalConjectures").mkdir()
        (root / "FormalConjectures" / "X.lean").write_text(
            '@[category research solved, formal_proof using lean4 at "https://github.com/o/r/blob/main/A.lean"]\n'
            "theorem some_conjecture : True := trivial\n"
        )
        self.assertEqual("branch_or_tag", ANALYZE.parse_fc(root)[0]["revision_pinning"])


if __name__ == "__main__":
    unittest.main()
