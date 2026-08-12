#!/usr/bin/env python3
"""Run and root one disposable stock-Buzz compatibility experiment.

Private keys exist only in this process environment and are never serialized.
The retained evidence authenticates stock-Buzz execution and activity transport,
not Buzz-authored scientific reasoning, Vela authority, or independent adoption.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import secrets
import signal
import stat
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
MATH_ROOT = HERE.parents[2]
BUZZ_COMMIT = "397796c5f343db4251198f44505b1afebe88223f"
BUZZ_TREE = "aa2867f523032a0b87bfc8c70b152d6e117c9696"
BUZZ_ORIGIN = "https://github.com/block/buzz.git"
MATH_COMMIT = "fab1c3ea6f342a491d5fdfd57fa1126970fb6e61"
MATH_TREE = "2668ca4c7ba345d43bc54ec951b818b469113e98"
P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
G = (
    0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
    0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8,
)
PROTECTED = (".vela", "records", "methods", "continuity")
SOURCE_FILES = ("LICENSE", "Cargo.lock", "rust-toolchain.toml", "docker-compose.yml")
COMPOSE_CLEANUP = {
    "buzz_root": None,
    "empty_inventory_preflight_passed": False,
    "compose_started_by_run": False,
}


def canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()


def sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def file_fact(path: Path) -> dict:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or path.is_symlink():
        raise RuntimeError(f"required regular file refused: {path.name}")
    data = path.read_bytes()
    return {
        "byte_length": len(data),
        "mode": f"{stat.S_IMODE(info.st_mode):04o}",
        "raw_sha256": sha256(data),
    }


def rooted(document: dict, key: str) -> dict:
    value = dict(document)
    value.pop(key, None)
    value[key] = sha256(canonical(value))
    return value


def write_json(path: Path, value: object) -> None:
    path.write_bytes(json.dumps(value, indent=2, ensure_ascii=False).encode() + b"\n")
    path.chmod(0o644)


def clean_git_environment(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("GIT_", "COMPOSE_"))
    }
    env.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_SYSTEM": os.devnull,
            "GIT_NO_LAZY_FETCH": "1",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    if extra:
        env.update(extra)
    return env


def git_bytes(repo: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", "--no-replace-objects", "-C", str(repo), *args],
        env=clean_git_environment(),
        capture_output=True,
        timeout=120,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(
            f"git {' '.join(args)} refused: {result.stderr[-2048:].decode(errors='replace').strip()}"
        )
    return result.stdout


def git(repo: Path, *args: str) -> str:
    return git_bytes(repo, *args).decode().strip()


def parse_local_config(raw: bytes) -> tuple[tuple[str, str], ...]:
    entries: list[tuple[str, str]] = []
    for raw_entry in raw.split(b"\0"):
        if not raw_entry:
            continue
        key, separator, value = raw_entry.partition(b"\n")
        if not separator:
            raise RuntimeError("malformed local Git configuration refused")
        entries.append((key.decode().lower(), value.decode()))
    return tuple(entries)


def assert_repository_storage(
    git_directory: Path,
    config_entries: tuple[tuple[str, str], ...],
    replacement_refs: tuple[str, ...],
) -> None:
    forbidden_config = []
    for key, value in config_entries:
        if (
            key == "extensions.partialclone"
            or key.endswith(".promisor")
            or key.endswith(".partialclonefilter")
            or key in ("core.sparsecheckout", "core.sparsecheckoutcone")
        ):
            forbidden_config.append((key, value))
    if forbidden_config:
        raise RuntimeError("partial, promisor, or sparse Buzz object store refused")
    if replacement_refs:
        raise RuntimeError("Buzz replacement refs refused")
    if any(
        path.exists()
        for path in (
            git_directory / "shallow",
            git_directory / "objects" / "info" / "alternates",
            git_directory / "objects" / "info" / "http-alternates",
            git_directory / "info" / "sparse-checkout",
        )
    ):
        raise RuntimeError("alternate or shallow Buzz object store refused")
    if any((git_directory / "objects" / "pack").glob("*.promisor")):
        raise RuntimeError("promisor Buzz pack refused")


def assert_index_matches_tree(repo: Path, tree_entries: dict[str, tuple[str, str, str]]) -> None:
    flags = git_bytes(repo, "ls-files", "-v", "-z").split(b"\0")
    observed_paths: list[str] = []
    for raw in flags:
        if not raw:
            continue
        if not raw.startswith(b"H "):
            raise RuntimeError("Buzz skip-worktree or assume-unchanged index flag refused")
        observed_paths.append(os.fsdecode(raw[2:]))
    if set(observed_paths) != set(tree_entries):
        raise RuntimeError("Buzz index path inventory differs from pinned tree")

    stages: dict[str, tuple[str, str, str]] = {}
    for raw in git_bytes(repo, "ls-files", "--stage", "-z").split(b"\0"):
        if not raw:
            continue
        header, separator, raw_path = raw.partition(b"\t")
        fields = header.split()
        if separator != b"\t" or len(fields) != 3 or fields[2] != b"0":
            raise RuntimeError("Buzz index stage entry refused")
        path = os.fsdecode(raw_path)
        stages[path] = (fields[0].decode(), "blob", fields[1].decode())
    if stages != tree_entries:
        raise RuntimeError("Buzz index mode or object identity differs from pinned tree")


def tracked_tree_inventory(repo: Path, commit: str = BUZZ_COMMIT) -> dict:
    tree_entries: dict[str, tuple[str, str, str]] = {}
    ordered_rows: list[tuple[str, str, str, str]] = []
    for raw in git_bytes(repo, "ls-tree", "-r", "-z", "--full-tree", commit).split(b"\0"):
        if not raw:
            continue
        header, separator, raw_path = raw.partition(b"\t")
        fields = header.split()
        if separator != b"\t" or len(fields) != 3:
            raise RuntimeError("Buzz pinned tree entry malformed")
        mode, object_type, object_id = (field.decode() for field in fields)
        path = os.fsdecode(raw_path)
        if path.startswith("/") or ".." in Path(path).parts or path in tree_entries:
            raise RuntimeError("Buzz pinned tree path refused")
        if object_type != "blob" or mode not in ("100644", "100755", "120000"):
            raise RuntimeError("Buzz pinned tree contains unsupported entry type or mode")
        tree_entries[path] = (mode, object_type, object_id)
        ordered_rows.append((path, mode, object_type, object_id))
    if not ordered_rows:
        raise RuntimeError("empty Buzz pinned tree refused")
    assert_index_matches_tree(repo, tree_entries)

    serialized = bytearray()
    total_bytes = 0
    by_mode = {"100644": 0, "100755": 0, "120000": 0}
    for path, mode, object_type, object_id in ordered_rows:
        worktree_path = repo / path
        info = worktree_path.lstat()
        if mode == "120000":
            if not stat.S_ISLNK(info.st_mode):
                raise RuntimeError(f"Buzz tracked symlink mode drift: {path}")
            data = os.readlink(os.fsencode(worktree_path))
        else:
            expected_mode = 0o755 if mode == "100755" else 0o644
            if (
                worktree_path.is_symlink()
                or not stat.S_ISREG(info.st_mode)
                or stat.S_IMODE(info.st_mode) != expected_mode
            ):
                raise RuntimeError(f"Buzz tracked regular-file mode drift: {path}")
            with worktree_path.open("rb") as handle:
                data = handle.read(info.st_size + 1)
            if len(data) != info.st_size:
                raise RuntimeError(f"Buzz tracked file changed during bounded read: {path}")
        git_oid = hashlib.sha1(
            b"blob " + str(len(data)).encode() + b"\0" + data,
            usedforsecurity=False,
        ).hexdigest()
        if git_oid != object_id:
            raise RuntimeError(f"Buzz worktree bytes differ from pinned Git blob: {path}")
        raw_root = hashlib.sha256(data).hexdigest()
        serialized.extend(
            mode.encode()
            + b"\0"
            + os.fsencode(path)
            + b"\0"
            + object_id.encode()
            + b"\0"
            + raw_root.encode()
            + b"\0"
            + str(len(data)).encode()
            + b"\n"
        )
        total_bytes += len(data)
        by_mode[mode] += 1
    return {
        "entry_count": len(ordered_rows),
        "raw_byte_length": total_bytes,
        "by_mode": by_mode,
        "inventory_root": sha256(bytes(serialized)),
        "inventory_root_definition": (
            "sha256 of mode + NUL + UTF-8 path + NUL + Git blob oid + NUL + "
            "raw SHA-256 hex + NUL + decimal byte length + LF for every pinned-tree "
            "entry in git ls-tree byte order"
        ),
    }


def tracked_file_fact(repo: Path, name: str, commit: str = BUZZ_COMMIT) -> dict:
    listing = git_bytes(repo, "ls-tree", "-z", commit, "--", name)
    if listing.count(b"\0") != 1 or not listing.endswith(b"\0"):
        raise RuntimeError(f"Buzz tracked source identity drift: {name}")
    header, separator, listed_name = listing[:-1].partition(b"\t")
    fields = header.split()
    if separator != b"\t" or listed_name.decode() != name or len(fields) != 3:
        raise RuntimeError(f"Buzz tracked source entry malformed: {name}")
    mode, object_type, object_id = (field.decode() for field in fields)
    if mode != "100644" or object_type != "blob" or len(object_id) != 40:
        raise RuntimeError(f"Buzz tracked source entry refused: {name}")
    if git(repo, "cat-file", "-t", object_id) != "blob":
        raise RuntimeError(f"Buzz tracked source object type drift: {name}")
    expected_size = int(git(repo, "cat-file", "-s", object_id))
    blob = git_bytes(repo, "cat-file", "blob", object_id)
    path = repo / name
    fact = file_fact(path)
    worktree = path.read_bytes()
    if len(blob) != expected_size or worktree != blob:
        raise RuntimeError(f"Buzz worktree bytes differ from exact Git blob: {name}")
    return {
        **fact,
        "git_blob_oid": object_id,
        "git_mode": mode,
    }


def compose_argv(buzz_root: Path) -> list[str]:
    if buzz_root.resolve(strict=True) != buzz_root:
        raise RuntimeError("noncanonical Buzz Compose root refused")
    return [
        "docker",
        "compose",
        "--project-name",
        "vela-stock-buzz-proof",
        "--file",
        "docker-compose.yml",
        "--project-directory",
        ".",
    ]


def cleanup_owned_compose(
    state: dict,
    *,
    runner=subprocess.run,
) -> bool:
    if not (
        state.get("empty_inventory_preflight_passed")
        and state.get("compose_started_by_run")
        and isinstance(state.get("buzz_root"), Path)
    ):
        return False
    runner(
        [*compose_argv(state["buzz_root"]), "down", "-v", "--remove-orphans"],
        cwd=state["buzz_root"],
        env=clean_git_environment(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=120,
        check=False,
    )
    state["compose_started_by_run"] = False
    return True


def point_add(left, right):
    if left is None:
        return right
    if right is None:
        return left
    x1, y1 = left
    x2, y2 = right
    if x1 == x2 and (y1 != y2 or y1 == 0):
        return None
    slope = (
        (3 * x1 * x1) * pow(2 * y1, P - 2, P) % P
        if x1 == x2
        else (y2 - y1) * pow((x2 - x1) % P, P - 2, P) % P
    )
    x3 = (slope * slope - x1 - x2) % P
    return x3, (slope * (x1 - x3) - y1) % P


def scalar_mult(multiplier: int):
    result = None
    addend = G
    while multiplier:
        if multiplier & 1:
            result = point_add(result, addend)
        addend = point_add(addend, addend)
        multiplier >>= 1
    return result


def ephemeral_key() -> tuple[str, str]:
    secret = secrets.randbelow(N - 1) + 1
    point = scalar_mult(secret)
    assert point is not None
    return f"{secret:064x}", f"{point[0]:064x}"


class Ledger:
    def __init__(self, buzz_root: Path):
        self.buzz_root = buzz_root
        self.entries: list[dict] = []

    def run(
        self,
        command_id: str,
        argv: list[str],
        *,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
        stdin: bytes | None = None,
        safe_argv: list[str] | None = None,
        timeout: int = 600,
        expected: tuple[int, ...] = (0,),
    ) -> subprocess.CompletedProcess[bytes]:
        result = subprocess.run(
            argv,
            cwd=cwd or self.buzz_root,
            env=env or clean_git_environment(),
            input=stdin,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        self.entries.append(
            {
                "argv": safe_argv or argv,
                "command_id": command_id,
                "exit_code": result.returncode,
                "stderr_byte_length": len(result.stderr),
                "stderr_raw_sha256": sha256(result.stderr),
                "stdout_byte_length": len(result.stdout),
                "stdout_raw_sha256": sha256(result.stdout),
            }
        )
        if result.returncode not in expected:
            raise RuntimeError(
                f"{command_id} failed with exit {result.returncode}: "
                f"{result.stderr[-2048:].decode(errors='replace')}"
            )
        return result


def json_stdout(result: subprocess.CompletedProcess[bytes]) -> object:
    return json.loads(result.stdout)


def docker_inventory(ledger: Ledger, suffix: str) -> dict:
    queries = {
        "containers": [
            "docker", "ps", "-a", "--filter", "name=^/buzz-", "--format", "{{.Names}}"
        ],
        "networks": [
            "docker", "network", "ls", "--filter", "name=^buzz-net$", "--format", "{{.Name}}"
        ],
        "volumes": [
            "docker", "volume", "ls", "--filter",
            "name=^buzz-(postgres|minio|prometheus)-data$", "--format", "{{.Name}}"
        ],
    }
    return {
        name: ledger.run(f"inventory_{suffix}_{name}", argv).stdout.decode().splitlines()
        for name, argv in queries.items()
    }


def wait_ready(relay: subprocess.Popen[bytes], timeout: float = 120.0) -> dict:
    started = time.monotonic()
    attempts = 0
    while time.monotonic() - started < timeout:
        attempts += 1
        if relay.poll() is not None:
            raise RuntimeError(f"Buzz relay exited before readiness: {relay.returncode}")
        try:
            with urllib.request.urlopen(
                "http://127.0.0.1:8080/_readiness", timeout=1
            ) as response:
                body = response.read()
                if response.status == 200 and json.loads(body) == {"status": "ready"}:
                    return {
                        "attempts": attempts,
                        "elapsed_milliseconds": round((time.monotonic() - started) * 1000),
                        "response_raw_sha256": sha256(body),
                    }
        except Exception:
            pass
        time.sleep(0.25)
    raise RuntimeError("Buzz relay readiness exceeded 120 seconds")


def assert_exact_source(buzz: Path) -> dict:
    if buzz.resolve() != buzz:
        raise RuntimeError("Buzz checkout must be a canonical ordinary Git worktree")
    dot_git = buzz / ".git"
    dot_git_info = dot_git.lstat()
    if dot_git.is_symlink() or not stat.S_ISDIR(dot_git_info.st_mode):
        raise RuntimeError("Buzz checkout must use an ordinary in-worktree Git directory")
    git_directory = Path(git(buzz, "rev-parse", "--absolute-git-dir")).resolve(strict=True)
    top_level = Path(git(buzz, "rev-parse", "--show-toplevel")).resolve(strict=True)
    common_directory = Path(git(buzz, "rev-parse", "--git-common-dir"))
    common_directory = (
        common_directory.resolve(strict=True)
        if common_directory.is_absolute()
        else (buzz / common_directory).resolve(strict=True)
    )
    if git_directory != dot_git or common_directory != dot_git or top_level != buzz:
        raise RuntimeError("Buzz Git directory or worktree topology drift")
    origin = git(buzz, "remote", "get-url", "origin")
    if origin != BUZZ_ORIGIN:
        raise RuntimeError("Buzz source origin drift")
    if git(buzz, "rev-parse", "HEAD") != BUZZ_COMMIT:
        raise RuntimeError("Buzz source commit drift")
    if git(buzz, "rev-parse", "HEAD^{tree}") != BUZZ_TREE:
        raise RuntimeError("Buzz source tree drift")
    if git(buzz, "rev-parse", "--is-shallow-repository") != "false":
        raise RuntimeError("shallow Buzz source refused")
    if git(buzz, "status", "--porcelain=v1", "--untracked-files=all"):
        raise RuntimeError("dirty Buzz source refused")
    if git(buzz, "status", "--porcelain=v1", "--ignored=matching", "--untracked-files=all"):
        raise RuntimeError("ignored Buzz worktree residue refused")
    config_entries = parse_local_config(git_bytes(buzz, "config", "--local", "--null", "--list"))
    replacement_refs = tuple(
        line
        for line in git(buzz, "for-each-ref", "--format=%(refname)", "refs/replace").splitlines()
        if line
    )
    assert_repository_storage(git_directory, config_entries, replacement_refs)
    git(buzz, "fsck", "--full", "--strict", "--no-reflogs")
    tracked_tree = tracked_tree_inventory(buzz)
    files = {name: tracked_file_fact(buzz, name) for name in SOURCE_FILES}
    if files["LICENSE"]["raw_sha256"] != (
        "sha256:108cb15997e51b75a8d18b0c1e2c52bd3879d051ab02118973387df1e4aab584"
    ):
        raise RuntimeError("Buzz Apache-2.0 license bytes drift")
    return {
        "commit": BUZZ_COMMIT,
        "custody": {
            "canonical_top_level": True,
            "exact_in_worktree_git_directory": True,
            "ignored_residue_absent": True,
            "lazy_fetch_disabled": True,
            "partial_promisor_shallow_alternates_and_replacements_absent": True,
            "sparse_skip_worktree_and_assume_unchanged_absent": True,
            "required_worktree_bytes_equal_exact_git_blobs": True,
            "all_tracked_worktree_entries_equal_pinned_tree": True,
        },
        "license_expression": "Apache-2.0",
        "origin": BUZZ_ORIGIN,
        "source_files": files,
        "tracked_tree": tracked_tree,
        "tree": BUZZ_TREE,
    }


def protected_state() -> dict:
    diff = subprocess.run(
        ["git", "--no-replace-objects", "diff", "HEAD", "--", *PROTECTED],
        cwd=MATH_ROOT,
        env=clean_git_environment(),
        capture_output=True,
        check=True,
    ).stdout
    status_output = subprocess.run(
        [
            "git", "--no-replace-objects", "status", "--porcelain=v1",
            "--untracked-files=all", "--", *PROTECTED,
        ],
        cwd=MATH_ROOT,
        env=clean_git_environment(),
        capture_output=True,
        check=True,
    ).stdout
    return {
        "diff_byte_length": len(diff),
        "diff_raw_sha256": sha256(diff),
        "status_byte_length": len(status_output),
        "status_raw_sha256": sha256(status_output),
    }


def query_raw_events(ledger: Ledger, event_ids: list[str]) -> list[dict]:
    literal_ids = ",".join(f"'{value}'" for value in event_ids)
    sql = (
        "select coalesce(jsonb_agg(jsonb_build_object("
        "'id',encode(id,'hex'),'pubkey',encode(pubkey,'hex'),"
        "'created_at',extract(epoch from created_at)::bigint,'kind',kind,"
        "'tags',tags,'content',content,'sig',encode(sig,'hex')) "
        f"order by array_position(array[{literal_ids}],encode(id,'hex'))), '[]'::jsonb) "
        f"from events where encode(id,'hex') in ({literal_ids})"
    )
    result = ledger.run(
        "raw_event_database_readback",
        ["docker", "exec", "buzz-postgres", "psql", "-U", "buzz", "-d", "buzz", "-Atqc", sql],
        safe_argv=[
            "docker", "exec", "buzz-postgres", "psql", "-U", "buzz", "-d", "buzz",
            "-Atqc", "<allowlisted-three-event-readback-sql>",
        ],
    )
    value = json_stdout(result)
    if [event["id"] for event in value] != event_ids:
        raise RuntimeError("raw event database readback identity drift")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--buzz-repo", type=Path, required=True)
    args = parser.parse_args()
    COMPOSE_CLEANUP.update(
        {
            "buzz_root": None,
            "empty_inventory_preflight_passed": False,
            "compose_started_by_run": False,
        }
    )
    buzz = args.buzz_repo.resolve(strict=True)
    source = assert_exact_source(buzz)
    if git(MATH_ROOT, "rev-parse", "HEAD") != MATH_COMMIT or git(
        MATH_ROOT, "rev-parse", "HEAD^{tree}"
    ) != MATH_TREE:
        raise RuntimeError("Math source baseline drift")
    before = protected_state()
    if before["diff_byte_length"] or before["status_byte_length"]:
        raise RuntimeError("protected Vela state is already dirty")

    packet = json.loads((HERE / "target-packet.json").read_text())
    if rooted(packet, "packet_root") != packet:
        raise RuntimeError("target packet root drift")
    packet_bytes = (HERE / "target-packet.json").read_bytes()
    packet_root = packet["packet_root"]
    ledger = Ledger(buzz)
    initial_inventory = docker_inventory(ledger, "before")
    if any(initial_inventory.values()):
        raise RuntimeError("pre-existing Buzz Docker resources refused")
    COMPOSE_CLEANUP["buzz_root"] = buzz
    COMPOSE_CLEANUP["empty_inventory_preflight_passed"] = True

    build_temp = tempfile.TemporaryDirectory(prefix="vela-stock-buzz-build-")
    build_root = Path(build_temp.name)
    build_env = clean_git_environment({"CARGO_TARGET_DIR": str(build_root)})
    build = ledger.run(
        "cargo_locked_release_build",
        [
            "cargo", "build", "--locked", "--release", "-p", "buzz-cli", "-p",
            "buzz-relay", "-p", "buzz-admin",
        ],
        env=build_env,
        timeout=1200,
    )
    binaries = {
        name: file_fact(build_root / "release" / name)
        for name in ("buzz", "buzz-relay", "buzz-admin")
    }
    rustc_verbose = ledger.run("rustc_verbose_version", ["rustc", "-vV"]).stdout.decode().strip()
    toolchain = {
        "architecture": platform.machine(),
        "bun": ledger.run("bun_version", ["bun", "--version"]).stdout.decode().strip(),
        "cargo": ledger.run("cargo_version", ["cargo", "-V"]).stdout.decode().strip(),
        "docker": json_stdout(
            ledger.run(
                "docker_version",
                ["docker", "version", "--format", '{"client":"{{.Client.Version}}","server":"{{.Server.Version}}"}'],
            )
        ),
        "operating_system": platform.platform(),
        "python": platform.python_version(),
        "rustc_verbose": rustc_verbose,
        "rustc_verbose_raw_sha256": sha256((rustc_verbose + "\n").encode()),
    }

    compose = compose_argv(buzz)
    ledger.run("compose_pull", [*compose, "pull", "postgres", "redis", "minio", "minio-init"])
    COMPOSE_CLEANUP["compose_started_by_run"] = True
    ledger.run(
        "compose_up",
        [*compose, "up", "-d", "--wait", "--wait-timeout", "60", "postgres", "redis", "minio"],
    )
    ledger.run(
        "compose_minio_init",
        [*compose, "up", "--no-deps", "--abort-on-container-exit", "--exit-code-from", "minio-init", "minio-init"],
    )
    image_names = ("postgres:17-alpine", "redis:7-alpine", "minio/minio:latest", "minio/mc:latest")
    images: dict[str, dict] = {}
    for image in image_names:
        observed = json_stdout(
            ledger.run(
                "image_inspect_" + image.replace("/", "_").replace(":", "_"),
                [
                    "docker", "image", "inspect", image, "--format",
                    '{"id":"{{.Id}}","repo_digests":{{json .RepoDigests}}}',
                ],
            )
        )
        images[image] = observed

    operator_secret, operator_pubkey = ephemeral_key()
    member_secret, member_pubkey = ephemeral_key()
    relay_secret, relay_pubkey = ephemeral_key()
    base_env = clean_git_environment()
    base_env.update(
        {
            "DATABASE_URL": "postgres://buzz:buzz_dev@localhost:5432/buzz",
            "REDIS_URL": "redis://localhost:6379",
            "BUZZ_BIND_ADDR": "127.0.0.1:3000",
            "RELAY_URL": "ws://localhost:3000",
            "BUZZ_RELAY_URL": "http://localhost:3000",
            "BUZZ_HEALTH_PORT": "8080",
            "BUZZ_METRICS_PORT": "9102",
            "BUZZ_S3_ENDPOINT": "http://localhost:9000",
            "BUZZ_S3_ACCESS_KEY": "buzz_dev",
            "BUZZ_S3_SECRET_KEY": "buzz_dev_secret",
            "BUZZ_S3_BUCKET": "buzz-media",
            "BUZZ_S3_REGION": "us-east-1",
            "BUZZ_S3_ADDRESSING_STYLE": "path",
            "BUZZ_GIT_REPO_PATH": str(build_root / "repos"),
            "BUZZ_GIT_PACK_CACHE_PATH": str(build_root / "repos" / ".pack-cache"),
            "RELAY_OWNER_PUBKEY": operator_pubkey,
            "BUZZ_RELAY_PRIVATE_KEY": relay_secret,
            "BUZZ_REQUIRE_RELAY_MEMBERSHIP": "false",
            "BUZZ_REQUIRE_AUTH_TOKEN": "false",
            "BUZZ_AUTO_MIGRATE": "false",
            "RUST_LOG": "info",
        }
    )
    bin_dir = build_root / "release"
    ledger.run(
        "buzz_database_migrate", [str(bin_dir / "buzz-admin"), "migrate"], env=base_env,
        safe_argv=["target/release/buzz-admin", "migrate"],
    )
    migrations_sql = (
        "select coalesce(jsonb_agg(jsonb_build_object('version',version,'description',description,"
        "'checksum',encode(checksum,'hex'),'success',success) order by version),'[]'::jsonb) "
        "from _sqlx_migrations"
    )
    migrations = json_stdout(
        ledger.run(
            "migration_database_readback",
            ["docker", "exec", "buzz-postgres", "psql", "-U", "buzz", "-d", "buzz", "-Atqc", migrations_sql],
            safe_argv=[
                "docker", "exec", "buzz-postgres", "psql", "-U", "buzz", "-d", "buzz",
                "-Atqc", "<allowlisted-migration-readback-sql>",
            ],
        )
    )

    private_secret_values = (operator_secret, member_secret, relay_secret)
    relay_log = build_root / "buzz-relay.log"
    relay_handle = relay_log.open("wb")
    relay = subprocess.Popen(
        [str(bin_dir / "buzz-relay")],
        cwd=buzz,
        env=base_env,
        stdout=relay_handle,
        stderr=subprocess.STDOUT,
    )
    relay_started = time.monotonic()
    try:
        readiness = wait_ready(relay)

        def buzz_command(
            command_id: str,
            actor: str,
            *arguments: str,
            stdin: bytes | None = None,
        ) -> object:
            env = base_env.copy()
            env["BUZZ_PRIVATE_KEY"] = actor
            result = ledger.run(
                command_id,
                [str(bin_dir / "buzz"), *arguments],
                env=env,
                stdin=stdin,
                safe_argv=["buzz", *arguments],
                timeout=90,
            )
            return json_stdout(result)

        created = buzz_command(
            "buzz_channel_create", operator_secret, "channels", "create", "--name",
            "vela-erdos-321-bridge", "--type", "stream", "--visibility", "open",
            "--description", "Disposable rooted Vela target transport",
        )
        channel_id = created["channel_id"]
        added = buzz_command(
            "buzz_channel_add_member", operator_secret, "channels", "add-member",
            "--channel", channel_id, "--pubkey", member_pubkey, "--role", "member",
        )
        channel_readback = buzz_command(
            "buzz_channel_get", member_secret, "channels", "get", "--channel", channel_id
        )
        member_readback = buzz_command(
            "buzz_channel_members", member_secret, "channels", "members", "--channel", channel_id
        )
        target_receipt = buzz_command(
            "buzz_target_send", operator_secret, "messages", "send", "--channel", channel_id,
            "--content", "-", stdin=packet_bytes,
        )
        target_id = target_receipt["event_id"]
        target_readback = buzz_command(
            "buzz_target_readback", member_secret, "messages", "get", "--channel", channel_id,
            "--limit", "50",
        )

        note = rooted(
            {
                "schema": "vela.workbench-note.v1",
                "authority_effect": "none",
                "authorship": {
                    "scientific_decomposition": "experiment_operator",
                    "buzz_role": "transport_storage_and_readback_only",
                },
                "workbench": {"name": "buzz", "repository": BUZZ_ORIGIN, "commit": BUZZ_COMMIT},
                "packet_root": packet_root,
                "activity": {"channel_id": channel_id, "received_event_id": target_id},
                "decomposition": [
                    {"step": "formalize_real_nat_log_bridge", "deliverable": "A Lean lemma relating the retained Real.log and Nat.log coordinates under explicit domain hypotheses"},
                    {"step": "prove_index_alignment", "deliverable": "Kernel-checked lower and upper index-alignment lemmas for k=d+2 and r=d+2"},
                    {"step": "verify_without_network", "deliverable": "A pinned command and result manifest that check the candidate in a clean network-disabled environment"},
                ],
                "result_status": "operator_authored_decomposition_transported_no_candidate",
                "nonclaims": [
                    "The experiment operator authored this decomposition; Buzz only transported, stored, and returned its bytes.",
                    "Buzz performed no scientific reasoning, proof construction, or result evaluation.",
                    "This decomposition is disposable workspace activity, not a proof.",
                    "No implication or equivalence was established.",
                    "No Vela Submission, Verification Record, Decision, Event, or Standing was created.",
                ],
                "note_root_definition": "sha256 of RFC 8785 canonical JSON with note_root omitted",
            },
            "note_root",
        )
        write_json(HERE / "workbench-note.json", note)
        note_bytes = (HERE / "workbench-note.json").read_bytes()
        note_receipt = buzz_command(
            "buzz_note_send", member_secret, "messages", "send", "--channel", channel_id,
            "--content", "-", "--reply-to", target_id, stdin=note_bytes,
        )
        note_id = note_receipt["event_id"]
        result = rooted(
            {
                "schema": "vela.workbench-result.v1",
                "authority_effect": "none",
                "authorship": {
                    "scientific_result": "experiment_operator",
                    "buzz_role": "transport_storage_and_readback_only",
                },
                "workbench": {"name": "buzz", "repository": BUZZ_ORIGIN, "commit": BUZZ_COMMIT, "channel_id": channel_id},
                "packet_root": packet_root,
                "activity_event_ids": [target_id, note_id],
                "result_status": "operator_authored_result_transported_no_candidate",
                "artifact_roots": [note["note_root"]],
                "observations": {
                    "packet_round_trip_byte_identical": True,
                    "packet_raw_byte_length": len(packet_bytes),
                    "packet_raw_sha256": sha256(packet_bytes),
                    "distinct_activity_keys": True,
                },
                "nonclaims": [
                    "This proves stock Buzz transported, stored, and read back an operator-authored rooted Vela work packet and operator-authored result.",
                    "Buzz performed no scientific reasoning, proof construction, or result evaluation.",
                    "It is not independent adoption because both actors were operated by the same experimenter.",
                    "No scientific candidate was produced or verified.",
                    "Buzz event signatures do not create a Vela Submission, Verification, Decision, Event, or Standing.",
                ],
                "result_root_definition": "sha256 of RFC 8785 canonical JSON with result_root omitted",
            },
            "result_root",
        )
        write_json(HERE / "workbench-result.json", result)
        result_bytes = (HERE / "workbench-result.json").read_bytes()
        result_receipt = buzz_command(
            "buzz_result_send", member_secret, "messages", "send", "--channel", channel_id,
            "--content", "-", "--reply-to", note_id, stdin=result_bytes,
        )
        result_id = result_receipt["event_id"]
        final_readback = buzz_command(
            "buzz_message_readback", operator_secret, "messages", "get", "--channel", channel_id,
            "--limit", "50",
        )
        event_ids = [target_id, note_id, result_id]
        raw_events = query_raw_events(ledger, event_ids)
        content_files = ("target-packet.json", "workbench-note.json", "workbench-result.json")
        for event, filename, expected_content in zip(
            raw_events, content_files, (packet_bytes, note_bytes, result_bytes), strict=True
        ):
            if event["content"].encode() != expected_content:
                raise RuntimeError(f"stock Buzz content round-trip drift: {filename}")
        normalized = {entry["id"]: entry for entry in final_readback}
        for event in raw_events:
            comparison = {key: event[key] for key in ("id", "pubkey", "created_at", "kind", "tags", "content")}
            if normalized.get(event["id"]) != comparison:
                raise RuntimeError("CLI normalized message readback differs from stored event")
        envelope = {
            "schema": "vela.stock-buzz-activity-events.v1",
            "authority_effect": "none",
            "channel_id": channel_id,
            "roles": [
                {"content_file": filename, "event_id": event_id, "role": role}
                for filename, event_id, role in zip(
                    content_files, event_ids, ("target_packet", "workbench_note", "workbench_result"), strict=True
                )
            ],
            "events": raw_events,
            "nonclaims": [
                "These signatures authenticate disposable local Buzz transport, storage, and readback activity only.",
                "The experiment operator authored the scientific packet, decomposition, and result; Buzz performed no scientific reasoning.",
                "Both activity identities were operated by the same experimenter.",
                "No independent adoption, scientific candidate, Vela Submission, Verification, Decision, Event, or Standing is established.",
            ],
        }
        write_json(HERE / "events.json", envelope)
    finally:
        if relay.poll() is None:
            relay.send_signal(signal.SIGTERM)
            try:
                relay.wait(timeout=45)
            except subprocess.TimeoutExpired:
                relay.kill()
                relay.wait(timeout=10)
        relay_handle.close()

    relay_log_bytes = relay_log.read_bytes()
    if any(secret.encode() in relay_log_bytes for secret in private_secret_values):
        raise RuntimeError("ephemeral Buzz private key escaped into raw relay log")
    relay_log_fact = file_fact(relay_log)
    lifecycle_allowlist = (
        "Starting buzz-relay", "Config loaded", "Postgres connected",
        "Skipping database migrations", "Deployment community ensured",
        "Health probe listener started", "buzz-relay TCP listening",
        "Shutdown signal received", "Starting graceful drain", "Audit worker drained cleanly",
    )
    lifecycle = []
    for line in relay_log_bytes.splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        message = entry.get("message")
        if message in lifecycle_allowlist:
            lifecycle.append({"level": entry.get("level"), "message": message})
    ledger.entries.append(
        {
            "argv": ["target/release/buzz-relay"],
            "command_id": "buzz_relay_runtime",
            "exit_code": relay.returncode,
            "expected_signal": "SIGTERM",
            "runtime_milliseconds": round((time.monotonic() - relay_started) * 1000),
            "stderr_byte_length": 0,
            "stderr_raw_sha256": sha256(b""),
            "stdout_byte_length": len(relay_log_bytes),
            "stdout_raw_sha256": sha256(relay_log_bytes),
        }
    )
    ledger.run("compose_down", [*compose, "down", "-v", "--remove-orphans"])
    COMPOSE_CLEANUP["compose_started_by_run"] = False
    final_inventory = docker_inventory(ledger, "after")
    if any(final_inventory.values()):
        raise RuntimeError("disposable Buzz Docker teardown incomplete")

    install = ledger.run(
        "nostr_tools_frozen_install", ["bun", "install", "--frozen-lockfile"], cwd=HERE
    )
    nostr = ledger.run(
        "nostr_tools_cross_implementation_verify", ["bun", "run", "verify-nostr.mjs"], cwd=HERE
    )
    nostr_result = json_stdout(nostr)
    write_json(HERE / "nostr-verification.json", nostr_result)
    build_temp.cleanup()
    if build_root.exists():
        raise RuntimeError("external Buzz build and relay-log directory cleanup failed")
    after = protected_state()
    if after != before or after["diff_byte_length"] or after["status_byte_length"]:
        raise RuntimeError("Vela protocol or continuity state changed during Buzz run")

    observations = {
        "channel_create_receipt": created,
        "channel_member_add_receipt": added,
        "channel_metadata_readback": channel_readback,
        "channel_membership_readback": member_readback,
        "message_receipts": [target_receipt, note_receipt, result_receipt],
        "message_readback": final_readback,
        "migration_count": len(migrations),
        "migration_inventory_root": sha256(canonical(migrations)),
        "readiness": readiness,
        "relay_lifecycle": lifecycle,
    }
    execution = rooted(
        {
            "schema": "vela.stock-buzz-execution-evidence.v1",
            "authority_effect": "none",
            "source": source,
            "build": {
                "binaries": binaries,
                "fresh_external_target_directory": True,
                "locked_release_build_stderr_raw_sha256": sha256(build.stderr),
                "locked_release_build_stdout_raw_sha256": sha256(build.stdout),
            },
            "runtime": {
                "compose_file": source["source_files"]["docker-compose.yml"],
                "images": images,
                "relay_log": {
                    **relay_log_fact,
                    "retained": False,
                    "removed_with_external_build_directory": True,
                },
                "selected_stock_services": ["postgres", "redis", "minio", "minio-init"],
                "toolchain": toolchain,
            },
            "activity": {
                "channel_id": channel_id,
                "operator_pubkey": operator_pubkey,
                "member_pubkey": member_pubkey,
                "relay_pubkey": relay_pubkey,
                "same_experimenter_operated_activity_keys": True,
                "observations": observations,
            },
            "command_ledger": ledger.entries,
            "teardown": {
                "before": initial_inventory,
                "after": final_inventory,
                "disposable_containers_network_and_volumes_absent": True,
                "external_build_directory_and_relay_log_absent": True,
            },
            "protected_vela_state": {"before": before, "after": after, "changed": False},
            "cross_implementation_signature_verification": nostr_result,
            "privacy": {
                "ephemeral_private_keys_passed_only_via_buzz_child_process_environments": True,
                "private_keys_retained": False,
                "private_keys_serialized": False,
                "raw_relay_log_scanned_for_all_three_private_keys_before_hash_and_removal": True,
                "participant_or_evaluator_inputs_used": False,
                "repository_authority_credentials_used": False,
            },
            "nonclaims": [
                "This same-experimenter run proves stock Buzz runtime compatibility, not independent adoption.",
                "The experiment operator authored the scientific packet, decomposition, and result; Buzz only transported, stored, and returned their bytes.",
                "Buzz performed no scientific reasoning, proof construction, or result evaluation.",
                "Buzz activity is not a Vela Submission, Verification, Decision, Event, or Standing.",
                "No scientific candidate was produced and no authority state changed.",
            ],
            "execution_root_definition": "sha256 of RFC 8785 canonical JSON with execution_root omitted",
        },
        "execution_root",
    )
    write_json(HERE / "execution-evidence.json", execution)
    retained = (
        "events.json", "execution-evidence.json", "nostr-verification.json",
        "target-packet.json", "workbench-note.json", "workbench-result.json",
        "package.json", "bun.lock", "run.py", "test_run.py", "test_verify.py",
        "verify.py", "verify-nostr.mjs",
    )
    file_inventory = {name: file_fact(HERE / name) for name in retained}
    manifest = rooted(
        {
            "schema": "vela.stock-buzz-compatibility-run.v2",
            "authority_effect": "none",
            "captured_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "math_source": {
                "commit": MATH_COMMIT,
                "tree": MATH_TREE,
                "repository_root": packet["repository"]["repository_root"],
            },
            "buzz_source": {"commit": BUZZ_COMMIT, "tree": BUZZ_TREE, "origin": BUZZ_ORIGIN},
            "activity": {
                "channel_id": channel_id,
                "event_ids": event_ids,
                "distinct_activity_keys": 2,
                "same_experimenter_operated_both_keys": True,
            },
            "files": file_inventory,
            "execution_root": execution["execution_root"],
            "result": {
                "status": "stock_buzz_transported_operator_authored_activity_no_candidate",
                "buzz_scientific_reasoning": False,
                "independent_adoption": False,
                "scientific_candidate_produced": False,
                "scientific_state_changed": False,
            },
            "aggregate_evidence_root_definition": "sha256 of RFC 8785 canonical JSON with aggregate_evidence_root omitted",
        },
        "aggregate_evidence_root",
    )
    write_json(HERE / "run-manifest.json", manifest)
    serialized = b"\n".join((HERE / name).read_bytes() for name in retained + ("run-manifest.json",))
    if any(value.encode() in serialized for value in private_secret_values):
        raise RuntimeError("private key material escaped into retained evidence")
    operator_secret = member_secret = relay_secret = "0" * 64
    print(json.dumps({
        "ok": True,
        "aggregate_evidence_root": manifest["aggregate_evidence_root"],
        "buzz_commit": BUZZ_COMMIT,
        "events": len(event_ids),
        "authority_effect": "none",
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        cleanup_owned_compose(COMPOSE_CLEANUP)
        print(f"stock_buzz_experiment_refused: {error}", file=sys.stderr)
        raise SystemExit(1)
