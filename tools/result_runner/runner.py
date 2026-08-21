#!/usr/bin/env python3
"""Run one bounded Codex candidate from an exact clean Git repository root."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import platform
import re
import shutil
import signal
import sqlite3
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable


IMAGE_RE = re.compile(r"sha256:[0-9a-f]{64}")
HEX_RE = re.compile(r"[0-9a-f]{64}")
GIT_RE = re.compile(r"[0-9a-f]{40}")
MOUNT_FORBIDDEN = {",", "\n", "\r", "\x00"}
FIXED_GIT_DATE = "2000-01-01T00:00:00Z"
HARD_MAX_PROMPT_BYTES = 1 << 20
HARD_MAX_SCHEMA_BYTES = 1 << 20
HARD_MAX_RESULT_BYTES = 1 << 20
HARD_MAX_STREAM_BYTES = 8 << 20
HARD_MAX_RUNTIME_BYTES = 16 << 20
HARD_MAX_RUNTIME_FILES = 256
HARD_MAX_TIMEOUT_SECONDS = 3600.0
SCHEMA_TOP_LEVEL_KEYS = {
    "additionalProperties",
    "properties",
    "required",
    "type",
}
SCHEMA_PROPERTY_KEYS = {
    "const",
    "enum",
    "maxLength",
    "minLength",
    "type",
}
CREDENTIAL_PATTERNS = (
    re.compile(rb"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(rb"(?i)bearer\s+[A-Za-z0-9._~+/-]{20,}"),
    re.compile(rb'(?i)"(?:access_token|refresh_token|api_key)"\s*:\s*"[^"\n]+"'),
    re.compile(rb"-----BEGIN (?:OPENSSH|RSA|EC) PRIVATE KEY-----"),
)


class RunnerError(RuntimeError):
    """A typed fail-closed runner error."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class CommandResult:
    argv: tuple[str, ...]
    returncode: int
    stdout: bytes
    stderr: bytes
    elapsed_seconds: float
    status: str


@dataclass(frozen=True)
class GitSnapshot:
    repository_id: str
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
            "repository_id": self.repository_id,
            "shallow": self.shallow,
            "tree": self.tree,
        }


@dataclass(frozen=True)
class DockerImage:
    requested_digest: str
    resolved_id: str
    os: str
    architecture: str

    def as_json(self) -> dict[str, str]:
        return {
            "architecture": self.architecture,
            "os": self.os,
            "requested_digest": self.requested_digest,
            "resolved_id": self.resolved_id,
        }


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: pathlib.Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def write_json(path: pathlib.Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json(value))


def _terminate_process_group(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except (PermissionError, ProcessLookupError):
        # The session leader can exit between poll and killpg. Fall back to
        # the child handle, which is either still ours or already terminal.
        try:
            process.terminate()
        except ProcessLookupError:
            return
    try:
        process.wait(timeout=0.5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (PermissionError, ProcessLookupError):
            try:
                process.kill()
            except ProcessLookupError:
                pass


def run_bounded(
    argv: list[str],
    *,
    cwd: pathlib.Path | None = None,
    env: dict[str, str] | None = None,
    input_bytes: bytes | None = None,
    timeout_seconds: float = 120.0,
    stdout_limit: int = 8 << 20,
    stderr_limit: int = 8 << 20,
    monitor: Callable[[], str | None] | None = None,
) -> CommandResult:
    """Run with bounded streams, wall time, and process-tree cancellation."""

    process = subprocess.Popen(
        argv,
        cwd=cwd,
        env=env,
        stdin=subprocess.PIPE if input_bytes is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    started = time.monotonic()
    stdout_chunks: list[bytes] = []
    stderr_chunks: list[bytes] = []
    stream_overflow = threading.Event()

    def consume(stream: Any, chunks: list[bytes], limit: int) -> None:
        retained = 0
        while True:
            chunk = stream.read(65536)
            if not chunk:
                return
            remaining = max(0, limit - retained)
            if remaining:
                chunks.append(chunk[:remaining])
                retained += min(len(chunk), remaining)
            if len(chunk) > remaining:
                stream_overflow.set()

    readers = [
        threading.Thread(
            target=consume, args=(process.stdout, stdout_chunks, stdout_limit)
        ),
        threading.Thread(
            target=consume, args=(process.stderr, stderr_chunks, stderr_limit)
        ),
    ]
    for reader in readers:
        reader.start()

    def provide_input() -> None:
        assert process.stdin is not None
        try:
            process.stdin.write(input_bytes or b"")
            process.stdin.flush()
        except BrokenPipeError:
            pass
        finally:
            process.stdin.close()

    writer = None
    if input_bytes is not None:
        writer = threading.Thread(target=provide_input)
        writer.start()

    status = "completed"
    while process.poll() is None:
        if stream_overflow.is_set():
            status = "stream_limit_exceeded"
            _terminate_process_group(process)
            break
        if time.monotonic() - started > timeout_seconds:
            status = "timeout"
            _terminate_process_group(process)
            break
        if monitor is not None:
            violation = monitor()
            if violation:
                status = violation
                _terminate_process_group(process)
                break
        time.sleep(0.02)
    process.wait()
    for reader in readers:
        reader.join()
    assert process.stdout is not None
    assert process.stderr is not None
    process.stdout.close()
    process.stderr.close()
    if writer is not None:
        writer.join()
    if stream_overflow.is_set() and status == "completed":
        status = "stream_limit_exceeded"
    if monitor is not None and status == "completed":
        # The child can create its last file after the final in-loop census and
        # exit before the next poll. Acceptance therefore requires a complete
        # census after termination and stream/input joins.
        violation = monitor()
        if violation:
            status = violation
    return CommandResult(
        argv=tuple(argv),
        returncode=process.returncode,
        stdout=b"".join(stdout_chunks),
        stderr=b"".join(stderr_chunks),
        elapsed_seconds=time.monotonic() - started,
        status=status,
    )


def run(
    argv: list[str],
    *,
    cwd: pathlib.Path | None = None,
    env: dict[str, str] | None = None,
    input_bytes: bytes | None = None,
    check: bool = True,
    timeout_seconds: float = 120.0,
    stdout_limit: int = 8 << 20,
    stderr_limit: int = 8 << 20,
) -> CommandResult:
    completed = run_bounded(
        argv,
        cwd=cwd,
        env=env,
        input_bytes=input_bytes,
        timeout_seconds=timeout_seconds,
        stdout_limit=stdout_limit,
        stderr_limit=stderr_limit,
    )
    if completed.status != "completed":
        raise RunnerError(
            "command_bound", f"command stopped: {completed.status}: {argv[0]}"
        )
    if check and completed.returncode != 0:
        stderr = completed.stderr.decode(errors="replace").strip()
        raise RunnerError(
            "command_failed",
            f"command failed ({completed.returncode}): {argv[0]}: {stderr}",
        )
    return completed


def git(repo: pathlib.Path, *args: str) -> str:
    return run(["git", "-C", str(repo), *args]).stdout.decode().strip()


def _reject_mount_delimiters(value: str, label: str) -> None:
    if any(character in value for character in MOUNT_FORBIDDEN):
        raise RunnerError("mount_path", f"{label} contains a Docker mount delimiter")


def canonical_existing_path(
    raw: pathlib.Path,
    label: str,
    *,
    file: bool = False,
    directory: bool = False,
) -> pathlib.Path:
    if not raw.is_absolute():
        raise RunnerError("path_not_absolute", f"{label} must be absolute")
    _reject_mount_delimiters(str(raw), label)
    if raw.is_symlink():
        raise RunnerError("path_symlink", f"{label} must not be a symlink")
    try:
        resolved = raw.resolve(strict=True)
    except FileNotFoundError as error:
        raise RunnerError("path_missing", f"{label} does not exist") from error
    if resolved != raw:
        raise RunnerError(
            "path_not_canonical", f"{label} must be canonical without aliases"
        )
    current = pathlib.Path(raw.anchor)
    for part in raw.parts[1:]:
        current /= part
        if current.is_symlink():
            raise RunnerError("path_symlink", f"{label} contains a symlink component")
    if file and not raw.is_file():
        raise RunnerError("path_not_file", f"{label} must be a regular file")
    if directory and not raw.is_dir():
        raise RunnerError("path_not_directory", f"{label} must be a directory")
    return raw


def prepare_output_path(raw: pathlib.Path, repo: pathlib.Path) -> pathlib.Path:
    if not raw.is_absolute():
        raise RunnerError("path_not_absolute", "output directory must be absolute")
    _reject_mount_delimiters(str(raw), "output directory")
    if raw.exists() or raw.is_symlink():
        raise RunnerError("output_collision", "output directory must not already exist")
    parent = canonical_existing_path(raw.parent, "output parent", directory=True)
    candidate = parent / raw.name
    if candidate != raw:
        raise RunnerError("path_not_canonical", "output directory must be canonical")
    if candidate == repo or repo in candidate.parents:
        raise RunnerError("output_in_source", "output directory must be outside source")
    return candidate


def validate_repository_root(repo: pathlib.Path) -> None:
    canonical_existing_path(repo, "source repository", directory=True)
    marker = repo / ".git"
    if marker.is_symlink() or not marker.is_dir():
        raise RunnerError(
            "unsupported_git_layout",
            "source root must contain an in-tree .git directory; "
            "gitfiles and linked worktrees are unsupported",
        )
    top = pathlib.Path(git(repo, "rev-parse", "--show-toplevel"))
    if top != repo:
        raise RunnerError(
            "not_repository_root", "--repo must equal the physical Git top level"
        )
    git_dir = pathlib.Path(git(repo, "rev-parse", "--absolute-git-dir"))
    if git_dir != marker:
        raise RunnerError(
            "unsupported_git_layout", "Git directory must be exactly <repo>/.git"
        )


def git_snapshot(repo: pathlib.Path) -> GitSnapshot:
    validate_repository_root(repo)
    status = git(repo, "status", "--porcelain=v1", "--untracked-files=all")
    if status:
        raise RunnerError("source_dirty", "source Git working tree is not clean")
    origin = git(repo, "config", "--get", "remote.origin.url")
    if not origin:
        raise RunnerError(
            "source_identity", "source repository has no remote.origin.url"
        )
    archive = run(
        ["git", "-C", str(repo), "archive", "--format=tar", "HEAD"],
        stdout_limit=64 << 20,
    ).stdout
    return GitSnapshot(
        repository_id=origin,
        commit=git(repo, "rev-parse", "HEAD"),
        tree=git(repo, "rev-parse", "HEAD^{tree}"),
        clean=True,
        shallow=git(repo, "rev-parse", "--is-shallow-repository") == "true",
        archive_sha256=sha256_bytes(archive),
    )


def assert_expected_source(
    snapshot: GitSnapshot,
    *,
    repository_id: str,
    commit: str,
    tree: str,
    archive_sha256: str,
) -> None:
    if (
        snapshot.repository_id != repository_id
        or snapshot.commit != commit
        or snapshot.tree != tree
        or snapshot.archive_sha256 != archive_sha256
    ):
        raise RunnerError(
            "source_identity_mismatch",
            "source repository identity does not match frozen inputs",
        )


def inspect_docker_image(image: str) -> DockerImage:
    if not IMAGE_RE.fullmatch(image):
        raise RunnerError(
            "image_digest",
            "image must be an exact sha256:<64 lowercase hex> digest",
        )
    completed = run(["docker", "image", "inspect", image])
    try:
        values = json.loads(completed.stdout)
        value = values[0]
        resolved = DockerImage(image, value["Id"], value["Os"], value["Architecture"])
    except (IndexError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise RunnerError(
            "image_inspect", "Docker image inspection returned invalid JSON"
        ) from error
    if resolved.resolved_id != image or resolved.os != "linux":
        raise RunnerError(
            "image_identity_mismatch", "Docker image identity/platform mismatch"
        )
    return resolved


def read_limited(path: pathlib.Path, limit: int, label: str) -> bytes:
    if path.stat().st_size > limit:
        raise RunnerError("input_limit", f"{label} exceeds {limit} bytes")
    return path.read_bytes()


def load_json_limited(path: pathlib.Path, limit: int, label: str) -> Any:
    try:
        return json.loads(read_limited(path, limit, label))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RunnerError("invalid_json", f"{label} is not valid UTF-8 JSON") from error


def validate_schema_definition(schema: Any) -> dict[str, Any]:
    if not isinstance(schema, dict):
        raise RunnerError("unsupported_schema", "schema must be an object")
    unsupported = sorted(set(schema) - SCHEMA_TOP_LEVEL_KEYS)
    if unsupported:
        raise RunnerError(
            "unsupported_schema",
            f"unsupported schema keywords: {', '.join(unsupported)}",
        )
    if schema.get("type") != "object":
        raise RunnerError(
            "unsupported_schema", "only top-level object schemas are supported"
        )
    properties = schema.get("properties")
    required = schema.get("required")
    if not isinstance(properties, dict) or not isinstance(required, list):
        raise RunnerError(
            "unsupported_schema",
            "properties object and required array are mandatory",
        )
    if schema.get("additionalProperties") is not False:
        raise RunnerError("unsupported_schema", "additionalProperties must be false")
    if any(not isinstance(name, str) for name in required) or len(set(required)) != len(
        required
    ):
        raise RunnerError(
            "unsupported_schema",
            "required must contain unique string field names",
        )
    if not set(required) <= set(properties):
        raise RunnerError(
            "unsupported_schema",
            "every required field must have a property rule",
        )
    for name, rule in properties.items():
        if not isinstance(name, str) or not isinstance(rule, dict):
            raise RunnerError(
                "unsupported_schema",
                "property names and rules must be objects",
            )
        unknown = sorted(set(rule) - SCHEMA_PROPERTY_KEYS)
        if unknown:
            raise RunnerError(
                "unsupported_schema",
                f"unsupported rule for {name}: {', '.join(unknown)}",
            )
        if rule.get("type") != "string":
            raise RunnerError(
                "unsupported_schema",
                f"property {name} must use supported type string",
            )
        for bound in ("minLength", "maxLength"):
            if bound in rule and (
                not isinstance(rule[bound], int)
                or isinstance(rule[bound], bool)
                or rule[bound] < 0
            ):
                raise RunnerError(
                    "unsupported_schema",
                    f"{name}.{bound} must be a nonnegative integer",
                )
        if rule.get("minLength", 0) > rule.get("maxLength", sys.maxsize):
            raise RunnerError(
                "unsupported_schema", f"{name} has inconsistent length bounds"
            )
        if "const" in rule and not isinstance(rule["const"], str):
            raise RunnerError("unsupported_schema", f"{name}.const must be a string")
        if "enum" in rule and (
            not isinstance(rule["enum"], list)
            or not rule["enum"]
            or any(not isinstance(item, str) for item in rule["enum"])
            or len(set(rule["enum"])) != len(rule["enum"])
        ):
            raise RunnerError(
                "unsupported_schema",
                f"{name}.enum must be unique nonempty strings",
            )
    return schema


def validate_small_schema(value: Any, schema: dict[str, Any]) -> None:
    schema = validate_schema_definition(schema)
    if not isinstance(value, dict):
        raise RunnerError("schema_validation", "output must be an object")
    properties = schema["properties"]
    missing = [name for name in schema["required"] if name not in value]
    if missing:
        raise RunnerError(
            "schema_validation",
            f"output is missing required fields: {', '.join(missing)}",
        )
    extras = sorted(set(value) - set(properties))
    if extras:
        raise RunnerError(
            "schema_validation",
            f"output has unexpected fields: {', '.join(extras)}",
        )
    for name, item in value.items():
        rule = properties[name]
        if not isinstance(item, str):
            raise RunnerError(
                "schema_validation", f"output field {name!r} must be a string"
            )
        if "const" in rule and item != rule["const"]:
            raise RunnerError(
                "schema_validation",
                f"output field {name!r} does not match const",
            )
        if "enum" in rule and item not in rule["enum"]:
            raise RunnerError(
                "schema_validation", f"output field {name!r} is outside enum"
            )
        if len(item) < rule.get("minLength", 0) or len(item) > rule.get(
            "maxLength", sys.maxsize
        ):
            raise RunnerError(
                "schema_validation",
                f"output field {name!r} violates length bounds",
            )


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
    for path, label in (
        (repo, "repo"),
        (auth, "auth"),
        (schema, "schema"),
        (output, "output"),
    ):
        _reject_mount_delimiters(str(path), label)
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


def semantic_invocation(
    *,
    model: str,
    reasoning: str,
    image: DockerImage,
    source: GitSnapshot,
    prompt_sha256: str,
    schema_sha256: str,
    runner_sha256: str,
) -> dict[str, Any]:
    value = {
        "container_cwd": "/repo",
        "image": image.as_json(),
        "model": model,
        "oauth_mount": {
            "destination": "/root/.codex/auth.json",
            "read_only": True,
        },
        "prompt_sha256": prompt_sha256,
        "reasoning": reasoning,
        "runner_sha256": runner_sha256,
        "schema_sha256": schema_sha256,
        "service_tier": "default",
        "source": source.as_json(),
        "source_mount": {"destination": "/repo", "read_only": True},
    }
    return value | {"identity_sha256": sha256_bytes(canonical_json(value))}


def canonical_provenance(
    *,
    invocation: dict[str, Any],
    result_sha256: str,
    result_bytes: int,
) -> dict[str, Any]:
    return {
        "invocation": invocation,
        "result": {"bytes": result_bytes, "sha256": result_sha256},
        "schema": "vela.result-runner.provenance.v1",
    }


def record_native(
    result: pathlib.Path, provenance: bytes, destination: pathlib.Path
) -> dict[str, str]:
    destination.mkdir(parents=True)
    run(["git", "init", "-q", "--initial-branch=main", str(destination)])
    git(destination, "config", "user.name", "Vela Result Runner")
    git(destination, "config", "user.email", "runner@invalid.local")
    shutil.copyfile(result, destination / "result.json")
    (destination / "provenance.json").write_bytes(provenance)
    for name in ("result.json", "provenance.json"):
        (destination / name).chmod(0o644)
    git(destination, "add", "--", "result.json", "provenance.json")
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_AUTHOR_DATE": FIXED_GIT_DATE,
            "GIT_COMMITTER_DATE": FIXED_GIT_DATE,
            "TZ": "UTC",
        }
    )
    run(
        [
            "git",
            "-C",
            str(destination),
            "commit",
            "-q",
            "-m",
            "Retain exact Result output",
        ],
        env=environment,
    )
    return {
        "commit": git(destination, "rev-parse", "HEAD"),
        "provenance_sha256": sha256_file(destination / "provenance.json"),
        "result_sha256": sha256_file(destination / "result.json"),
        "tree": git(destination, "rev-parse", "HEAD^{tree}"),
    }


def record_graph(
    result: pathlib.Path, provenance: bytes, destination: pathlib.Path
) -> dict[str, Any]:
    destination.mkdir(parents=True)
    result_bytes = result.read_bytes()
    result_digest = sha256_bytes(result_bytes)
    provenance_digest = sha256_bytes(provenance)
    (destination / "result.json").write_bytes(result_bytes)
    (destination / "provenance.json").write_bytes(provenance)
    graph = {
        "edges": [
            {
                "from": "run",
                "kind": "produced",
                "to": f"result:{result_digest}",
            },
            {
                "from": "run",
                "kind": "bound_by",
                "to": f"provenance:{provenance_digest}",
            },
        ],
        "nodes": [
            {"id": "run", "kind": "execution"},
            {
                "id": f"provenance:{provenance_digest}",
                "kind": "provenance",
                "sha256": provenance_digest,
            },
            {
                "id": f"result:{result_digest}",
                "kind": "result",
                "sha256": result_digest,
            },
        ],
        "schema": "vela.result-runner.graph.v1",
    }
    graph_json = destination / "graph.json"
    graph_db = destination / "graph.sqlite"
    projection_json = destination / "sqlite-projection.json"
    write_json(graph_json, graph)
    connection = sqlite3.connect(graph_db)
    try:
        connection.execute("PRAGMA journal_mode=OFF")
        connection.execute("PRAGMA synchronous=OFF")
        connection.execute("PRAGMA page_size=4096")
        connection.execute(
            "CREATE TABLE nodes "
            "(id TEXT PRIMARY KEY, kind TEXT NOT NULL, payload BLOB NOT NULL)"
        )
        connection.execute(
            "CREATE TABLE edges "
            "(source TEXT NOT NULL, kind TEXT NOT NULL, target TEXT NOT NULL)"
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
        connection.execute("VACUUM")
        sqlite_source_id = connection.execute("SELECT sqlite_source_id()").fetchone()[0]
        sqlite_compile_options = sorted(
            row[0] for row in connection.execute("PRAGMA compile_options").fetchall()
        )
    finally:
        connection.close()
    logical_content = {
        "edges": sorted(
            graph["edges"], key=lambda item: (item["from"], item["kind"], item["to"])
        ),
        "nodes": sorted(graph["nodes"], key=lambda item: item["id"]),
        "schema": "vela.result-runner.sqlite-logical.v1",
    }
    replayed_logical_content = read_sqlite_logical_content(graph_db)
    if replayed_logical_content != logical_content:
        raise RunnerError(
            "sqlite_logical_content",
            "SQLite projection does not match canonical Graph content",
        )
    logical_content_sha256 = sha256_bytes(canonical_json(logical_content))
    sqlite_sha256 = sha256_file(graph_db)
    serializer = {
        "platform_machine": platform.machine(),
        "platform_system": platform.system(),
        "python_cache_tag": sys.implementation.cache_tag,
        "python_executable_sha256": sha256_file(
            pathlib.Path(sys.executable).resolve(strict=True)
        ),
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "sqlite_compile_options": sqlite_compile_options,
        "sqlite_source_id": sqlite_source_id,
        "sqlite_version": sqlite3.sqlite_version,
    }
    write_json(
        projection_json,
        {
            "byte_replay_scope": "exact recorded serializer environment only",
            "byte_sha256": sqlite_sha256,
            "logical_content_sha256": logical_content_sha256,
            "portable_replay": "integrity plus canonical logical content",
            "schema": "vela.result-runner.sqlite-projection.v1",
            "serializer": serializer,
        },
    )
    return {
        "json_sha256": sha256_file(graph_json),
        "provenance_sha256": sha256_file(destination / "provenance.json"),
        "result_sha256": sha256_file(destination / "result.json"),
        "sqlite_logical_content_sha256": logical_content_sha256,
        "sqlite_projection_sha256": sha256_file(projection_json),
        "sqlite_serializer": serializer,
        "sqlite_sha256": sqlite_sha256,
    }


def read_sqlite_logical_content(database: pathlib.Path) -> dict[str, Any]:
    """Read the canonical, version-portable logical Graph projection."""
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    try:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise RunnerError("sqlite_integrity", "SQLite integrity check failed")
        nodes = []
        for identifier, kind, payload in connection.execute(
            "SELECT id, kind, payload FROM nodes ORDER BY id"
        ).fetchall():
            node = json.loads(payload)
            if not isinstance(node, dict) or (
                node.get("id") != identifier or node.get("kind") != kind
            ):
                raise RunnerError(
                    "sqlite_logical_content",
                    "SQLite node columns and canonical payload disagree",
                )
            nodes.append(node)
        edges = [
            {"from": source, "kind": kind, "to": target}
            for source, kind, target in connection.execute(
                "SELECT source, kind, target FROM edges "
                "ORDER BY source, kind, target"
            ).fetchall()
        ]
    finally:
        connection.close()
    return {
        "edges": edges,
        "nodes": nodes,
        "schema": "vela.result-runner.sqlite-logical.v1",
    }


def runtime_monitor(
    root: pathlib.Path,
    *,
    max_files: int,
    max_bytes: int,
    max_result_bytes: int,
) -> Callable[[], str | None]:
    def inspect() -> str | None:
        count = 0
        total = 0
        for path in root.rglob("*"):
            if path.is_symlink():
                return "runtime_symlink_rejected"
            if path.is_dir():
                continue
            if not path.is_file():
                return "runtime_nonregular_rejected"
            count += 1
            size = path.stat().st_size
            total += size
            if count > max_files:
                return "runtime_file_count_exceeded"
            if path == root / "result.json" and size > max_result_bytes:
                return "runtime_result_size_exceeded"
            if total > max_bytes:
                return "runtime_total_size_exceeded"
        return None

    return inspect


def credential_findings(
    paths: Iterable[pathlib.Path],
) -> list[dict[str, Any]]:
    findings = []
    for path in sorted(set(paths)):
        if not path.is_file() or path.is_symlink():
            continue
        data = path.read_bytes()
        for index, pattern in enumerate(CREDENTIAL_PATTERNS):
            if pattern.search(data):
                findings.append({"path": str(path), "pattern": index})
    return findings


def manifest(paths: Iterable[pathlib.Path], root: pathlib.Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(set(paths)):
        if path.is_symlink() or not path.is_file():
            raise RunnerError(
                "manifest_input", f"manifest input is not regular: {path}"
            )
        rows.append(
            {
                "bytes": path.stat().st_size,
                "path": str(path.relative_to(root)),
                "sha256": sha256_file(path),
            }
        )
    return rows


def parse_codex_metrics(stdout: bytes) -> dict[str, int]:
    metrics = {
        "cached_input_tokens": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "reasoning_output_tokens": 0,
        "tool_calls": 0,
    }
    for line in stdout.splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(value, dict):
            continue
        usage = value.get("usage")
        if isinstance(usage, dict):
            for key in metrics:
                if key != "tool_calls" and isinstance(usage.get(key), int):
                    metrics[key] = max(metrics[key], usage[key])
        item = value.get("item")
        if isinstance(item, dict) and item.get("type") in {
            "command_execution",
            "mcp_tool_call",
            "web_search",
        }:
            metrics["tool_calls"] += 1
    return metrics


def _positive_limit(value: float | int, hard: float | int, label: str) -> None:
    if value <= 0 or value > hard:
        raise RunnerError("invalid_bound", f"{label} must be > 0 and <= {hard}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=pathlib.Path)
    parser.add_argument("--expected-repository-id", required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--expected-tree", required=True)
    parser.add_argument("--expected-archive-sha256", required=True)
    parser.add_argument("--prompt", required=True, type=pathlib.Path)
    parser.add_argument("--schema", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    parser.add_argument("--image", required=True)
    parser.add_argument("--auth", required=True, type=pathlib.Path)
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument(
        "--reasoning",
        default="low",
        choices=("low", "medium", "high", "xhigh"),
    )
    parser.add_argument("--timeout-seconds", default=900.0, type=float)
    parser.add_argument("--max-prompt-bytes", default=65536, type=int)
    parser.add_argument("--max-schema-bytes", default=65536, type=int)
    parser.add_argument("--max-output-bytes", default=8192, type=int)
    parser.add_argument("--max-stream-bytes", default=1 << 20, type=int)
    parser.add_argument("--max-runtime-bytes", default=1 << 20, type=int)
    parser.add_argument("--max-runtime-files", default=64, type=int)
    parser.add_argument("--disposable-vela", action="store_true")
    parser.add_argument("--vela-bin", type=pathlib.Path)
    parser.add_argument("--vela-sha256")
    parser.add_argument(
        "--skip-docker",
        action="store_true",
        help="Validate and retain the exact dry invocation without model execution",
    )
    return parser.parse_args(argv)


def execute(args: argparse.Namespace) -> int:
    for value, hard, label in (
        (args.timeout_seconds, HARD_MAX_TIMEOUT_SECONDS, "timeout"),
        (args.max_prompt_bytes, HARD_MAX_PROMPT_BYTES, "prompt limit"),
        (args.max_schema_bytes, HARD_MAX_SCHEMA_BYTES, "schema limit"),
        (args.max_output_bytes, HARD_MAX_RESULT_BYTES, "result limit"),
        (args.max_stream_bytes, HARD_MAX_STREAM_BYTES, "stream limit"),
        (args.max_runtime_bytes, HARD_MAX_RUNTIME_BYTES, "runtime byte limit"),
        (args.max_runtime_files, HARD_MAX_RUNTIME_FILES, "runtime file limit"),
    ):
        _positive_limit(value, hard, label)
    if not GIT_RE.fullmatch(args.expected_commit) or not GIT_RE.fullmatch(
        args.expected_tree
    ):
        raise RunnerError(
            "source_identity",
            "expected commit and tree must be lowercase Git object IDs",
        )
    if not HEX_RE.fullmatch(args.expected_archive_sha256):
        raise RunnerError(
            "source_identity",
            "expected archive digest must be 64 lowercase hex",
        )

    repo = canonical_existing_path(args.repo, "source repository", directory=True)
    validate_repository_root(repo)
    prompt = canonical_existing_path(args.prompt, "prompt", file=True)
    schema_path = canonical_existing_path(args.schema, "schema", file=True)
    auth = canonical_existing_path(args.auth, "OAuth file", file=True)
    output = prepare_output_path(args.output, repo)
    prompt_bytes = read_limited(prompt, args.max_prompt_bytes, "prompt")
    validate_schema_definition(
        load_json_limited(schema_path, args.max_schema_bytes, "schema")
    )

    before = git_snapshot(repo)
    assert_expected_source(
        before,
        repository_id=args.expected_repository_id,
        commit=args.expected_commit,
        tree=args.expected_tree,
        archive_sha256=args.expected_archive_sha256,
    )
    if run(["docker", "context", "show"]).stdout.decode().strip() != ("desktop-linux"):
        raise RunnerError("docker_context", "Docker context must be desktop-linux")
    image_before = inspect_docker_image(args.image)
    output.mkdir()
    command = docker_codex_command(
        image=args.image,
        repo=repo,
        auth=auth,
        schema=schema_path,
        output=output,
        model=args.model,
        reasoning=args.reasoning,
    )
    invocation = semantic_invocation(
        model=args.model,
        reasoning=args.reasoning,
        image=image_before,
        source=before,
        prompt_sha256=sha256_bytes(prompt_bytes),
        schema_sha256=sha256_file(schema_path),
        runner_sha256=sha256_file(pathlib.Path(__file__)),
    )
    write_json(
        output / "invocation.json",
        {
            "argv": command,
            "host_argv_sha256": sha256_bytes(canonical_json(command)),
            "oauth_read_only": True,
            "semantic": invocation,
            "source_read_only": True,
        },
    )
    if args.skip_docker:
        after = git_snapshot(repo)
        image_after = inspect_docker_image(args.image)
        if after != before or image_after != image_before:
            raise RunnerError(
                "dry_run_drift",
                "source or image identity changed during dry run",
            )
        write_json(
            output / "receipt.json",
            {
                "docker_image": image_before.as_json(),
                "git_source": {
                    "after": after.as_json(),
                    "before": before.as_json(),
                },
                "schema": "vela.result-runner.receipt.v2",
                "status": "dry_run",
            },
        )
        write_json(
            output / "manifest.json",
            {
                "files": manifest(
                    [output / "invocation.json", output / "receipt.json"],
                    output,
                ),
                "schema": "vela.result-runner.manifest.v1",
            },
        )
        return 0

    receipts = output / "receipts"
    receipts.mkdir()
    completed = run_bounded(
        command,
        input_bytes=prompt_bytes,
        timeout_seconds=args.timeout_seconds,
        stdout_limit=args.max_stream_bytes,
        stderr_limit=args.max_stream_bytes,
        monitor=runtime_monitor(
            output,
            max_files=args.max_runtime_files,
            max_bytes=args.max_runtime_bytes,
            max_result_bytes=args.max_output_bytes,
        ),
    )
    (receipts / "codex.stdout").write_bytes(completed.stdout)
    (receipts / "codex.stderr").write_bytes(completed.stderr)
    write_json(
        receipts / "execution.json",
        {
            "elapsed_seconds": round(completed.elapsed_seconds, 3),
            "exit_code": completed.returncode,
            "status": completed.status,
            "stderr_bytes": len(completed.stderr),
            "stderr_sha256": sha256_bytes(completed.stderr),
            "stdout_bytes": len(completed.stdout),
            "stdout_sha256": sha256_bytes(completed.stdout),
        },
    )
    if completed.status != "completed":
        raise RunnerError(
            completed.status, f"Codex execution stopped: {completed.status}"
        )
    if completed.returncode != 0:
        raise RunnerError(
            "codex_exit",
            f"Codex execution failed with exit {completed.returncode}",
        )

    result = output / "result.json"
    if not result.is_file() or result.is_symlink():
        raise RunnerError(
            "missing_result", "Codex did not produce a regular result.json"
        )
    result_bytes = read_limited(result, args.max_output_bytes, "result.json")
    value = load_json_limited(result, args.max_output_bytes, "result.json")
    validate_small_schema(
        value,
        load_json_limited(schema_path, args.max_schema_bytes, "schema"),
    )
    after = git_snapshot(repo)
    assert_expected_source(
        after,
        repository_id=args.expected_repository_id,
        commit=args.expected_commit,
        tree=args.expected_tree,
        archive_sha256=args.expected_archive_sha256,
    )
    image_after = inspect_docker_image(args.image)
    if after != before or image_after != image_before:
        raise RunnerError(
            "identity_drift",
            "source or image identity changed during execution",
        )

    scan_paths = [
        receipts / "codex.stdout",
        receipts / "codex.stderr",
        result,
    ]
    findings = credential_findings(scan_paths)
    write_json(
        receipts / "credential-scan.json",
        {
            "findings": findings,
            "scanned_files": len(scan_paths),
            "status": "pass" if not findings else "fail",
        },
    )
    if findings:
        for path in scan_paths:
            path.unlink(missing_ok=True)
        raise RunnerError(
            "credential_finding",
            "credential-like bytes found; captured payloads deleted",
        )

    provenance = canonical_json(
        canonical_provenance(
            invocation=invocation,
            result_sha256=sha256_bytes(result_bytes),
            result_bytes=len(result_bytes),
        )
    )
    native = record_native(result, provenance, output / "routes" / "native")
    graph = record_graph(result, provenance, output / "routes" / "graph")
    routes: dict[str, Any] = {"graph": graph, "native": native}
    if args.disposable_vela:
        from vela_disposable import record_disposable

        if args.vela_bin is None or args.vela_sha256 is None:
            raise RunnerError(
                "vela_args",
                "--disposable-vela requires --vela-bin and --vela-sha256",
            )
        vela_bin = canonical_existing_path(args.vela_bin, "Vela binary", file=True)
        routes["vela_disposable"] = record_disposable(
            result=result,
            provenance=provenance,
            destination=output / "routes" / "vela",
            vela_bin=vela_bin,
            expected_vela_sha256=args.vela_sha256,
            method=pathlib.Path(__file__).with_name("review-method.json"),
        )
    write_json(
        output / "receipt.json",
        {
            "docker_image": image_before.as_json(),
            "elapsed_seconds": round(completed.elapsed_seconds, 3),
            "git_source": {
                "after": after.as_json(),
                "before": before.as_json(),
                "container_cwd": "/repo",
                "read_only": True,
            },
            "invocation_identity_sha256": invocation["identity_sha256"],
            "metrics": parse_codex_metrics(completed.stdout),
            "output": {
                "bytes": len(result_bytes),
                "sha256": sha256_bytes(result_bytes),
            },
            "routes": routes,
            "schema": "vela.result-runner.receipt.v2",
            "status": "pass",
        },
    )
    portable = output / "portable-evidence"
    portable.mkdir()
    for source, name in (
        (result, "result.json"),
        (output / "invocation.json", "invocation.json"),
        (output / "receipt.json", "receipt.json"),
        (receipts / "execution.json", "execution.json"),
        (receipts / "credential-scan.json", "credential-scan.json"),
        (receipts / "codex.stdout", "codex.stdout"),
        (receipts / "codex.stderr", "codex.stderr"),
        (
            output / "routes" / "native" / "provenance.json",
            "provenance.json",
        ),
        (output / "routes" / "graph" / "graph.json", "graph.json"),
        (output / "routes" / "graph" / "graph.sqlite", "graph.sqlite"),
        (
            output / "routes" / "graph" / "sqlite-projection.json",
            "sqlite-projection.json",
        ),
    ):
        shutil.copyfile(source, portable / name)
    if args.disposable_vela:
        shutil.copyfile(
            pathlib.Path(__file__).with_name("review-method.json"),
            portable / "review-method.json",
        )
        vela_receipts = portable / "vela-receipts"
        shutil.copytree(output / "routes" / "vela" / "receipts", vela_receipts)
    portable_files = [path for path in portable.rglob("*") if path.is_file()]
    write_json(
        portable / "manifest.json",
        {
            "files": manifest(portable_files, portable),
            "schema": "vela.result-runner.portable-evidence.v1",
        },
    )
    all_files = [
        path
        for path in output.rglob("*")
        if path.is_file() and path.name != "manifest.json"
    ]
    final_findings = credential_findings(all_files)
    if final_findings:
        raise RunnerError(
            "credential_finding",
            "credential-like bytes found in final evidence",
        )
    write_json(
        output / "manifest.json",
        {
            "files": manifest(all_files, output),
            "schema": "vela.result-runner.manifest.v1",
        },
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        return execute(args)
    except RunnerError as error:
        output = getattr(args, "output", None)
        if (
            isinstance(output, pathlib.Path)
            and output.is_absolute()
            and output.is_dir()
            and not output.is_symlink()
        ):
            write_json(
                output / "failure-receipt.json",
                {
                    "error": {"code": error.code, "message": str(error)},
                    "schema": "vela.result-runner.failure.v1",
                    "status": "fail",
                },
            )
        raise


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RunnerError as error:
        print(f"result-runner[{error.code}]: {error}", file=sys.stderr)
        raise SystemExit(1)
