#!/usr/bin/env python3
"""Hostile source-custody and cleanup-ownership tests for the stock-Buzz runner."""

from __future__ import annotations

import argparse
import importlib.util
import os
import subprocess
import tempfile
from types import SimpleNamespace
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("stock_buzz_run", HERE / "run.py")
RUN = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(RUN)


def expect_runtime(callable_value, fragment: str) -> None:
    try:
        callable_value()
    except RuntimeError as error:
        if fragment not in str(error):
            raise AssertionError(f"expected {fragment!r}, got {error!r}") from error
    else:
        raise AssertionError(f"expected RuntimeError containing {fragment!r}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--buzz-repo", type=Path, required=True)
    args = parser.parse_args()
    buzz = args.buzz_repo.resolve(strict=True)

    baseline = RUN.assert_exact_source(buzz)
    assert baseline["commit"] == RUN.BUZZ_COMMIT
    assert baseline["tree"] == RUN.BUZZ_TREE
    assert all(
        fact["git_mode"] == "100644" and len(fact["git_blob_oid"]) == 40
        for fact in baseline["source_files"].values()
    )

    hostile = {
        "GIT_DIR": "/hostile/not-the-git-dir",
        "GIT_WORK_TREE": "/hostile/not-the-worktree",
        "GIT_OBJECT_DIRECTORY": "/hostile/not-the-objects",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES": "/hostile/not-the-alternates",
        "GIT_CONFIG_GLOBAL": "/hostile/not-the-config",
        "GIT_CONFIG_SYSTEM": "/hostile/not-the-system-config",
        "GIT_REPLACE_REF_BASE": "refs/hostile-replacements/",
        "GIT_NO_LAZY_FETCH": "0",
        "COMPOSE_FILE": "/hostile/not-the-compose-file.yml",
        "COMPOSE_PROJECT_NAME": "hostile-project",
        "COMPOSE_PROFILES": "hostile-profile",
    }
    prior = {key: os.environ.get(key) for key in hostile}
    try:
        os.environ.update(hostile)
        assert RUN.assert_exact_source(buzz) == baseline
    finally:
        for key, value in prior.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    cleaned = RUN.clean_git_environment()
    assert cleaned["GIT_NO_LAZY_FETCH"] == "1"
    assert cleaned["GIT_NO_REPLACE_OBJECTS"] == "1"
    assert "GIT_DIR" not in cleaned and "GIT_WORK_TREE" not in cleaned
    assert not any(key.startswith("COMPOSE_") for key in cleaned)
    assert RUN.compose_argv(buzz) == [
        "docker", "compose", "--project-name", "vela-stock-buzz-proof",
        "--file", "docker-compose.yml", "--project-directory", ".",
    ]

    inventory_calls: list[tuple[str, list[str]]] = []

    class HostileInventoryLedger:
        def run(self, command_id, argv):
            inventory_calls.append((command_id, argv))
            stdout = b"buzz-postgres-data\n" if command_id == "inventory_before_volumes" else b""
            return SimpleNamespace(stdout=stdout)

    hostile_inventory = RUN.docker_inventory(HostileInventoryLedger(), "before")
    assert hostile_inventory == {
        "containers": [], "networks": [], "volumes": ["buzz-postgres-data"]
    }
    assert inventory_calls[-1] == (
        "inventory_before_volumes",
        [
            "docker", "volume", "ls", "--filter",
            "name=^buzz-(postgres|minio|prometheus)-data$", "--format", "{{.Name}}",
        ],
    )

    with tempfile.TemporaryDirectory() as temporary_raw:
        temporary = Path(temporary_raw)
        expect_runtime(
            lambda: RUN.assert_repository_storage(
                temporary,
                (("remote.origin.partialclonefilter", "blob:none"),),
                (),
            ),
            "partial, promisor, or sparse",
        )
        expect_runtime(
            lambda: RUN.assert_repository_storage(
                temporary,
                (("remote.origin.promisor", "true"),),
                (),
            ),
            "partial, promisor, or sparse",
        )
        expect_runtime(
            lambda: RUN.assert_repository_storage(temporary, (), ("refs/replace/object",)),
            "replacement refs",
        )
        pack = temporary / "objects" / "pack"
        pack.mkdir(parents=True)
        (pack / "pack-hostile.promisor").write_bytes(b"")
        expect_runtime(
            lambda: RUN.assert_repository_storage(temporary, (), ()),
            "promisor Buzz pack",
        )
        (pack / "pack-hostile.promisor").unlink()
        shallow = temporary / "shallow"
        shallow.write_text("hostile\n")
        expect_runtime(
            lambda: RUN.assert_repository_storage(temporary, (), ()),
            "alternate or shallow",
        )
        shallow.unlink()
        alternates = temporary / "objects" / "info" / "alternates"
        alternates.parent.mkdir(parents=True)
        alternates.write_text("/hostile/object/store\n")
        expect_runtime(
            lambda: RUN.assert_repository_storage(temporary, (), ()),
            "alternate or shallow",
        )

    with tempfile.TemporaryDirectory() as repository_raw:
        repository = Path(repository_raw) / "repository"
        subprocess.run(["git", "init", "-q", str(repository)], check=True)
        tracked = repository / "required.txt"
        tracked.write_bytes(b"exact tracked bytes\n")
        subprocess.run(["git", "-C", str(repository), "add", "required.txt"], check=True)
        subprocess.run(
            [
                "git", "-C", str(repository), "-c", "user.name=Vela test",
                "-c", "user.email=vela-test@example.invalid", "commit", "-qm", "fixture",
            ],
            check=True,
        )
        commit = RUN.git(repository, "rev-parse", "HEAD")
        inventory = RUN.tracked_tree_inventory(repository, commit)
        assert inventory["entry_count"] == 1 and inventory["raw_byte_length"] == 20
        assert RUN.tracked_file_fact(repository, "required.txt", commit)["byte_length"] == 20
        subprocess.run(
            ["git", "-C", str(repository), "update-index", "--skip-worktree", "required.txt"],
            check=True,
        )
        expect_runtime(
            lambda: RUN.tracked_tree_inventory(repository, commit),
            "skip-worktree or assume-unchanged",
        )
        subprocess.run(
            ["git", "-C", str(repository), "update-index", "--no-skip-worktree", "required.txt"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(repository), "update-index", "--assume-unchanged", "required.txt"],
            check=True,
        )
        expect_runtime(
            lambda: RUN.tracked_tree_inventory(repository, commit),
            "skip-worktree or assume-unchanged",
        )
        subprocess.run(
            ["git", "-C", str(repository), "update-index", "--no-assume-unchanged", "required.txt"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(repository), "config", "--local", "core.sparseCheckout", "true"],
            check=True,
        )
        git_directory = Path(RUN.git(repository, "rev-parse", "--absolute-git-dir"))
        config_entries = RUN.parse_local_config(
            RUN.git_bytes(repository, "config", "--local", "--null", "--list")
        )
        expect_runtime(
            lambda: RUN.assert_repository_storage(git_directory, config_entries, ()),
            "partial, promisor, or sparse",
        )
        subprocess.run(
            ["git", "-C", str(repository), "config", "--local", "--unset", "core.sparseCheckout"],
            check=True,
        )
        tracked.chmod(0o755)
        expect_runtime(
            lambda: RUN.tracked_tree_inventory(repository, commit),
            "regular-file mode drift",
        )
        tracked.chmod(0o644)
        subprocess.run(
            ["git", "-C", str(repository), "update-index", "--chmod=+x", "required.txt"],
            check=True,
        )
        expect_runtime(
            lambda: RUN.tracked_tree_inventory(repository, commit),
            "index mode or object identity",
        )
        subprocess.run(
            ["git", "-C", str(repository), "update-index", "--chmod=-x", "required.txt"],
            check=True,
        )
        tracked.write_bytes(b"hostile worktree drift\n")
        expect_runtime(
            lambda: RUN.tracked_file_fact(repository, "required.txt", commit),
            "worktree bytes differ",
        )

    calls: list[tuple[list[str], dict]] = []

    def recorder(argv, **kwargs):
        calls.append((argv, kwargs))

    for state in (
        {"buzz_root": buzz, "empty_inventory_preflight_passed": False, "compose_started_by_run": False},
        {"buzz_root": buzz, "empty_inventory_preflight_passed": False, "compose_started_by_run": True},
        {"buzz_root": buzz, "empty_inventory_preflight_passed": True, "compose_started_by_run": False},
    ):
        assert RUN.cleanup_owned_compose(state, runner=recorder) is False
    assert calls == []
    preexisting_unlabelled_volume = {
        "buzz_root": buzz,
        "empty_inventory_preflight_passed": not any(hostile_inventory.values()),
        "compose_started_by_run": False,
    }
    assert RUN.cleanup_owned_compose(preexisting_unlabelled_volume, runner=recorder) is False
    assert calls == []
    owned = {
        "buzz_root": buzz,
        "empty_inventory_preflight_passed": True,
        "compose_started_by_run": True,
    }
    assert RUN.cleanup_owned_compose(owned, runner=recorder) is True
    assert len(calls) == 1
    assert calls[0][0] == [
        "docker", "compose", "--project-name", "vela-stock-buzz-proof",
        "--file", "docker-compose.yml", "--project-directory", ".",
        "down", "-v", "--remove-orphans",
    ]
    assert not any(key.startswith("COMPOSE_") for key in calls[0][1]["env"])
    assert owned["compose_started_by_run"] is False

    source = (HERE / "run.py").read_text()
    assert "packet_understood_no_candidate_produced" not in source
    assert '"independent_verification"' not in source
    assert 'relay_log = build_root / "buzz-relay.log"' in source
    assert "Buzz performed no scientific reasoning" in source
    print("stock-buzz-run-guards: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
