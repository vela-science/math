#!/usr/bin/env python3
"""Validate the frozen Phase 0 Math ownership inventory."""

from __future__ import annotations

import json
import subprocess
from collections import Counter
from pathlib import Path


BASELINE_COMMIT = "b1f1a1decd565d9aa38303efaba22d2a54fdf0b8"
BASELINE_TREE = "7c2fe41c80d2706f6709f3fce274e87b835f7e1d"
EXPECTED_COUNTS = {
    "activity_owned": 25,
    "authority_required": 143,
    "core_conformance": 6,
    "historical_evidence": 684,
    "obsolete_unbound": 0,
    "projection_owned": 4,
    "source_owned_future": 65,
}

ROOT = Path(__file__).resolve().parents[1]


def git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.strip()


def is_exact_or_below(path: str, *roots: str) -> bool:
    return any(path == root or path.startswith(root + "/") for root in roots)


def classify(path: str) -> str | None:
    if path in {
        ".gitattributes",
        ".gitignore",
        "AGENTS.md",
        "CLAUDE.md",
        "README.md",
        "vela.toml",
        "evidence/erdos-321/definition-correspondence.v1.json",
        "evidence/erdos-321/definition-correspondence.v2.json",
    } or is_exact_or_below(
        path,
        ".vela",
        "records",
        "continuity",
        "evidence/erdos-321/correction-impact",
        "evidence/erdos-321/terminal-variants",
        "evidence/erdos-522",
        "methods/erdos-321",
        "methods/erdos-522",
        "methods/erdos-887",
        "methods/review-provenance",
        "evidence/formal-conjectures/work-offers/results/erdos-887-pilot-02-current-binding",
    ):
        return "authority_required"

    if path in {
        ".github/workflows/terminal-variant-evidence.yml",
        "evidence/formal-conjectures/work-offers/lifecycle/erdos-887-pr-1237-fidelity-repair.v1.json",
        "evidence/formal-conjectures/work-offers/packets/erdos-887-pr-1237-fidelity-repair.v1.json",
    } or is_exact_or_below(
        path,
        "evidence/erdos-321/external-workbench-return",
        "evidence/erdos-321/translation",
        "evidence/erdos-321/workbench-compatibility",
        "evidence/formal-conjectures/agent-evaluation",
        "evidence/formal-conjectures/reviews",
        "evidence/formal-conjectures/work-offers/execution",
        "evidence/formal-conjectures/work-offers/results/erdos-887-pilot-01",
        "sources/gpt_erdos",
        "sources/wiki",
    ):
        return "historical_evidence"

    if path in {
        ".github/workflows/formal-conjectures-phase-0.yml",
        "sources.yaml",
        "sources.lock.json",
    } or is_exact_or_below(
        path,
        "evidence/formal-conjectures/audit-pilot",
        "evidence/formal-conjectures/source-adapter",
        "methods/formal-conjectures",
    ):
        return "source_owned_future"

    if is_exact_or_below(
        path,
        "evidence/formal-conjectures/conformance",
        "methods/source-adapters",
    ):
        return "core_conformance"

    if is_exact_or_below(path, "evidence/formal-conjectures/campaigns"):
        return "projection_owned"

    if path in {
        "evidence/formal-conjectures/work-offers/README.md",
        "evidence/formal-conjectures/work-offers/build.py",
        "evidence/formal-conjectures/work-offers/index.v1.json",
        "evidence/formal-conjectures/work-offers/packets/erdos-887-proof-discharge.v1.json",
        "evidence/formal-conjectures/work-offers/test_build.py",
    } or is_exact_or_below(
        path,
        "evidence/formal-conjectures/work-offers/proof-discharge",
        "evidence/formal-conjectures/work-offers/results/erdos-887-proof-discharge-attempt-01",
    ):
        return "activity_owned"

    return None


def main() -> None:
    observed_tree = git("rev-parse", f"{BASELINE_COMMIT}^{{tree}}")
    if observed_tree != BASELINE_TREE:
        raise SystemExit(
            f"baseline tree drift: expected {BASELINE_TREE}, observed {observed_tree}"
        )

    paths = git("ls-tree", "-r", "--name-only", BASELINE_COMMIT).splitlines()
    records = [{"path": path, "classification": classify(path)} for path in paths]
    unclassified = [
        record["path"] for record in records if record["classification"] is None
    ]
    if unclassified:
        raise SystemExit("unclassified baseline paths:\n" + "\n".join(unclassified))

    counts = Counter(record["classification"] for record in records)
    counts["obsolete_unbound"] += 0
    observed_counts = dict(sorted(counts.items()))
    if observed_counts != EXPECTED_COUNTS:
        raise SystemExit(
            "ownership count drift: "
            + json.dumps(
                {"expected": EXPECTED_COUNTS, "observed": observed_counts},
                sort_keys=True,
            )
        )

    print(
        json.dumps(
            {
                "ok": True,
                "baseline_commit": BASELINE_COMMIT,
                "baseline_tree": BASELINE_TREE,
                "tracked_paths": len(paths),
                "counts": observed_counts,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )


if __name__ == "__main__":
    main()
