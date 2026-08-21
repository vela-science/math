#!/usr/bin/env python3
"""Run one bounded Codex candidate from a real Git checkout.

The runner deliberately owns execution mechanics, not scientific authority.
It records exact output through Native Git and JSON/SQLite routes.  The optional
Vela route is disposable and always rejects its qualification-only Proposal.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import sqlite3
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any, Iterable


class RunnerError(RuntimeError):
    """A fail-closed runner precondition or execution error."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: pathlib.Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def write_json(path: pathlib.Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json(value))


def run(
    argv: list[str],
    *,
    cwd: pathlib.Path | None = None,
    env: dict[str, str] | None = None,
    input_bytes: bytes | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(
        argv,
        cwd=cwd,
        env=env,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and completed.returncode != 0:
        stderr = completed.stderr.decode(errors="replace").strip()
        raise RunnerError(
            f"command failed ({completed.returncode}): {argv[0]}: {stderr}"
        )
    return completed


def git(repo: pathlib.Path, *args: str) -> str:
    return run(["git", "-C", str(repo), *args]).stdout.decode().strip()


@dataclass(frozen=True)
class GitSnapshot:
    commit: str
    tree: str
    clean: bool
    shallow: bool
    archive_sha256: str

    def as_json(self) -> dict[str, Any]:
        return {
            "archive_sha256": self.archive_sha256,
            "clean": self.clean,
            "commit": self.commit,
            "shallow": self.shallow,
            "tree": self.tree,
        }


def git_snapshot(repo: pathlib.Path) -> GitSnapshot:
    if not repo.is_absolute() or not repo.is_dir():
        raise RunnerError("source repository must be an existing absolute directory")
    if git(repo, "rev-parse", "--is-inside-work-tree") != "true":
        raise RunnerError("source path is not a Git working tree")
    status = git(repo, "status", "--porcelain=v1", "--untracked-files=all")
    if status:
        raise RunnerError("source Git working tree is not clean")
    archive = run(["git", "-C", str(repo), "archive", "--format=tar", "HEAD"]).stdout
    return GitSnapshot(
        commit=git(repo, "rev-parse", "HEAD"),
        tree=git(repo, "rev-parse", "HEAD^{tree}"),
        clean=True,
        shallow=git(repo, "rev-parse", "--is-shallow-repository") == "true",
        archive_sha256=sha256_bytes(archive),
    )


def ensure_regular_absolute(path: pathlib.Path, label: str) -> pathlib.Path:
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise RunnerError(f"{label} must be an absolute, non-symlink regular file")
    return path


def validate_small_schema(value: Any, schema: dict[str, Any]) -> None:
    """Validate the deliberately small object schema supported by this runner.

    Full scientific schemas remain external and should use their canonical
    validators. This catches malformed qualification and candidate envelopes
    before recorders consume them without introducing a schema framework.
    """

    if schema.get("type") != "object" or not isinstance(value, dict):
        raise RunnerError("output must satisfy an object schema")
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    if not isinstance(properties, dict) or not isinstance(required, list):
        raise RunnerError("unsupported output schema")
    missing = [name for name in required if name not in value]
    if missing:
        raise RunnerError(f"output is missing required fields: {', '.join(missing)}")
    if schema.get("additionalProperties") is False:
        extras = sorted(set(value) - set(properties))
        if extras:
            raise RunnerError(f"output has unexpected fields: {', '.join(extras)}")
    for name, rule in properties.items():
        if name not in value:
            continue
        if rule.get("type") == "string" and not isinstance(value[name], str):
            raise RunnerError(f"output field {name!r} must be a string")
        if "const" in rule and value[name] != rule["const"]:
            raise RunnerError(f"output field {name!r} does not match its constant")


def docker_codex_command(
    *,
    image: str,
    repo: pathlib.Path,
    auth: pathlib.Path,
    schema: pathlib.Path,
    output: pathlib.Path,
    model: str,
    reasoning: str,
) -> list[str]:
    return [
        "docker",
        "run",
        "--rm",
        "-i",
        "--mount",
        f"type=bind,src={repo},dst=/repo,readonly",
        "--mount",
        f"type=bind,src={auth},dst=/root/.codex/auth.json,readonly",
        "--mount",
        f"type=bind,src={schema},dst=/inputs/output.schema.json,readonly",
        "--mount",
        f"type=bind,src={output},dst=/output",
        "--workdir",
        "/repo",
        "--entrypoint",
        "codex",
        image,
        "exec",
        "--ephemeral",
        "--ignore-user-config",
        "--ignore-rules",
        "-m",
        model,
        "-c",
        f'model_reasoning_effort="{reasoning}"',
        "-c",
        'service_tier="default"',
        "-s",
        "danger-full-access",
        "-C",
        "/repo",
        "--output-schema",
        "/inputs/output.schema.json",
        "--json",
        "-o",
        "/output/result.json",
        "-",
    ]


def record_native(result: pathlib.Path, destination: pathlib.Path) -> dict[str, str]:
    destination.mkdir(parents=True)
    run(["git", "init", "-q", str(destination)])
    git(destination, "config", "user.name", "Vela Result Runner")
    git(destination, "config", "user.email", "runner@invalid.local")
    shutil.copyfile(result, destination / "result.json")
    git(destination, "add", "--", "result.json")
    git(destination, "commit", "-q", "-m", "Retain exact Result output")
    return {
        "commit": git(destination, "rev-parse", "HEAD"),
        "tree": git(destination, "rev-parse", "HEAD^{tree}"),
    }


def record_graph(result: pathlib.Path, destination: pathlib.Path) -> dict[str, str]:
    destination.mkdir(parents=True)
    result_bytes = result.read_bytes()
    digest = sha256_bytes(result_bytes)
    graph = {
        "edges": [{"from": "run", "kind": "produced", "to": f"result:{digest}"}],
        "nodes": [
            {"id": "run", "kind": "execution"},
            {"id": f"result:{digest}", "kind": "result", "sha256": digest},
        ],
        "schema": "vela.result-runner.graph.v1",
    }
    graph_json = destination / "graph.json"
    graph_db = destination / "graph.sqlite"
    write_json(graph_json, graph)
    connection = sqlite3.connect(graph_db)
    try:
        connection.execute(
            "CREATE TABLE nodes (id TEXT PRIMARY KEY, kind TEXT NOT NULL, payload BLOB NOT NULL)"
        )
        connection.execute(
            "CREATE TABLE edges (source TEXT NOT NULL, kind TEXT NOT NULL, target TEXT NOT NULL)"
        )
        for node in graph["nodes"]:
            connection.execute(
                "INSERT INTO nodes VALUES (?, ?, ?)",
                (node["id"], node["kind"], canonical_json(node)),
            )
        for edge in graph["edges"]:
            connection.execute(
                "INSERT INTO edges VALUES (?, ?, ?)",
                (edge["from"], edge["kind"], edge["to"]),
            )
        connection.commit()
    finally:
        connection.close()
    return {
        "json_sha256": sha256_file(graph_json),
        "sqlite_sha256": sha256_file(graph_db),
    }


def manifest(paths: Iterable[pathlib.Path], root: pathlib.Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(set(paths)):
        if path.is_symlink() or not path.is_file():
            raise RunnerError(f"manifest input is not a regular file: {path}")
        rows.append(
            {
                "bytes": path.stat().st_size,
                "path": str(path.relative_to(root)),
                "sha256": sha256_file(path),
            }
        )
    return rows


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=pathlib.Path)
    parser.add_argument("--prompt", required=True, type=pathlib.Path)
    parser.add_argument("--schema", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    parser.add_argument("--image", required=True)
    parser.add_argument("--auth", required=True, type=pathlib.Path)
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument(
        "--reasoning", default="low", choices=("low", "medium", "high", "xhigh")
    )
    parser.add_argument("--max-output-bytes", default=8192, type=int)
    parser.add_argument("--disposable-vela", action="store_true")
    parser.add_argument("--vela-bin", type=pathlib.Path)
    parser.add_argument("--vela-sha256")
    parser.add_argument(
        "--skip-docker",
        action="store_true",
        help="Validate inputs and emit the exact Docker command without execution",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    repo = args.repo.resolve(strict=True)
    prompt = ensure_regular_absolute(args.prompt.resolve(strict=True), "prompt")
    schema_path = ensure_regular_absolute(args.schema.resolve(strict=True), "schema")
    auth = ensure_regular_absolute(args.auth.resolve(strict=True), "OAuth file")
    output_candidate = args.output.resolve()
    if output_candidate == repo or repo in output_candidate.parents:
        raise RunnerError("output directory must be outside the source repository")
    if args.output.exists():
        raise RunnerError("output directory must not already exist")
    args.output.mkdir(parents=True)
    output = args.output.resolve()

    before = git_snapshot(repo)
    if run(["docker", "context", "show"]).stdout.decode().strip() != "desktop-linux":
        raise RunnerError("Docker context must be desktop-linux")
    run(["docker", "image", "inspect", args.image])

    command = docker_codex_command(
        image=args.image,
        repo=repo,
        auth=auth,
        schema=schema_path,
        output=output,
        model=args.model,
        reasoning=args.reasoning,
    )
    write_json(
        output / "invocation.json",
        {
            "argv": command,
            "cwd_in_container": "/repo",
            "source_read_only": True,
            "oauth_read_only": True,
        },
    )
    if args.skip_docker:
        write_json(
            output / "receipt.json",
            {
                "schema": "vela.result-runner.receipt.v1",
                "status": "dry_run",
                "git_source": {"before": before.as_json()},
            },
        )
        return 0

    started = time.monotonic()
    completed = run(command, input_bytes=prompt.read_bytes(), check=False)
    elapsed = time.monotonic() - started
    receipts = output / "receipts"
    receipts.mkdir()
    (receipts / "codex.stdout").write_bytes(completed.stdout)
    (receipts / "codex.stderr").write_bytes(completed.stderr)
    (receipts / "exit-code.txt").write_text(f"{completed.returncode}\n")
    if completed.returncode != 0:
        raise RunnerError(f"Codex execution failed with exit {completed.returncode}")

    result = output / "result.json"
    if not result.is_file() or result.is_symlink():
        raise RunnerError("Codex did not produce a regular result.json")
    if result.stat().st_size > args.max_output_bytes:
        raise RunnerError("result.json exceeds the configured byte limit")
    value = json.loads(result.read_text())
    schema = json.loads(schema_path.read_text())
    validate_small_schema(value, schema)
    after = git_snapshot(repo)
    if after != before:
        raise RunnerError("source Git identity or bytes changed during execution")

    native = record_native(result, output / "routes" / "native")
    graph = record_graph(result, output / "routes" / "graph")
    routes: dict[str, Any] = {"graph": graph, "native": native}
    if args.disposable_vela:
        from vela_disposable import record_disposable

        if args.vela_bin is None or args.vela_sha256 is None:
            raise RunnerError("--disposable-vela requires --vela-bin and --vela-sha256")
        vela_bin = ensure_regular_absolute(
            args.vela_bin.resolve(strict=True), "Vela binary"
        )
        routes["vela_disposable"] = record_disposable(
            result=result,
            destination=output / "routes" / "vela",
            vela_bin=vela_bin,
            expected_vela_sha256=args.vela_sha256,
            method=pathlib.Path(__file__).with_name("review-method.json"),
        )
    write_json(
        output / "receipt.json",
        {
            "elapsed_seconds": round(elapsed, 3),
            "git_source": {
                "after": after.as_json(),
                "before": before.as_json(),
                "container_cwd": "/repo",
            },
            "output": {"bytes": result.stat().st_size, "sha256": sha256_file(result)},
            "routes": routes,
            "schema": "vela.result-runner.receipt.v1",
            "status": "pass",
        },
    )
    files = [
        path
        for path in output.rglob("*")
        if path.is_file() and path.name != "manifest.json"
    ]
    write_json(
        output / "manifest.json",
        {"files": manifest(files, output), "schema": "vela.result-runner.manifest.v1"},
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RunnerError as error:
        print(f"result-runner: {error}", file=sys.stderr)
        raise SystemExit(1)
