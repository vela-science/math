#!/usr/bin/env python3
"""Focused no-network tests for the terminal-variant evidence builder."""

from __future__ import annotations

import importlib.util
import copy
import json
from pathlib import Path
import os
import stat
import subprocess
import tempfile


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("terminal_variant_build", HERE / "build.py")
assert SPEC is not None and SPEC.loader is not None
BUILD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)


def expect_error(callable_value, fragment: str) -> None:
    try:
        callable_value()
    except BUILD.BuildError as error:
        if fragment not in str(error):
            raise AssertionError(f"expected {fragment!r}, got {error!r}") from error
    else:
        raise AssertionError(f"expected failure containing {fragment!r}")


def main() -> int:
    source_repo = Path(os.environ.get(
        "VELA_LEAN_PROOFS_REPO",
        str(BUILD.ROOT.parent / "lean-proofs"),
    ))
    mathlib_repo = Path(os.environ["VELA_MATHLIB_REPO"])
    pnt_repo = Path(os.environ["VELA_PNT_REPO"])
    documents = BUILD.documents(
        BUILD.exact_real_directory(str(source_repo.resolve())),
        BUILD.exact_real_directory(str(mathlib_repo.resolve())),
        BUILD.exact_real_directory(str(pnt_repo.resolve())),
    )
    assert tuple(documents) == BUILD.OUTPUT_NAMES
    manifest = documents["source-lock.v0.1.json"]
    inventory = manifest["terminal_source"]["proof_ci_rights_inventory"]
    assert len(inventory) == BUILD.SOURCE_INVENTORY_COUNT
    assert all(row["mode"] == "100644" for row in inventory)
    assert manifest["terminal_source"]["tree"] == BUILD.SOURCE_TREE
    assert manifest["terminal_source"]["project_subtree"] == BUILD.SOURCE_PROJECT_TREE
    assert manifest["terminal_source"]["inventory_root"] == BUILD.SOURCE_INVENTORY_ROOT
    assert sum(row["byte_length"] for row in inventory) == BUILD.SOURCE_INVENTORY_BYTES
    assert manifest["terminal_source"]["project_lake_manifest"]["status"] == "absent_at_pinned_tree"
    assert manifest["proof_environment"]["historical_reconstruction_status"] == "not exact"
    assert manifest["math_base"] == {
        "commit": BUILD.MATH_COMMIT,
        "objects": manifest["math_base"]["objects"],
        "tree": BUILD.MATH_TREE,
    }
    assert manifest["proof_environment"]["mutable_historical_inputs"]
    assert manifest["proof_environment"]["mathlib"]["tree"] == BUILD.MATHLIB_TREE
    assert manifest["proof_environment"]["prime_number_theorem_and"]["tree"] == BUILD.PNT_TREE
    dependency = manifest["proof_environment"]["dependency_resolution"]
    assert dependency["status"] == "basis_unavailable_in_pinned_tree"
    assert dependency["project_mathlib_commit"] == BUILD.MATHLIB_COMMIT
    assert dependency["prime_number_theorem_and_manifest_mathlib_commit"] == "db127794c79fdeb86f6b0cf6ff2c804026fbaff1"
    assert manifest["rights"]["rights_class"] == "NOASSERTION"
    assert manifest["rights"]["handling"] == "reference_only"
    assert manifest["rights"]["downstream_redistribution_rights"] == "not_established"
    assert "hosting permission only" in manifest["rights"]["permission_basis"]
    assert "copies no Star Fleet theorem source bytes" in manifest["rights"]["handling_detail"]
    assert documents["comparison.v0.1.json"]["authority_effect"] == "none"
    assert documents["comparison.v0.1.json"]["comparison"]["formal_bridge_status"] == "not_constructed"
    relations = documents["comparison.v0.1.json"]["comparison"]["per_variant_relations"]
    assert [relation["candidate_index_alignment"] for relation in relations] == ["k = d + 2", "r = d + 2"]
    assert "1 / log 2 * log^[r] N" in relations[1]["constant_delta"]
    assert "automatically supplies 1 <= r" in relations[1]["condition_delta"]
    assert "d >= 2" not in relations[1]["condition_delta"]
    assert documents["plan.v0.1.json"]["status"] == "preregistered_not_run"
    plan = documents["plan.v0.1.json"]
    instrument = BUILD.read_instrument()
    participant_packet = BUILD.read_rooted_json(BUILD.PARTICIPANT_PACKET_NAME)
    assert {key: value["lines"] for key, value in participant_packet["evidence_locator_catalog"].items()} == {
        "span_01": "5-9", "span_02": "11-15", "span_03": "19-20", "span_04": "21-24",
        "span_05": "31-37", "span_06": "93-95", "span_07": "108-110", "span_08": "34-63",
    }
    assert plan["reader_instrument_root"] == instrument["content_root"]
    assert plan["participant_packet_root"] == participant_packet["content_root"]
    assert instrument["status"] == "frozen_not_run"
    assert instrument["assignment_schedule"]["participant_classes"]["human"]["initial_sequence"] == "baseline_first"
    assert instrument["assignment_schedule"]["participant_classes"]["model"]["target"] == 0
    assert instrument["observed_enrollment_ledger"]["status"] == "not_created"
    assert instrument["periods"]["first"].endswith("primary analysis")
    assert "exposed follow-up" in instrument["periods"]["second"]
    assert "compare the terminal theorem" in participant_packet["prompt"]
    assert "overlapping" not in participant_packet["prompt"] and "implication" not in participant_packet["prompt"]
    exclusions = "\n".join(instrument["eligibility"]["exclude"])
    assert all(term in exclusions for term in ("comparison.v0.1.json", "plan.v0.1.json", "README", "reader_scorer.py"))
    assert all(
        measurement["status"] == "not_measured" and measurement["value"] is None
        for measurement in instrument["measurements"]
    )
    drifted_definition = copy.deepcopy(instrument)
    drifted_definition["content_root_definition"] = "arbitrary definition"
    expect_error(lambda: BUILD.validate_rooted(drifted_definition, "instrument"), "definition drift")
    assert not any(path.suffix == ".lean" for path in HERE.rglob("*.lean"))
    generated_bytes = b"".join(
        BUILD.rendered(documents[name]) for name in BUILD.OUTPUT_NAMES
    )
    terminal_source = BUILD.run_git(
        source_repo, "show", f"{BUILD.SOURCE_COMMIT}:starfleet/erdos-321/Research/FinalAsymptotic.lean",
    )
    assert terminal_source not in generated_bytes

    expect_error(lambda: BUILD.exact_real_directory(str(source_repo.parent / "missing")), "missing")
    with tempfile.TemporaryDirectory() as alias_parent_raw:
        alias_parent = Path(alias_parent_raw)
        alias = alias_parent / "source-link"
        alias.symlink_to(source_repo.resolve(), target_is_directory=True)
        expect_error(lambda: BUILD.exact_real_directory(str(alias)), "non-symlink")

    with tempfile.TemporaryDirectory() as first_raw, tempfile.TemporaryDirectory() as second_raw:
        first = Path(first_raw)
        second = Path(second_raw)
        first_outputs = {name: BUILD.rendered(value) for name, value in documents.items()}
        second_outputs = {name: BUILD.rendered(value) for name, value in documents.items()}
        BUILD.write_outputs(first, first_outputs)
        BUILD.write_outputs(second, second_outputs)
        assert {path.name: path.read_bytes() for path in first.iterdir()} == {
            path.name: path.read_bytes() for path in second.iterdir()
        }
        link = first / "blocked.json"
        link.symlink_to(first / "source-lock.v0.1.json")
        expect_error(
            lambda: BUILD.write_outputs(first, {"blocked.json": b"{}\n"}),
            "regular file",
        )
        mode_target = first / "source-lock.v0.1.json"
        mode_target.chmod(0o755)
        assert stat.S_IMODE(mode_target.stat().st_mode) == 0o755
        assert BUILD.main([
            "--lean-proofs-repo", str(source_repo.resolve()),
            "--mathlib-repo", str(mathlib_repo.resolve()),
            "--pnt-repo", str(pnt_repo.resolve()),
            "--output-dir", str(first.resolve()),
            "--check",
        ]) == 1
        mode_target.chmod(0o644)
        mode_target.write_bytes(mode_target.read_bytes() + b"x")
        expect_error(lambda: BUILD.check_outputs(first.resolve(), first_outputs), "bounded regular file")

    with tempfile.TemporaryDirectory() as failed_write_raw:
        failed_write = Path(failed_write_raw).resolve()
        original_fsync = BUILD.os.fsync
        try:
            BUILD.os.fsync = lambda _descriptor: (_ for _ in ()).throw(OSError("forced fsync failure"))
            try:
                BUILD.write_outputs(failed_write, {"failed.json": b"{}\n"})
            except OSError as error:
                assert "forced fsync failure" in str(error)
            else:
                raise AssertionError("forced fsync failure was accepted")
        finally:
            BUILD.os.fsync = original_fsync
        assert list(failed_write.iterdir()) == []

    with tempfile.TemporaryDirectory() as alias_output_raw:
        base = Path(alias_output_raw).resolve()
        real_parent = base / "real"
        output = real_parent / "output"
        output.mkdir(parents=True)
        alias = base / "alias"
        alias.symlink_to(real_parent, target_is_directory=True)
        assert BUILD.main([
            "--lean-proofs-repo", str(source_repo.resolve()),
            "--mathlib-repo", str(mathlib_repo.resolve()),
            "--pnt-repo", str(pnt_repo.resolve()),
            "--output-dir", str(alias / "output"),
            "--check",
        ]) == 1

    baseline_outputs = {
        name: BUILD.rendered(value) for name, value in documents.items()
    }
    hostile_environment = {
        "GIT_DIR": "/definitely/not/the/source",
        "GIT_WORK_TREE": "/definitely/not/the/worktree",
        "GIT_OBJECT_DIRECTORY": "/definitely/not/the/objects",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES": "/definitely/not/the/alternates",
        "GIT_CONFIG_GLOBAL": "/definitely/not/the/config",
        "GIT_CONFIG_SYSTEM": "/definitely/not/the/system-config",
        "GIT_REPLACE_REF_BASE": "refs/replace-hostile/",
    }
    prior_environment = {key: os.environ.get(key) for key in hostile_environment}
    try:
        os.environ.update(hostile_environment)
        hostile_documents = BUILD.documents(source_repo, mathlib_repo, pnt_repo)
    finally:
        for key, value in prior_environment.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    assert {
        name: BUILD.rendered(value) for name, value in hostile_documents.items()
    } == baseline_outputs

    with tempfile.TemporaryDirectory() as hostile_clone_raw:
        hostile_clone = Path(hostile_clone_raw) / "lean-proofs"
        subprocess.run(
            ["git", "clone", "--local", "--no-hardlinks", str(source_repo), str(hostile_clone)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            ["git", "-C", str(hostile_clone), "remote", "set-url", "origin", BUILD.SOURCE_REMOTE],
            check=True,
        )
        common = Path(BUILD.run_git(hostile_clone, "rev-parse", "--git-common-dir").decode().strip())
        if not common.is_absolute():
            common = hostile_clone / common
        alternates = common / "objects" / "info" / "alternates"
        alternates.parent.mkdir(parents=True, exist_ok=True)
        alternates.write_text("/untrusted/object/store\n", encoding="utf-8")
        expect_error(
            lambda: BUILD.verify_local_object_store(hostile_clone, BUILD.SOURCE_REMOTE),
            "alternate object store",
        )
        alternates.unlink()
        subprocess.run(
            ["git", "-C", str(hostile_clone), "config", "--local", "remote.origin.promisor", "true"],
            check=True,
        )
        expect_error(
            lambda: BUILD.verify_local_object_store(hostile_clone, BUILD.SOURCE_REMOTE),
            "promisor object store",
        )

    with tempfile.TemporaryDirectory() as print_root_raw:
        print_root_directory = Path(print_root_raw)
        result = BUILD.main([
            "--lean-proofs-repo", str(source_repo.resolve()),
            "--mathlib-repo", str(mathlib_repo.resolve()),
            "--pnt-repo", str(pnt_repo.resolve()),
            "--output-dir", str(print_root_directory),
            "--print-root",
        ])
        assert result == 0
        assert list(print_root_directory.iterdir()) == []

    for name, value in documents.items():
        parsed = json.loads(BUILD.rendered(value))
        content_root = parsed.pop("content_root")
        assert content_root == f"sha256:{BUILD.sha256_hex(BUILD.jcs(parsed))}", name

    expected_paths = {
        "AGENTS.md", "README.md", ".github/workflows/terminal-variant-evidence.yml",
        *(f"evidence/erdos-321/terminal-variants/{name}" for name in (
            "README.md", "build.py", "comparison.v0.1.json", "plan.v0.1.json",
            "evidence_rooting.py", "participant-packet.v0.1.json", "reader-instrument.v0.1.json",
            "reader_protocol.py", "reader_protocol_test.py", "reader_scorer.py",
            "source-lock.v0.1.json", "test_build.py",
        )),
    }
    workflow_contract = (BUILD.ROOT / ".github/workflows/terminal-variant-evidence.yml").read_text()
    assert workflow_contract.count('- "README.md"') == 2
    assert 'git diff --check "$base"...HEAD' in workflow_contract
    unit_readme = (HERE / "README.md").read_text()
    assert "python3 evidence/erdos-321/terminal-variants/" not in unit_readme
    changed_paths = set(BUILD.run_git(BUILD.ROOT, "diff", "--name-only", BUILD.MATH_COMMIT).decode().splitlines())
    changed_paths.update(BUILD.run_git(BUILD.ROOT, "ls-files", "--others", "--exclude-standard").decode().splitlines())
    assert changed_paths == expected_paths
    assert BUILD.run_git(BUILD.ROOT, "diff", "--", ".vela", "records", "methods", "continuity") == b""
    assert BUILD.run_git(BUILD.ROOT, "merge-base", "--is-ancestor", BUILD.MATH_COMMIT, "HEAD") == b""
    a6 = "a6a31a528ee86ab79c2aaf4e71e43fc63f4a4e98"
    assert subprocess.run(
        ["git", "--no-replace-objects", "-C", str(BUILD.ROOT), "merge-base", "--is-ancestor", a6, "HEAD"],
        check=False, env=BUILD.git_environment(), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    ).returncode == 1
    bundle_root = f"sha256:{BUILD.sha256_hex(BUILD.jcs(BUILD.output_inventory(baseline_outputs)))}"
    assert (BUILD.ROOT / "README.md").read_text().count(bundle_root) == 1
    assert not any(path.name == "__pycache__" for path in BUILD.ROOT.rglob("__pycache__"))
    print("erdos-321-terminal-variants-tests: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
