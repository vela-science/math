from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import runner  # noqa: E402


def make_repo(parent: pathlib.Path, name: str = "repo") -> pathlib.Path:
    repo = (parent / name).resolve()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "config",
            "user.email",
            "test@invalid.local",
        ],
        check=True,
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "remote",
            "add",
            "origin",
            "https://example.invalid/source.git",
        ],
        check=True,
    )
    (repo / "a.txt").write_text("a\n")
    subprocess.run(["git", "-C", str(repo), "add", "a.txt"], check=True)
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_AUTHOR_DATE": "2001-01-01T00:00:00Z",
            "GIT_COMMITTER_DATE": "2001-01-01T00:00:00Z",
        }
    )
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-q", "-m", "a"],
        check=True,
        env=environment,
    )
    return repo


class RunnerTests(unittest.TestCase):
    def test_docker_command_uses_real_repo_stdin_and_read_only_inputs(self) -> None:
        command = runner.docker_codex_command(
            image="sha256:" + "a" * 64,
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

    def test_docker_mount_delimiters_are_rejected(self) -> None:
        with self.assertRaisesRegex(runner.RunnerError, "mount delimiter"):
            runner.docker_codex_command(
                image="sha256:" + "a" * 64,
                repo=pathlib.Path("/source,bad"),
                auth=pathlib.Path("/auth"),
                schema=pathlib.Path("/schema"),
                output=pathlib.Path("/output"),
                model="m",
                reasoning="low",
            )

    def test_git_snapshot_requires_exact_clean_root_and_identity(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = make_repo(pathlib.Path(raw).resolve())
            snapshot = runner.git_snapshot(repo)
            self.assertTrue(snapshot.clean)
            self.assertEqual(
                snapshot.repository_id,
                "https://example.invalid/source.git",
            )
            runner.assert_expected_source(
                snapshot,
                repository_id=snapshot.repository_id,
                commit=snapshot.commit,
                tree=snapshot.tree,
                archive_sha256=snapshot.archive_sha256,
            )
            with self.assertRaisesRegex(runner.RunnerError, "identity does not match"):
                runner.assert_expected_source(
                    snapshot,
                    repository_id=snapshot.repository_id,
                    commit="0" * 40,
                    tree=snapshot.tree,
                    archive_sha256=snapshot.archive_sha256,
                )
            (repo / "a.txt").write_text("changed\n")
            with self.assertRaisesRegex(runner.RunnerError, "not clean"):
                runner.git_snapshot(repo)

    def test_subdirectory_relative_and_symlink_roots_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = pathlib.Path(raw).resolve()
            repo = make_repo(root)
            subdirectory = repo / "sub"
            subdirectory.mkdir()
            with self.assertRaises(runner.RunnerError):
                runner.validate_repository_root(subdirectory)
            with self.assertRaisesRegex(runner.RunnerError, "absolute"):
                runner.canonical_existing_path(
                    pathlib.Path("repo"), "repo", directory=True
                )
            alias = root / "alias"
            alias.symlink_to(repo)
            with self.assertRaisesRegex(runner.RunnerError, "symlink"):
                runner.canonical_existing_path(alias, "repo", directory=True)

    def test_linked_worktree_gitfile_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = pathlib.Path(raw).resolve()
            repo = make_repo(root)
            linked = root / "linked"
            subprocess.run(
                ["git", "-C", str(repo), "worktree", "add", "-q", str(linked)],
                check=True,
            )
            self.assertTrue((linked / ".git").is_file())
            with self.assertRaisesRegex(
                runner.RunnerError, "linked worktrees are unsupported"
            ):
                runner.validate_repository_root(linked)

    def test_image_digest_is_fail_closed(self) -> None:
        for image in (
            "vela:latest",
            "sha256:abc",
            "sha256:" + "A" * 64,
            "sha256:" + "a" * 63,
        ):
            with (
                self.subTest(image=image),
                self.assertRaisesRegex(runner.RunnerError, "exact sha256"),
            ):
                runner.inspect_docker_image(image)

    def test_supported_schema_subset(self) -> None:
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "qualification": {
                    "type": "string",
                    "const": "pass",
                    "enum": ["pass"],
                    "minLength": 4,
                    "maxLength": 4,
                    "pattern": "^pass$",
                }
            },
            "required": ["qualification"],
        }
        runner.validate_small_schema({"qualification": "pass"}, schema)
        for value in (
            {"qualification": "fail"},
            {"qualification": 1},
            {"qualification": "pass", "extra": "x"},
            {},
        ):
            with self.subTest(value=value), self.assertRaises(runner.RunnerError):
                runner.validate_small_schema(value, schema)

    def test_schema_rejects_every_unsupported_type_and_keyword(self) -> None:
        base = {
            "type": "object",
            "additionalProperties": False,
            "properties": {"x": {"type": "string"}},
            "required": ["x"],
        }
        hostile = []
        for unsupported_type in (
            "integer",
            "number",
            "boolean",
            "array",
            "object",
            "null",
        ):
            value = json.loads(json.dumps(base))
            value["properties"]["x"]["type"] = unsupported_type
            hostile.append(value)
        for keyword in (
            "oneOf",
            "anyOf",
            "allOf",
            "not",
            "if",
            "items",
            "minimum",
            "format",
            "default",
            "$ref",
            "patternProperties",
        ):
            value = json.loads(json.dumps(base))
            value[keyword] = []
            hostile.append(value)
        nested = json.loads(json.dumps(base))
        nested["properties"]["x"]["format"] = "email"
        hostile.append(nested)
        for schema in hostile:
            with self.subTest(schema=schema), self.assertRaises(runner.RunnerError):
                runner.validate_schema_definition(schema)

    def test_bounded_process_times_out_and_kills_tree(self) -> None:
        completed = runner.run_bounded(
            [
                sys.executable,
                "-c",
                "import subprocess,time; "
                "subprocess.Popen(['sleep','30']); time.sleep(30)",
            ],
            timeout_seconds=0.15,
            stdout_limit=1024,
            stderr_limit=1024,
        )
        self.assertEqual(completed.status, "timeout")
        self.assertLess(completed.elapsed_seconds, 2)

    def test_bounded_process_caps_streams(self) -> None:
        completed = runner.run_bounded(
            [sys.executable, "-c", "import sys; sys.stdout.write('x'*1000000)"],
            timeout_seconds=2,
            stdout_limit=1024,
            stderr_limit=1024,
        )
        self.assertEqual(completed.status, "stream_limit_exceeded")
        self.assertEqual(len(completed.stdout), 1024)

    def test_runtime_monitor_rejects_size_count_and_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = pathlib.Path(raw).resolve()
            check = runner.runtime_monitor(
                root, max_files=1, max_bytes=3, max_result_bytes=2
            )
            (root / "result.json").write_bytes(b"aaa")
            self.assertEqual(check(), "runtime_result_size_exceeded")
            (root / "result.json").write_bytes(b"aa")
            (root / "b").write_bytes(b"b")
            self.assertEqual(check(), "runtime_file_count_exceeded")
            (root / "b").unlink()
            (root / "link").symlink_to(root / "result.json")
            self.assertEqual(check(), "runtime_symlink_rejected")

    def test_native_and_graph_replay_is_byte_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = pathlib.Path(raw).resolve()
            result = root / "result.json"
            result.write_bytes(b'{"qualification":"pass"}\n')
            provenance = runner.canonical_json(
                {
                    "schema": "vela.result-runner.provenance.v1",
                    "source": {
                        "repository_id": "https://example.invalid/source.git",
                        "commit": "a" * 40,
                        "tree": "b" * 40,
                        "archive_sha256": "c" * 64,
                    },
                }
            )
            first_native = runner.record_native(result, provenance, root / "native-1")
            second_native = runner.record_native(result, provenance, root / "native-2")
            first_graph = runner.record_graph(result, provenance, root / "graph-1")
            second_graph = runner.record_graph(result, provenance, root / "graph-2")
            self.assertEqual(first_native, second_native)
            self.assertEqual(first_graph, second_graph)
            for name in (
                "result.json",
                "provenance.json",
                "graph.json",
                "graph.sqlite",
            ):
                self.assertEqual(
                    (root / "graph-1" / name).read_bytes(),
                    (root / "graph-2" / name).read_bytes(),
                )
            connection = runner.sqlite3.connect(root / "graph-1" / "graph.sqlite")
            try:
                self.assertEqual(
                    connection.execute("SELECT COUNT(*) FROM nodes").fetchone()[0],
                    3,
                )
                self.assertEqual(
                    connection.execute("SELECT COUNT(*) FROM edges").fetchone()[0],
                    2,
                )
                self.assertEqual(
                    connection.execute("PRAGMA integrity_check").fetchone()[0],
                    "ok",
                )
            finally:
                connection.close()

    def test_provenance_binds_all_execution_identities(self) -> None:
        source = runner.GitSnapshot(
            repository_id="https://example.invalid/source.git",
            commit="a" * 40,
            tree="b" * 40,
            clean=True,
            shallow=False,
            archive_sha256="c" * 64,
        )
        image = runner.DockerImage(
            "sha256:" + "d" * 64,
            "sha256:" + "d" * 64,
            "linux",
            "arm64",
        )
        value = runner.semantic_invocation(
            model="gpt-5.6-sol",
            reasoning="low",
            image=image,
            source=source,
            prompt_sha256="e" * 64,
            schema_sha256="f" * 64,
            runner_sha256="1" * 64,
        )
        self.assertEqual(value["source"]["commit"], "a" * 40)
        self.assertEqual(value["image"]["resolved_id"], "sha256:" + "d" * 64)
        self.assertEqual(value["model"], "gpt-5.6-sol")
        self.assertEqual(len(value["identity_sha256"]), 64)

    def test_credential_scan_detects_and_never_echoes_secret(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = pathlib.Path(raw).resolve()
            secret = root / "secret"
            field = "access_" + "token"
            secret.write_text('{"' + field + '":"very-secret-token-value-12345"}')
            findings = runner.credential_findings([secret])
            self.assertEqual(len(findings), 1)
            self.assertNotIn("very-secret", json.dumps(findings))

    def test_manifest_uses_explicit_regular_files_only(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = pathlib.Path(raw).resolve()
            first = root / "first"
            second = root / "second"
            first.write_text("1")
            second.write_text("22")
            rows = runner.manifest([second, first], root)
            self.assertEqual([row["path"] for row in rows], ["first", "second"])
            self.assertEqual([row["bytes"] for row in rows], [1, 2])


if __name__ == "__main__":
    unittest.main()
