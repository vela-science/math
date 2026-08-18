#!/usr/bin/env python3
"""Source-occurrence baseline that reads only an exported candidate bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
from pathlib import Path
from typing import Any


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def pretty(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode()


def sha256(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def derive_response(bundle: Path) -> dict[str, Any]:
    task = load(bundle / "task.json")
    claim_entry = next(
        entry
        for entry in task["candidate_view"]["inclusions"]
        if entry["role"] == "accepted_predecessor_claim"
    )
    source_entry = next(
        entry
        for entry in task["candidate_view"]["inclusions"]
        if entry["role"] == "formal_source_snapshot"
    )
    claim = load(bundle / "inputs" / claim_entry["path"])
    source = (bundle / "inputs" / source_entry["path"]).read_text(encoding="utf-8")
    namespace_match = re.search(
        r"^namespace\s+([A-Za-z0-9_]+)\s*$", source, re.MULTILINE
    )
    declarations = re.findall(r"^theorem\s+([A-Za-z0-9_.]+)\b", source, re.MULTILINE)
    namespace = namespace_match.group(1) if namespace_match else ""
    wanted = [
        name
        for name in declarations
        if name in {"erdos_321", "erdos_321.variants.isTheta"}
    ]
    occurrences = sorted(f"{namespace}.{name}" for name in wanted if namespace)
    assertion = claim["assertion"]["text"]
    exact_is_theta = next(
        (item for item in occurrences if item.endswith(".variants.isTheta")), None
    )
    mismatch = exact_is_theta is not None and exact_is_theta not in assertion

    if len(occurrences) != 2 or not mismatch:
        return {
            "action": "refuse",
            "format": "math.time-frozen-replay-response.v1",
            "nonclaims": ["problem_resolution", "scientific_acceptance"],
            "rationale": "The retained t0 sources do not yield one unambiguous namespace-qualified occurrence correction.",
            "refusal_reason": "ambiguous_occurrence",
            "relation": None,
            "required_evidence": [],
            "scope": "no_transition",
            "subject_occurrences": [],
            "target_claim_id": task["t0"]["claim"]["claim_id"],
            "target_claim_root": task["t0"]["claim"]["claim_root"],
            "task_id": task["task"]["task_id"],
        }

    return {
        "action": "propose_transition",
        "format": "math.time-frozen-replay-response.v1",
        "nonclaims": [
            "fixed_nat_log_implication",
            "problem_resolution",
            "scientific_acceptance",
            "statement_equivalence",
        ],
        "rationale": "The retained Formal Conjectures source exposes namespace-qualified main and isTheta declarations while the accepted t0 assertion uses a shortened occurrence name. Propose an occurrence-only correction and require source-mapping plus revision-fidelity checks.",
        "refusal_reason": None,
        "relation": "corrects",
        "required_evidence": [
            "claim_revision_fidelity",
            "subject_occurrence_mapping",
        ],
        "scope": "occurrence_resolution_only",
        "subject_occurrences": occurrences,
        "target_claim_id": task["t0"]["claim"]["claim_id"],
        "target_claim_root": task["t0"]["claim"]["claim_root"],
        "task_id": task["task"]["task_id"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--response", type=Path, required=True)
    parser.add_argument("--provenance", type=Path, required=True)
    arguments = parser.parse_args()

    response = derive_response(arguments.bundle)
    response_bytes = pretty(response)
    arguments.response.parent.mkdir(parents=True, exist_ok=True)
    arguments.response.write_bytes(response_bytes)
    manifest = load(arguments.bundle / "bundle-manifest.json")
    provenance = {
        "command": {
            "argv": [
                "python3",
                "baseline.py",
                "--bundle",
                "<candidate-bundle>",
                "--response",
                "candidate-output.json",
                "--provenance",
                "provenance.json",
            ],
            "exit_code": 0,
            "working_directory": "pilot-root",
        },
        "dependencies": [
            "The exporter, baseline, and evaluator use the same Math Git object database and host.",
            "The baseline sees only paths inside the exported candidate bundle by implementation, not by an operating-system sandbox.",
            "No model provider, network source, Repository signer, or authority credential is used.",
        ],
        "environment": {
            "architecture": platform.machine(),
            "os": platform.system(),
            "runtime": platform.python_implementation()
            + " "
            + platform.python_version(),
        },
        "format": "math.time-frozen-replay-provenance.v1",
        "input_bundle_root": manifest["bundle_root"],
        "limitations": [
            "Internal deterministic baseline only; not external validation or evidence of model quality.",
            "The rule detects a namespace/occurrence mismatch and does not judge mathematical truth or semantic equivalence.",
        ],
        "model": None,
        "output_sha256": sha256(response_bytes),
        "performer": {
            "id": "deterministic-tool:source-occurrence-baseline-v1",
            "kind": "deterministic_tool",
        },
        "tools": [
            {
                "name": "python",
                "version": platform.python_version(),
            }
        ],
    }
    arguments.provenance.parent.mkdir(parents=True, exist_ok=True)
    arguments.provenance.write_bytes(pretty(provenance))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
