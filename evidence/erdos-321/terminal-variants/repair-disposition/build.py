#!/usr/bin/env python3
"""Build the exact negative disposition for the terminal bridge obligation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
OUTPUT = HERE / "repair-disposition.v1.json"
LEAN_PROOFS_COMMIT = "a8c2872a27cf8d11cf6744ca4a2c5b49ace5fea0"
LEAN_PROOFS_REMOTE = "https://github.com/williamjblair/lean-proofs.git"
TERMINAL_PATH = "starfleet/erdos-321/Research/FinalAsymptotic.lean"
TERMINAL_SHA256 = "63dd7ba024ec235a47c1b90c638acae758a50f2d0ee4267e0f69b22cd5d9c0b5"
TERMINAL_TOOLCHAIN = "leanprover/lean4:v4.31.0"
FC_COMMIT = "59f30aa314ba225fcd9268723ce8291616df1ab0"
FC_REMOTE = "https://github.com/google-deepmind/formal-conjectures.git"
FC_PATH = "FormalConjectures/ErdosProblems/321.lean"
FC_SHA256 = "601d8486743aede6803feaaefc7bbb73f0aa8873d0296a6a1c5400fd86c32357"
FC_TOOLCHAIN = "leanprover/lean4:v4.27.0"
COMPARISON_PATH = REPO / "evidence/erdos-321/terminal-variants/comparison.v0.1.json"


class BuildError(ValueError):
    pass


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def rooted(value: dict[str, Any]) -> dict[str, Any]:
    result = dict(value)
    result["content_root"] = digest(canonical(result))
    return result


def git(repo: Path, *args: str) -> bytes:
    result = subprocess.run(["git", "--no-replace-objects", "-C", str(repo), *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=30)
    if result.returncode:
        raise BuildError("Git refused exact source read")
    return result.stdout


def source(repo: Path, remote: str, commit: str, path: str, expected_sha: str) -> tuple[bytes, dict[str, Any]]:
    if git(repo, "config", "--get", "remote.origin.url").decode().strip() != remote:
        raise BuildError("source remote drift")
    if git(repo, "rev-parse", f"{commit}^{{commit}}").decode().strip() != commit:
        raise BuildError("source commit drift")
    row = git(repo, "ls-tree", commit, "--", path).decode().strip()
    parts = row.split(maxsplit=3)
    if len(parts) != 4 or parts[0:2] != ["100644", "blob"] or parts[3] != path:
        raise BuildError("source blob identity drift")
    data = git(repo, "cat-file", "blob", parts[2])
    if hashlib.sha256(data).hexdigest() != expected_sha:
        raise BuildError("source bytes drift")
    return data, {"repository": remote, "commit": commit, "path": path, "git_blob_sha1": parts[2], "size": len(data), "raw_sha256": "sha256:" + expected_sha}


def require(text: str, fragments: list[str], label: str) -> None:
    if any(fragment not in text for fragment in fragments):
        raise BuildError(f"{label} declaration drift")


def build(lean_proofs: Path, formal_conjectures: Path) -> dict[str, Any]:
    terminal_raw, terminal = source(lean_proofs, LEAN_PROOFS_REMOTE, LEAN_PROOFS_COMMIT, TERMINAL_PATH, TERMINAL_SHA256)
    fixed_raw, fixed = source(formal_conjectures, FC_REMOTE, FC_COMMIT, FC_PATH, FC_SHA256)
    terminal_toolchain_raw, terminal_toolchain = source(lean_proofs, LEAN_PROOFS_REMOTE, LEAN_PROOFS_COMMIT, "starfleet/erdos-321/lean-toolchain", hashlib.sha256((TERMINAL_TOOLCHAIN + "\n").encode()).hexdigest())
    fc_toolchain_raw, fc_toolchain = source(formal_conjectures, FC_REMOTE, FC_COMMIT, "lean-toolchain", hashlib.sha256(FC_TOOLCHAIN.encode()).hexdigest())
    if terminal_toolchain_raw.decode().strip() != TERMINAL_TOOLCHAIN or fc_toolchain_raw.decode().strip() != FC_TOOLCHAIN:
        raise BuildError("toolchain text drift")
    terminal_text, fixed_text = terminal_raw.decode(), fixed_raw.decode()
    require(terminal_text, ["theorem erdos321_asymptotic", "IsTerminalLogDepth B n d", "c * terminalReciprocalScale n d", "C * terminalReciprocalScale n d"], "terminal")
    require(fixed_text, ["theorem erdos_321.variants.lower", "k ≤ log^[k] N", "theorem erdos_321.variants.upper", "1 ≤ log^[2 * r] N"], "fixed")
    comparison_raw = COMPARISON_PATH.read_bytes()
    comparison = json.loads(comparison_raw)
    if comparison["content_root"] != "sha256:808c9ba973d36b0ed79366ae04357c04e2c5b2c0aa5a04967f90ad09eabba699":
        raise BuildError("comparison root drift")
    document = {
        "schema": "vela.math.erdos321-terminal-bridge-disposition.v1",
        "authority_effect": "none",
        "problem": "erdos:321",
        "question": "Do the retained terminal theorem premises establish either fixed Nat.log variant after the candidate endpoint substitutions?",
        "sources": {
            "terminal": {**terminal, "toolchain": {**terminal_toolchain, "value": TERMINAL_TOOLCHAIN}},
            "fixed_variants": {**fixed, "toolchain": {**fc_toolchain, "value": FC_TOOLCHAIN}},
            "comparison": {"path": COMPARISON_PATH.relative_to(REPO).as_posix(), "size": len(comparison_raw), "raw_sha256": digest(comparison_raw), "content_root": comparison["content_root"]},
        },
        "candidate_alignments": [
            {"variant": "lower", "substitution": "k = d + 2", "establishes": "displayed product endpoint alignment only"},
            {"variant": "upper", "substitution": "r = d + 2", "establishes": "displayed product endpoint alignment only"},
        ],
        "missing_bridges": [
            {"id": "lower_hypothesis", "required": "4 <= d + 2 and d + 2 <= Nat.log^[d + 2] n", "terminal_basis": "d <= n and a Real.log tower around Real.log (Real.log n)", "retained_theorem": None},
            {"id": "upper_hypothesis", "required": "1 <= d + 2 and 1 <= Nat.log^[2 * (d + 2)] n", "terminal_basis": "terminal real-log threshold conditions", "retained_theorem": None},
            {"id": "coordinate_product", "required": "an exact coercion and equality or inequality between the Nat.log product and iteratedLogTailProduct", "terminal_basis": "real-valued recursive logarithm product", "retained_theorem": None},
            {"id": "constants", "required": "a theorem relating existential c and C to the fixed explicit coefficients", "terminal_basis": "existential positive c and nonnegative C", "retained_theorem": None},
        ],
        "execution": {
            "source_identity_check": "pass",
            "source_statement_check": "pass",
            "common_exact_interpreter": "unavailable",
            "reason": "the retained projects use Lean 4.31.0 and Lean 4.27.0 and retain no cross-version port or bridge module",
            "kernel_bridge_result": "not_observed",
        },
        "disposition": {
            "status": "unsupported_by_retained_basis",
            "relation_lower": "unresolved",
            "relation_upper": "unresolved",
            "claim": "At the exact retained source revisions, the terminal theorem and structural comparison do not establish implication to either fixed Nat.log variant.",
            "next_action": "Retain both relations as unresolved. Reopen only with a rooted common-source port and an explicit kernel-checked bridge theorem.",
        },
        "does_not_establish": [
            "No mathematical impossibility of a bridge is claimed.",
            "Neither terminal nor fixed statement is shown false.",
            "The candidate index substitutions are not variable-substitution theorems.",
            "No fresh terminal or fixed theorem execution is claimed.",
            "This record is not a Vela Verification, Decision, or Standing change."
        ],
    }
    return rooted(document)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lean-proofs-repo", type=Path, required=True)
    parser.add_argument("--formal-conjectures-repo", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    document = build(args.lean_proofs_repo.resolve(), args.formal_conjectures_repo.resolve())
    raw = (json.dumps(document, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode()
    if args.check:
        if OUTPUT.read_bytes() != raw:
            raise BuildError("repair disposition drift")
    else:
        OUTPUT.write_bytes(raw)
    print(document["content_root"])


if __name__ == "__main__":
    main()
