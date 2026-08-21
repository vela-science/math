from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import runner  # noqa: E402


class RunnerTests(unittest.TestCase):
    def test_docker_command_uses_real_repo_stdin_and_read_only_inputs(self) -> None:
        command = runner.docker_codex_command(
            image="sha256:abc",
            repo=pathlib.Path("/source"),
            auth=pathlib.Path("/auth.json"),
            schema=pathlib.Path("/schema.json"),
            output=pathlib.Path("/output"),
            model="gpt-5.6-sol",
            reasoning="low",
        )
        joined = " ".join(command)
        self.assertIn("docker run --rm -i", joined)
        self.assertIn("src=/source,dst=/repo,readonly", joined)
        self.assertIn("src=/auth.json,dst=/root/.codex/auth.json,readonly", joined)
        self.assertIn("-C /repo", joined)
        self.assertIn("--workdir /repo --entrypoint codex", joined)
        self.assertNotIn("--read-only", command)
        self.assertNotIn("/work", joined)
        self.assertNotIn("/bin/bash", command)

    def test_git_snapshot_requires_clean_real_repository(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = pathlib.Path(raw).resolve()
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            subprocess.run(
                ["git", "-C", str(repo), "config", "user.name", "Test"], check=True
            )
            subprocess.run(
                ["git", "-C", str(repo), "config", "user.email", "test@invalid.local"],
                check=True,
            )
            (repo / "a.txt").write_text("a\n")
            subprocess.run(["git", "-C", str(repo), "add", "a.txt"], check=True)
            subprocess.run(
                ["git", "-C", str(repo), "commit", "-q", "-m", "a"], check=True
            )
            snapshot = runner.git_snapshot(repo)
            self.assertTrue(snapshot.clean)
            self.assertEqual(len(snapshot.commit), 40)
            (repo / "a.txt").write_text("changed\n")
            with self.assertRaisesRegex(runner.RunnerError, "not clean"):
                runner.git_snapshot(repo)

    def test_small_schema_is_fail_closed(self) -> None:
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {"qualification": {"type": "string", "const": "pass"}},
            "required": ["qualification"],
        }
        runner.validate_small_schema({"qualification": "pass"}, schema)
        with self.assertRaises(runner.RunnerError):
            runner.validate_small_schema({"qualification": "fail"}, schema)
        with self.assertRaises(runner.RunnerError):
            runner.validate_small_schema(
                {"qualification": "pass", "extra": True}, schema
            )

    def test_native_and_graph_record_exact_result(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = pathlib.Path(raw)
            result = root / "result.json"
            result.write_bytes(b'{"qualification":"pass"}\n')
            native = runner.record_native(result, root / "native")
            graph = runner.record_graph(result, root / "graph")
            self.assertEqual(len(native["commit"]), 40)
            self.assertEqual(len(native["tree"]), 40)
            self.assertEqual(len(graph["json_sha256"]), 64)
            self.assertEqual(len(graph["sqlite_sha256"]), 64)
            connection = runner.sqlite3.connect(root / "graph" / "graph.sqlite")
            try:
                self.assertEqual(
                    connection.execute("SELECT COUNT(*) FROM nodes").fetchone()[0], 2
                )
                self.assertEqual(
                    connection.execute("SELECT COUNT(*) FROM edges").fetchone()[0], 1
                )
            finally:
                connection.close()

    def test_manifest_uses_explicit_regular_files_only(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = pathlib.Path(raw)
            first = root / "first"
            second = root / "second"
            first.write_text("1")
            second.write_text("22")
            rows = runner.manifest([second, first], root)
            self.assertEqual([row["path"] for row in rows], ["first", "second"])
            self.assertEqual([row["bytes"] for row in rows], [1, 2])


if __name__ == "__main__":
    unittest.main()
