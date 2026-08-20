#!/usr/bin/env python3
"""Tests for the Formal Conjectures build audit.

Two things are being protected. The first is that `verify` actually rejects the
mistakes this kind of audit makes: claiming a clean axiom set on a checkout
nobody built, flags that do not follow from the axiom sets they are derived
from, a finding that names no link, a locator confidence quietly upgraded from
the static audit, and third-party source pasted into a frozen file.

The second is the arithmetic in `build.py` that decides what an axiom set
means, and the project-shape reasoning that decides what to build.
"""

from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

import build  # noqa: E402
import evaluate  # noqa: E402


def load() -> dict:
    return evaluate.load_inputs(BASE)


class Fixture:
    """A scratch copy of the evaluation directory that can be corrupted."""

    def __init__(self) -> None:
        self.dir = Path(tempfile.mkdtemp(prefix="fc-build-audit-test-"))
        for name in evaluate.INPUTS:
            shutil.copy(BASE / name, self.dir / name)
        shutil.copy(BASE / "evaluate.py", self.dir / "evaluate.py")
        shutil.copy(BASE / "build.py", self.dir / "build.py")
        self.static = self.dir / "static.json"
        shutil.copy(evaluate.STATIC_RESULTS, self.static)

    def write(self, name: str, value: dict) -> None:
        (self.dir / name).write_text(json.dumps(value))

    def read(self, name: str) -> dict:
        return json.loads((self.dir / name).read_text())

    def verify(self):
        return evaluate.verify_files(self.dir, self.static)

    def close(self) -> None:
        shutil.rmtree(self.dir, ignore_errors=True)


class FixtureCase(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = Fixture()
        self.addCleanup(self.fixture.close)

    def assertRejects(self, fragment: str) -> None:
        with self.assertRaises(evaluate.InvalidAudit) as caught:
            self.fixture.verify()
        self.assertIn(fragment, str(caught.exception))


class TestVerifyAcceptsTheFrozenAudit(unittest.TestCase):
    def test_verify_passes_and_roots_are_stable(self) -> None:
        first = evaluate.verify_files()
        second = evaluate.verify_files()
        self.assertEqual(first["roots"], second["roots"])
        for root in first["roots"].values():
            self.assertTrue(root.startswith("sha256:"))

    def test_report_derives_from_builds_only(self) -> None:
        report = evaluate.build_report()
        builds = load()["builds.json"]
        self.assertEqual(report["authority_effect"], "none")
        self.assertEqual(report["coverage"]["checkouts_total"], len(builds["checkouts"]))
        self.assertEqual(report["coverage"]["links_total"], len(builds["links"]))
        total = sum(report["outcomes"]["by_checkout"].values())
        self.assertEqual(total, len(builds["checkouts"]))

    def test_every_row_states_an_outcome_in_the_closed_vocabulary(self) -> None:
        builds = load()["builds.json"]
        for row in builds["checkouts"]:
            self.assertIn(row["outcome"], evaluate.OUTCOMES)
        for row in builds["links"]:
            self.assertIn(row["build_outcome"], evaluate.OUTCOMES)

    def test_nothing_claims_authority(self) -> None:
        for value in load().values():
            self.assertEqual(value["authority_effect"], "none")


class TestVerifyRejectsOverclaim(FixtureCase):
    def test_unattempted_checkout_may_not_carry_axioms(self) -> None:
        builds = self.fixture.read("builds.json")
        row = next(
            r for r in builds["checkouts"] if r["outcome"] not in evaluate.ATTEMPTED
        ) if any(
            r["outcome"] not in evaluate.ATTEMPTED for r in builds["checkouts"]
        ) else builds["checkouts"][0]
        row["outcome"] = "not_attempted"
        row["axioms"] = {"Foo.bar": {"status": "read", "axioms": ["propext"]}}
        self.fixture.write("builds.json", builds)
        self.assertRejects("unattempted checkout carries axiom readings")

    def test_built_without_an_axiom_reading_is_rejected(self) -> None:
        builds = self.fixture.read("builds.json")
        row = next(r for r in builds["checkouts"] if r["outcome"] == "built")
        row["axioms"] = {"Foo.bar": {"status": "not_found", "error": "unknown identifier"}}
        row["axiom_flags"] = []
        self.fixture.write("builds.json", builds)
        self.assertRejects("without a single axiom reading")

    def test_a_failure_must_carry_its_exact_text(self) -> None:
        builds = self.fixture.read("builds.json")
        candidates = [
            r
            for r in builds["checkouts"]
            if r["outcome"] in {"build_failed", "build_timeout", "toolchain_unavailable"}
        ]
        if not candidates:
            self.skipTest("no failure row in this run")
        candidates[0]["error"] = ""
        self.fixture.write("builds.json", builds)
        self.assertRejects("failure without exact text")

    def test_axiom_flags_must_follow_from_the_axiom_sets(self) -> None:
        builds = self.fixture.read("builds.json")
        row = next(r for r in builds["checkouts"] if r["outcome"] == "built")
        row["axiom_flags"] = ["sorryAx"]
        self.fixture.write("builds.json", builds)
        self.assertRejects("not derived from the axiom sets")

    def test_a_link_may_not_disagree_with_its_checkout(self) -> None:
        builds = self.fixture.read("builds.json")
        row = next(r for r in builds["links"] if r["build_outcome"] != "built")
        row["build_outcome"] = "built"
        self.fixture.write("builds.json", builds)
        self.assertRejects("disagrees with its checkout")

    def test_a_partial_run_must_say_why(self) -> None:
        builds = self.fixture.read("builds.json")
        attempted = sum(1 for r in builds["checkouts"] if r["outcome"] in evaluate.ATTEMPTED)
        if attempted == len(builds["checkouts"]):
            self.skipTest("this run is complete")
        findings = self.fixture.read("findings.json")
        findings["coverage"]["why_partial"] = ""
        self.fixture.write("findings.json", findings)
        self.assertRejects("partial run must state why")


class TestVerifyRejectsAnIncompleteReading(FixtureCase):
    """A clean axiom closure is necessary and not sufficient.

    `@[csimp]` (lean4#7463) can substitute an unverified implementation without
    touching the closure, and a hypothesis parameter never appears in one at
    all. So a reading that carries only the closure is incomplete, and `verify`
    treats it as such rather than as a clean result.
    """

    def read_reading(self):
        builds = self.fixture.read("builds.json")
        for row in builds["checkouts"]:
            for decl, reading in (row.get("axioms") or {}).items():
                if reading.get("status") == "read":
                    return builds, row, decl, reading
        return None, None, None, None

    def test_a_reading_without_prop_hypotheses_is_rejected(self) -> None:
        builds, _, _, reading = self.read_reading()
        if reading is None:
            self.skipTest("no axiom reading in this run")
        reading.pop("prop_hypotheses", None)
        self.fixture.write("builds.json", builds)
        self.assertRejects("without a prop_hypotheses field")

    def test_unavailable_may_not_carry_a_count(self) -> None:
        builds, _, _, reading = self.read_reading()
        if reading is None:
            self.skipTest("no axiom reading in this run")
        reading["prop_hypotheses"] = {"status": "unavailable", "prop_binders": 0}
        self.fixture.write("builds.json", builds)
        self.assertRejects("unavailable prop_hypotheses carries a count")

    def test_more_prop_binders_than_binders_is_rejected(self) -> None:
        builds, _, _, reading = self.read_reading()
        if reading is None:
            self.skipTest("no axiom reading in this run")
        reading["prop_hypotheses"] = {"status": "read", "prop_binders": 9, "total_binders": 2}
        self.fixture.write("builds.json", builds)
        self.assertRejects("more Prop binders than binders")

    def test_an_unknown_hypothesis_status_is_rejected(self) -> None:
        builds, _, _, reading = self.read_reading()
        if reading is None:
            self.skipTest("no axiom reading in this run")
        reading["prop_hypotheses"] = {"status": "probably_fine"}
        self.fixture.write("builds.json", builds)
        self.assertRejects("prop_hypotheses status")

    def test_the_rubric_must_name_the_known_closure_leaks(self) -> None:
        rubric = self.fixture.read("rubric.json")
        rubric["trust_surfaces"]["axiom_closure"]["known_leaks"] = []
        self.fixture.write("rubric.json", rubric)
        self.assertRejects("known leaks")

    def test_the_rubric_must_define_both_surfaces(self) -> None:
        rubric = self.fixture.read("rubric.json")
        del rubric["trust_surfaces"]["prop_hypotheses"]
        self.fixture.write("rubric.json", rubric)
        self.assertRejects("must define the prop_hypotheses surface")


class TestHypothesisProbeParsing(unittest.TestCase):
    def test_a_probe_that_did_not_run_is_unavailable_not_zero(self) -> None:
        self.assertEqual(build.parse_prop_hypotheses("", "A.b"), {"status": "unavailable"})
        self.assertEqual(
            build.parse_prop_hypotheses("error: unknown identifier 'run_cmd'", "A.b"),
            {"status": "unavailable"},
        )

    def test_a_declaration_with_no_prop_binders_reads_zero(self) -> None:
        out = build.parse_prop_hypotheses("info: VELA_PROP_COUNT A.b 0 3", "A.b")
        self.assertEqual(out["status"], "read")
        self.assertEqual(out["prop_binders"], 0)
        self.assertEqual(out["total_binders"], 3)
        self.assertEqual(out["types"], [])

    def test_hypothesis_types_are_captured_and_capped(self) -> None:
        long = "x" * 500
        text = f"info: VELA_PROP_HYP A.b @@ {long}\ninfo: VELA_PROP_COUNT A.b 1 4"
        out = build.parse_prop_hypotheses(text, "A.b")
        self.assertEqual(out["prop_binders"], 1)
        self.assertLessEqual(len(out["types"][0]), build.MAX_HYPOTHESIS_RENDERING)

    def test_many_hypotheses_are_truncated_and_say_so(self) -> None:
        lines = "\n".join(f"info: VELA_PROP_HYP A.b @@ h{index}" for index in range(40))
        out = build.parse_prop_hypotheses(lines + "\ninfo: VELA_PROP_COUNT A.b 40 40", "A.b")
        self.assertEqual(out["prop_binders"], 40)
        self.assertEqual(len(out["types"]), build.MAX_HYPOTHESES_RECORDED)
        self.assertTrue(out["types_truncated"])

    def test_one_declarations_hypotheses_are_not_read_as_anothers(self) -> None:
        """The whole point of naming every marker: the batch is one file."""
        text = (
            "info: VELA_PROP_HYP A.first @@ 0 < n\n"
            "info: VELA_PROP_COUNT A.first 1 2\n"
            "info: VELA_PROP_COUNT A.second 0 1\n"
        )
        first = build.parse_prop_hypotheses(text, "A.first")
        second = build.parse_prop_hypotheses(text, "A.second")
        self.assertEqual(first["prop_binders"], 1)
        self.assertEqual(first["types"], ["0 < n"])
        self.assertEqual(second["prop_binders"], 0)
        self.assertEqual(second["types"], [])

    def test_a_neighbours_unknown_constant_is_not_attributed_here(self) -> None:
        text = (
            "error: Unknown constant `A.missing`\n"
            "info: 'A.present' depends on axioms: [propext]\n"
            "info: VELA_PROP_COUNT A.present 0 1\n"
        )
        present = build.read_one(text, "A.present", 1)
        missing = build.read_one(text, "A.missing", 1)
        self.assertEqual(present["status"], "read")
        self.assertEqual(present["axioms"], ["propext"])
        self.assertEqual(missing["status"], "not_found")

    def test_the_probe_is_valid_lean_for_a_dotted_name(self) -> None:
        probe = build.hypothesis_probe_for("Erdos418.erdos_418")
        self.assertIn("`Erdos418.erdos_418", probe)
        self.assertIn("forallTelescope info.type", probe)
        self.assertNotIn("forallTelescopeReducing", probe)
        self.assertIn("let mut props : Nat := 0", probe)
        self.assertNotIn("DECL", probe)


class TestStatedNegativesAreRederived(FixtureCase):
    """The headline of this audit is a set of zeros.

    A negative result nobody re-checks is a sentence, not a finding, so every
    stated zero is recomputed from `builds.json` and a mismatch is fatal.
    """

    def test_an_understated_build_failure_count_is_rejected(self) -> None:
        findings = self.fixture.read("findings.json")
        findings["stated_negatives"]["build_failures_at_a_pinned_revision"] = 7
        self.fixture.write("findings.json", findings)
        self.assertRejects("stated negative disagrees with builds.json")

    def test_a_false_sorry_free_claim_is_rejected(self) -> None:
        builds = self.fixture.read("builds.json")
        row = next(r for r in builds["checkouts"] if r["outcome"] == "built")
        decl, reading = next(
            (d, r) for d, r in row["axioms"].items() if r.get("status") == "read"
        )
        reading["axioms"] = sorted(set(reading["axioms"]) | {"sorryAx"})
        row["axiom_flags"] = sorted(set(row["axiom_flags"]) | {"sorryAx"})
        self.fixture.write("builds.json", builds)
        # The claim of zero `sorryAx` no longer matches the data.
        self.assertRejects("declarations_whose_closure_contains_sorryAx")

    def test_an_unavailable_probe_cannot_be_hidden(self) -> None:
        builds = self.fixture.read("builds.json")
        row = next(r for r in builds["checkouts"] if r["outcome"] == "built")
        reading = next(r for r in row["axioms"].values() if r.get("status") == "read")
        reading["prop_hypotheses"] = {"status": "unavailable"}
        self.fixture.write("builds.json", builds)
        self.assertRejects("declarations_whose_hypothesis_probe_was_unavailable")

    def test_bare_zeros_without_a_reading_are_rejected(self) -> None:
        findings = self.fixture.read("findings.json")
        findings["stated_negatives"]["reading"] = ""
        self.fixture.write("findings.json", findings)
        self.assertRejects("read in prose")

    def test_dropping_the_negatives_entirely_is_rejected(self) -> None:
        findings = self.fixture.read("findings.json")
        del findings["stated_negatives"]
        self.fixture.write("findings.json", findings)
        self.assertRejects("must state its negative results")


class TestVerifyRejectsDriftFromTheStaticAudit(FixtureCase):
    def test_locator_confidence_may_not_be_upgraded(self) -> None:
        builds = self.fixture.read("builds.json")
        row = next(
            r for r in builds["links"] if r["target_locator_confidence"] != "high"
        )
        row["target_locator_confidence"] = "high"
        self.fixture.write("builds.json", builds)
        self.assertRejects("locator confidence altered")

    def test_static_root_drift_is_rejected(self) -> None:
        builds = self.fixture.read("builds.json")
        builds["source"]["static_results_root"] = "sha256:" + "0" * 64
        self.fixture.write("builds.json", builds)
        self.assertRejects("results_root drift")

    def test_dropping_a_checkout_is_rejected(self) -> None:
        builds = self.fixture.read("builds.json")
        builds["checkouts"] = builds["checkouts"][:-1]
        self.fixture.write("builds.json", builds)
        self.assertRejects("checkout-count drift")

    def test_dropping_a_link_is_rejected(self) -> None:
        builds = self.fixture.read("builds.json")
        builds["links"] = builds["links"][:-1]
        self.fixture.write("builds.json", builds)
        self.assertRejects("link-count drift")


class TestVerifyRejectsUngroundedFindings(FixtureCase):
    def test_a_finding_must_name_a_real_link(self) -> None:
        findings = self.fixture.read("findings.json")
        if not findings["cases"]:
            self.skipTest("no findings in this run")
        findings["cases"][0]["links"] = ["NoSuch/File.lean:1"]
        self.fixture.write("findings.json", findings)
        self.assertRejects("references no link")

    def test_an_axiom_finding_needs_a_nonstandard_axiom_set(self) -> None:
        findings = self.fixture.read("findings.json")
        cases = [c for c in findings["cases"] if c["kind"] == "axiom_clause_failure"]
        if not cases:
            self.skipTest("no axiom finding in this run")
        cases[0]["axioms"] = ["propext", "Classical.choice", "Quot.sound"]
        self.fixture.write("findings.json", findings)
        self.assertRejects("axiom set is standard")

    def test_a_flagged_link_must_have_a_finding(self) -> None:
        findings = self.fixture.read("findings.json")
        builds = self.fixture.read("builds.json")
        if not any(r["axiom_flags"] for r in builds["links"]):
            self.skipTest("no flagged link in this run")
        findings["cases"] = [
            c for c in findings["cases"] if c["kind"] != "axiom_clause_failure"
        ]
        self.fixture.write("findings.json", findings)
        self.assertRejects("axiom flag with no finding")

    def test_a_build_failure_finding_must_read_the_failure(self) -> None:
        findings = self.fixture.read("findings.json")
        cases = [c for c in findings["cases"] if c["kind"].endswith("build_failure")]
        if not cases:
            self.skipTest("no build-failure finding in this run")
        cases[0]["drift_reading"] = ""
        self.fixture.write("findings.json", findings)
        self.assertRejects("read as drift or not")


class TestVerifyProtectsRights(FixtureCase):
    def test_oversized_retained_text_is_rejected(self) -> None:
        builds = self.fixture.read("builds.json")
        builds["checkouts"][0]["error"] = "x" * (evaluate.MAX_RETAINED_STRING + 1)
        self.fixture.write("builds.json", builds)
        self.assertRejects("oversized retained external text")

    def test_a_source_body_field_is_rejected_anywhere(self) -> None:
        builds = self.fixture.read("builds.json")
        builds["checkouts"][0]["proof_text"] = "theorem foo : True := trivial"
        self.fixture.write("builds.json", builds)
        self.assertRejects("third-party source field forbidden")

    def test_a_scoring_field_is_rejected(self) -> None:
        builds = self.fixture.read("builds.json")
        builds["checkouts"][0]["score"] = 1
        self.fixture.write("builds.json", builds)
        self.assertRejects("aggregate scoring field forbidden")

    def test_schema_drift_is_rejected(self) -> None:
        builds = self.fixture.read("builds.json")
        builds["schema"] = "something-else"
        self.fixture.write("builds.json", builds)
        self.assertRejects("schema drift")

    def test_invented_authority_is_rejected(self) -> None:
        builds = self.fixture.read("builds.json")
        builds["authority_effect"] = "accepted"
        self.fixture.write("builds.json", builds)
        self.assertRejects("authority_effect none")

    def test_the_frozen_files_hold_no_long_strings(self) -> None:
        values = load()
        evaluate.enforce_rights_shape(values["builds.json"], "builds.json")


class TestAxiomArithmetic(unittest.TestCase):
    def test_the_standard_three_are_not_a_flag(self) -> None:
        self.assertEqual(build.classify_axioms(["propext", "Classical.choice", "Quot.sound"]), [])
        self.assertEqual(build.classify_axioms([]), [])

    def test_native_decide_is_named_by_either_of_its_axioms(self) -> None:
        self.assertEqual(
            build.classify_axioms(["propext", "Lean.ofReduceBool"]), ["native_decide"]
        )
        self.assertEqual(
            build.classify_axioms(["Quot.sound", "Lean.trustCompiler"]), ["native_decide"]
        )

    def test_sorry_is_named_even_beside_native_decide(self) -> None:
        flags = build.classify_axioms(["propext", "sorryAx", "Lean.ofReduceBool"])
        self.assertEqual(flags, ["native_decide", "sorryAx"])

    def test_an_unknown_axiom_is_named_separately(self) -> None:
        self.assertEqual(build.classify_axioms(["propext", "myAxiom"]), ["nonstandard_axiom"])

    def test_evaluate_and_build_agree_on_every_flag(self) -> None:
        """Two implementations of the same rule must not drift apart."""
        cases = [
            [],
            ["propext"],
            ["propext", "Classical.choice", "Quot.sound"],
            ["sorryAx"],
            ["Lean.ofReduceBool", "Lean.trustCompiler"],
            ["propext", "sorryAx", "Lean.trustCompiler", "Foo.bar"],
            ["Classical.choice", "Foo.bar"],
        ]
        for case in cases:
            self.assertEqual(
                build.classify_axioms(case), evaluate.axiom_flags(case), msg=str(case)
            )


class TestProjectShape(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = Path(tempfile.mkdtemp(prefix="fc-build-shape-"))
        self.addCleanup(shutil.rmtree, self.dir, True)

    def project(self, rel: str, toolchain: str = "leanprover/lean4:v4.27.0", mathlib: bool = True):
        root = self.dir / rel
        (root).mkdir(parents=True, exist_ok=True)
        (root / "lean-toolchain").write_text(toolchain + "\n")
        (root / "lakefile.toml").write_text(
            'name = "demo"\n' + ('[[require]]\nname = "mathlib"\n' if mathlib else "")
        )
        return root

    def test_a_repository_with_several_projects_picks_the_one_holding_the_link(self) -> None:
        self.project("src/v4.24.0")
        newer = self.project("src/v4.29.1")
        (newer / "Proofs").mkdir()
        (newer / "Proofs" / "Erdos418.lean").write_text("theorem t : True := trivial\n")
        roots = build.project_roots(self.dir)
        self.assertEqual(len(roots), 2)
        chosen, basis = build.pick_project(
            self.dir, roots, ["src/v4.29.1/Proofs/Erdos418.lean"]
        )
        self.assertEqual(chosen, newer)
        self.assertEqual(basis, "contains_linked_file")

    def test_a_sole_project_is_reported_as_such(self) -> None:
        only = self.project(".")
        roots = build.project_roots(self.dir)
        self.assertEqual(roots, [only])
        chosen, basis = build.pick_project(self.dir, roots, [])
        self.assertEqual(basis, "sole_project")

    def test_a_repository_with_no_manifest_has_no_project(self) -> None:
        (self.dir / "Foo.lean").write_text("theorem t : True := trivial\n")
        self.assertEqual(build.project_roots(self.dir), [])
        self.assertEqual(build.pick_project(self.dir, [], []), (None, "none"))

    def test_a_lean_toolchain_without_a_manifest_is_not_a_project(self) -> None:
        (self.dir / "lean-toolchain").write_text("leanprover/lean4:v4.27.0\n")
        self.assertEqual(build.project_roots(self.dir), [])

    def test_toolchain_and_mathlib_dependency_are_read_from_the_project(self) -> None:
        root = self.project("proj", toolchain="leanprover/lean4:v4.31.0")
        self.assertEqual(build.read_toolchain(root), "leanprover/lean4:v4.31.0")
        self.assertTrue(build.depends_on_mathlib(root))
        bare = self.project("bare", mathlib=False)
        self.assertFalse(build.depends_on_mathlib(bare))

    def test_mathlib_revision_comes_from_the_lake_manifest(self) -> None:
        root = self.project("proj")
        (root / "lake-manifest.json").write_text(
            json.dumps({"packages": [{"name": "mathlib", "rev": "abc123"}]})
        )
        self.assertEqual(build.mathlib_rev(root), "abc123")

    def test_a_linked_path_becomes_a_module_name(self) -> None:
        root = self.project("src/v4.29.1")
        (root / "Proofs").mkdir()
        (root / "Proofs" / "Erdos418.lean").write_text("theorem t : True := trivial\n")
        module = build.module_of(root, self.dir, "src/v4.29.1/Proofs/Erdos418.lean")
        self.assertEqual(module, "Proofs.Erdos418")

    def test_a_dotted_numeric_filename_becomes_one_escaped_component(self) -> None:
        """Formal Conjectures names OEIS files after the sequence number.

        Lake makes `FormalConjectures/OEIS/103311.wip.lean` the module
        `FormalConjectures.OEIS.«103311.wip»` — the stem is ONE component,
        internal dot included. Verified against a Lake fixture: the raw dotted
        name and the split-component form both fail to build, this one works.
        Under the raw form all 38 links of one checkout reported `probe_failed`
        while every declaration was present and compiled.
        """
        root = self.project("proj")
        (root / "OEIS").mkdir()
        (root / "OEIS" / "103311.wip.lean").write_text("theorem t : True := trivial\n")
        module = build.module_of(root, self.dir, "proj/OEIS/103311.wip.lean")
        self.assertEqual(module, "OEIS.«103311.wip»")

    def test_an_ordinary_component_is_left_alone(self) -> None:
        for part in ("ErdosProblems", "A", "Foo", "bar'", "Nat"):
            self.assertEqual(build.escape_component(part), part)
        self.assertEqual(build.escape_component("103311.wip"), "«103311.wip»")
        self.assertEqual(build.escape_component("1a"), "«1a»")

    def test_machine_paths_are_redacted_from_retained_text(self) -> None:
        root = Path("/scratch/repos/owner__repo@abc")
        text = f"{root}/Foo.lean:1:0: error: object file missing"
        self.assertEqual(
            build.redact(text, root), "<checkout>/Foo.lean:1:0: error: object file missing"
        )

    def test_a_path_outside_the_project_yields_no_module(self) -> None:
        root = self.project("proj")
        (self.dir / "Other.lean").write_text("theorem t : True := trivial\n")
        self.assertIsNone(build.module_of(root, self.dir, "Other.lean"))
        self.assertIsNone(build.module_of(root, self.dir, "proj/Missing.lean"))
        self.assertIsNone(build.module_of(root, self.dir, "README.md"))


class TestWorklist(unittest.TestCase):
    def test_the_worklist_is_the_static_audit_ordered_by_link_count(self) -> None:
        static = build.load_static(evaluate.STATIC_RESULTS)
        entries = build.worklist(static)
        self.assertEqual(len(entries), len(static["checkouts"]))
        counts = [len(entry["links"]) for entry in entries]
        self.assertEqual(counts, sorted(counts, reverse=True))
        self.assertEqual(sum(counts), sum(1 for l in static["links"] if l.get("checkout")))
        self.assertEqual(entries[0]["repo"], "plby/lean-proofs")

    def test_the_worklist_carries_locator_confidence_through_unchanged(self) -> None:
        static = build.load_static(evaluate.STATIC_RESULTS)
        entries = build.worklist(static)
        seen = {
            (link["fc_decl"], link["target_locator_confidence"])
            for entry in entries
            for link in entry["links"]
        }
        expected = {
            (link["fc_decl"], link["target_locator_confidence"])
            for link in static["links"]
            if link.get("checkout")
        }
        self.assertEqual(seen, expected)


class TestExcerpt(unittest.TestCase):
    def test_an_excerpt_is_capped(self) -> None:
        text = "\n".join(f"error: line {index}" for index in range(200))
        out = build.excerpt(text)
        self.assertLessEqual(len(out), build.MAX_EXCERPT)

    def test_an_excerpt_prefers_error_lines(self) -> None:
        text = "info: building\ninfo: still building\nerror: unknown identifier foo\n"
        self.assertIn("unknown identifier", build.excerpt(text))
        self.assertNotIn("still building", build.excerpt(text))

    def test_an_excerpt_of_nothing_is_empty(self) -> None:
        self.assertEqual(build.excerpt(""), "")


if __name__ == "__main__":
    unittest.main()
