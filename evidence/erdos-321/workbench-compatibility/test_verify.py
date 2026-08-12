#!/usr/bin/env python3
"""Hostile drift tests for the frozen stock-Buzz evidence verifier."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import shutil
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("stock_buzz_verify", HERE / "verify.py")
VERIFY = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(VERIFY)
EXPECTED = json.loads((HERE / "run-manifest.json").read_text())["aggregate_evidence_root"]


def mutate(name: str, callback) -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        for source in HERE.iterdir():
            if source.is_file():
                shutil.copy2(source, root / source.name)
        path = root / name
        value = json.loads(path.read_text())
        callback(value)
        path.write_bytes(json.dumps(value, indent=2).encode() + b"\n")
        try:
            VERIFY.verify(root, EXPECTED)
        except (AssertionError, KeyError, TypeError, ValueError):
            return
        raise AssertionError(f"hostile mutation unexpectedly passed: {name}")


def write_json(path: Path, value: dict) -> None:
    path.write_bytes(json.dumps(value, indent=2).encode() + b"\n")


def reroot(value: dict, key: str) -> None:
    value.pop(key, None)
    value[key] = VERIFY.sha256(VERIFY.canonical(value))


def semantic_execution_mutate(callback) -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        for source in HERE.iterdir():
            if source.is_file():
                shutil.copy2(source, root / source.name)
        execution_path = root / "execution-evidence.json"
        execution = json.loads(execution_path.read_text())
        callback(execution)
        reroot(execution, "execution_root")
        write_json(execution_path, execution)
        manifest_path = root / "run-manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["execution_root"] = execution["execution_root"]
        manifest["files"]["execution-evidence.json"] = VERIFY.file_fact(execution_path)
        reroot(manifest, "aggregate_evidence_root")
        write_json(manifest_path, manifest)
        try:
            VERIFY.verify(root)
        except (AssertionError, KeyError, TypeError, ValueError):
            return
        raise AssertionError("semantic execution mutation unexpectedly passed")


def semantic_manifest_mutate(callback) -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        for source in HERE.iterdir():
            if source.is_file():
                shutil.copy2(source, root / source.name)
        manifest_path = root / "run-manifest.json"
        manifest = json.loads(manifest_path.read_text())
        callback(manifest)
        reroot(manifest, "aggregate_evidence_root")
        write_json(manifest_path, manifest)
        try:
            VERIFY.verify(root)
        except (AssertionError, KeyError, TypeError, ValueError):
            return
        raise AssertionError("semantic manifest mutation unexpectedly passed")


def main() -> int:
    result = VERIFY.verify(HERE, EXPECTED)
    assert result["ok"] and result["events"] == 3
    mutate("events.json", lambda value: value["events"][0].__setitem__("content", "drift"))
    mutate(
        "execution-evidence.json",
        lambda value: value["build"]["binaries"]["buzz"].__setitem__("raw_sha256", "sha256:" + "0" * 64),
    )
    mutate(
        "execution-evidence.json",
        lambda value: value["command_ledger"][0].__setitem__("command_id", "shell"),
    )
    mutate(
        "execution-evidence.json",
        lambda value: value["teardown"]["after"]["containers"].append("buzz-postgres"),
    )
    mutate(
        "execution-evidence.json",
        lambda value: value["protected_vela_state"].__setitem__("changed", True),
    )
    mutate(
        "nostr-verification.json",
        lambda value: value.__setitem__("nostr_tools_version", "latest"),
    )
    mutate(
        "run-manifest.json",
        lambda value: value.__setitem__("aggregate_evidence_root", "sha256:" + "f" * 64),
    )
    semantic_execution_mutate(
        lambda value: value["source"]["custody"].__setitem__("lazy_fetch_disabled", False)
    )
    semantic_execution_mutate(
        lambda value: value["teardown"].__setitem__(
            "external_build_directory_and_relay_log_absent", False
        )
    )
    semantic_execution_mutate(
        lambda value: value["cross_implementation_signature_verification"].__setitem__(
            "verification_scope", "scientific_verification"
        )
    )
    semantic_execution_mutate(
        lambda value: value["command_ledger"][0]["argv"].append("--hostile")
    )
    semantic_manifest_mutate(
        lambda value: value["result"].__setitem__("buzz_scientific_reasoning", True)
    )
    with contextlib.redirect_stdout(io.StringIO()):
        assert VERIFY.verify(HERE, EXPECTED)["authority_effect"] == "none"
    print(json.dumps({"ok": True, "hostile_mutations_refused": 12}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
