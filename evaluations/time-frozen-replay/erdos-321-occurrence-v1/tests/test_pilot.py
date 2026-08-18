from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PILOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PILOT))

import pilot  # noqa: E402


class FrozenReplayPilotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.bundle = self.root / "candidate"
        pilot.export_bundle(self.bundle)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_baseline(self) -> tuple[Path, Path]:
        response = self.root / "candidate-output.json"
        provenance = self.root / "provenance.json"
        subprocess.run(
            [
                sys.executable,
                str(PILOT / "baseline.py"),
                "--bundle",
                str(self.bundle),
                "--response",
                str(response),
                "--provenance",
                str(provenance),
            ],
            check=True,
        )
        return response, provenance

    def rebind_provenance(self, response: Path, provenance: Path) -> None:
        value = json.loads(provenance.read_text(encoding="utf-8"))
        value["output_sha256"] = pilot.digest(response.read_bytes())
        provenance.write_bytes(pilot.pretty_bytes(value))

    def test_exact_fixture_and_bundle_verify(self) -> None:
        fixture = pilot.verify_fixture()
        bundle = pilot.verify_bundle(self.bundle)
        self.assertEqual(fixture["task_sha256"], bundle["task_sha256"])
        self.assertRegex(bundle["bundle_root"], r"^sha256:[0-9a-f]{64}$")

    def test_candidate_bundle_excludes_protected_t1(self) -> None:
        adjudication = json.loads(pilot.ADJUDICATION.read_text(encoding="utf-8"))
        self.assertFalse((self.bundle / "protected").exists())
        with self.assertRaises(FileNotFoundError):
            (self.bundle / "protected" / "adjudication.json").read_bytes()
        payload = b"\n".join(
            path.read_bytes() for path in self.bundle.rglob("*") if path.is_file()
        )
        for token in adjudication["protected_tokens"]:
            self.assertNotIn(token.encode(), payload)
        protected_paths = {entry["path"] for entry in adjudication["protected_entries"]}
        exported_paths = {
            str(path.relative_to(self.bundle)).removeprefix("inputs/")
            for path in self.bundle.rglob("*")
            if path.is_file()
        }
        self.assertTrue(exported_paths.isdisjoint(protected_paths))

    def test_candidate_metadata_does_not_disclose_scored_answer_labels(self) -> None:
        adjudication = json.loads(pilot.ADJUDICATION.read_text(encoding="utf-8"))
        metadata = pilot.TASK.read_text(encoding="utf-8") + (
            pilot.RESPONSE_SCHEMA.read_text(encoding="utf-8")
        )
        self.assertNotIn(adjudication["expected"]["relation"], metadata)
        self.assertNotIn(adjudication["expected"]["scope"], metadata)

    def test_mutable_source_is_refused(self) -> None:
        source = (
            self.bundle
            / "inputs/evidence/erdos-321/translation/sources/formal-conjectures-321.lean"
        )
        source.write_text(source.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        with self.assertRaisesRegex(
            pilot.PilotError, "candidate byte changed"
        ) as raised:
            pilot.verify_bundle(self.bundle)
        self.assertEqual("mutable_source", raised.exception.code)

    def test_injected_protected_file_is_refused(self) -> None:
        injected = self.bundle / "protected" / "adjudication.json"
        injected.parent.mkdir(parents=True)
        injected.write_bytes(pilot.ADJUDICATION.read_bytes())
        with self.assertRaises(pilot.PilotError) as raised:
            pilot.verify_bundle(self.bundle)
        self.assertEqual("leakage", raised.exception.code)

    def test_missing_root_is_refused(self) -> None:
        task = json.loads(pilot.TASK.read_text(encoding="utf-8"))
        del task["t0"]["repository_root"]
        changed = self.root / "missing-root-task.json"
        changed.write_bytes(pilot.pretty_bytes(task))
        with self.assertRaises(pilot.PilotError) as raised:
            pilot.verify_fixture(task_path=changed)
        self.assertEqual("missing_root", raised.exception.code)

    def test_wrong_repository_roots_are_refused(self) -> None:
        for period in ("t0", "t1"):
            with self.subTest(period=period):
                task = json.loads(pilot.TASK.read_text(encoding="utf-8"))
                adjudication = json.loads(
                    pilot.ADJUDICATION.read_text(encoding="utf-8")
                )
                target = task["t0"] if period == "t0" else adjudication["t1"]
                target["repository_root"] = "sha256:" + "0" * 64
                changed_task = self.root / f"wrong-{period}-root-task.json"
                changed_adjudication = (
                    self.root / f"wrong-{period}-root-adjudication.json"
                )
                changed_task.write_bytes(pilot.pretty_bytes(task))
                changed_adjudication.write_bytes(pilot.pretty_bytes(adjudication))
                with self.assertRaises(pilot.PilotError) as raised:
                    pilot.verify_fixture(
                        task_path=changed_task,
                        adjudication_path=changed_adjudication,
                    )
                self.assertEqual("wrong_root", raised.exception.code)

    def test_wrong_period_is_refused(self) -> None:
        task = json.loads(pilot.TASK.read_text(encoding="utf-8"))
        adjudication = json.loads(pilot.ADJUDICATION.read_text(encoding="utf-8"))
        task["t0"]["commit"] = adjudication["t1"]["commit"]
        task["t0"]["tree"] = adjudication["t1"]["tree"]
        task["t0"]["repository_root"] = adjudication["t1"]["repository_root"]
        changed = self.root / "wrong-period-task.json"
        changed.write_bytes(pilot.pretty_bytes(task))
        with self.assertRaises(pilot.PilotError) as raised:
            pilot.verify_fixture(task_path=changed)
        self.assertEqual("wrong_period", raised.exception.code)

    def test_copied_answer_is_detected(self) -> None:
        response, provenance = self.run_baseline()
        value = json.loads(response.read_text(encoding="utf-8"))
        protected = json.loads(pilot.ADJUDICATION.read_text(encoding="utf-8"))[
            "protected_tokens"
        ][3]
        value["rationale"] += " " + protected
        response.write_bytes(pilot.pretty_bytes(value))
        self.rebind_provenance(response, provenance)
        score = pilot.evaluate(self.bundle, response, provenance)
        self.assertFalse(score["eligible"])
        self.assertEqual("fail", score["dimensions"]["hindsight_leakage"]["status"])

    def test_malformed_output_is_refused(self) -> None:
        response, provenance = self.run_baseline()
        value = json.loads(response.read_text(encoding="utf-8"))
        value["unexpected"] = "not allowed"
        response.write_bytes(pilot.pretty_bytes(value))
        with self.assertRaises(pilot.PilotError) as raised:
            pilot.evaluate(self.bundle, response, provenance)
        self.assertEqual("malformed_output", raised.exception.code)

    def test_evaluator_self_reference_is_detected(self) -> None:
        response, provenance = self.run_baseline()
        value = json.loads(response.read_text(encoding="utf-8"))
        value["rationale"] += " protected/adjudication.json"
        response.write_bytes(pilot.pretty_bytes(value))
        self.rebind_provenance(response, provenance)
        score = pilot.evaluate(self.bundle, response, provenance)
        self.assertFalse(score["eligible"])
        self.assertEqual(
            "fail", score["dimensions"]["evaluator_self_reference"]["status"]
        )

    def test_baseline_score_is_deterministic(self) -> None:
        response, provenance = self.run_baseline()
        first = pilot.evaluate(self.bundle, response, provenance)
        second = pilot.evaluate(self.bundle, response, provenance)
        self.assertEqual(pilot.pretty_bytes(first), pilot.pretty_bytes(second))
        self.assertTrue(first["eligible"])
        self.assertEqual({"fail": 0, "not_applicable": 0, "pass": 7}, first["summary"])

    def test_peer_performer_kind_does_not_change_dimensions(self) -> None:
        response, provenance = self.run_baseline()
        base = json.loads(provenance.read_text(encoding="utf-8"))
        comparable: list[dict[str, object]] = []
        for kind in ("human", "ai_agent", "organization", "deterministic_tool"):
            value = json.loads(json.dumps(base))
            value["performer"] = {"id": f"test:{kind}", "kind": kind}
            provenance.write_bytes(pilot.pretty_bytes(value))
            score = pilot.evaluate(self.bundle, response, provenance)
            comparable.append(
                {
                    "dimensions": score["dimensions"],
                    "eligible": score["eligible"],
                    "limitations": score["limitations"],
                    "summary": score["summary"],
                }
            )
        self.assertTrue(all(item == comparable[0] for item in comparable[1:]))


if __name__ == "__main__":
    unittest.main()
