#!/usr/bin/env python3
"""Run and verify a matched context-free CLI reading of the correction."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from typing import Any

import build


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SCHEMA = HERE / "cold-reader-response.schema.json"
RESULT = HERE / "cold-reader-result.v1.json"
EVALUATION = HERE / "cold-reader-evaluation.v1.json"

BASELINE_FILES = (
    "evidence/erdos-321/definition-correspondence.v1.json",
    "evidence/erdos-321/definition-correspondence.v2.json",
    "evidence/erdos-321/translation/semantic-diff.v1.json",
    "evidence/erdos-321/translation/semantic-loss.v1.json",
    "evidence/erdos-321/terminal-variants/comparison.v0.1.json",
    "records/claims/sha256/40dec807844df7badd60cab570b811a1c6137bd0d0a9b6d1408f3b2da33d1f67.json",
    "records/claims/sha256/d5d77e7d96e390e0bf692d0abd44367eb06a0c6a61534e1c6654962d6c644776.json",
    ".vela/authority/events/vev_e045ff0592e193fa.json",
    ".vela/authority/events/vev_fb652e14f2a9323f.json",
)
TREATMENT_FILE = "evidence/erdos-321/correction-impact/correction-impact.v1.json"

EXPECTED = {
    "affected_relation_ids": ["admissible_relation", "correspondence_structure", "fixed_statement_availability"],
    "conclusion_changed": False,
    "incomplete_basis_relation_ids": ["dependency_cone", "fresh_kernel_rebuild"],
    "predecessor_verdict": "rejected",
    "report_authority_effect": "none",
    "successor_verdict": "accepted",
    "unresolved_relation_ids": ["optimality_and_open_problem", "terminal_to_fixed_lower", "terminal_to_fixed_upper"],
}


def prompt(files: list[str]) -> str:
    listed = "\n".join(f"- {path}" for path in files)
    return f"""You are a context-free reader. Use only the files below. Do not use the network, inspect any parent directory, or write files.

Files:
{listed}

Return the required JSON object. Determine whether the corrected scientific conclusion changed; classify every affected, unresolved, and incomplete-basis relation represented by the response schema; identify the predecessor and successor human verdicts; state whether this report itself has authority effect; and state the next repair obligation. Evidence files must be paths from the list above. Do not treat a Verification as acceptance or an open obligation as completed."""


def copy_inputs(destination: Path, paths: list[str]) -> None:
    for relative in paths:
        source = REPO / relative
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def usage_from_events(raw: str) -> dict[str, int]:
    usage: dict[str, int] = {}
    for line in raw.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        candidate = event.get("usage")
        if not isinstance(candidate, dict):
            candidate = event.get("data", {}).get("usage") if isinstance(event.get("data"), dict) else None
        if isinstance(candidate, dict):
            usage = {key: value for key, value in candidate.items() if isinstance(key, str) and isinstance(value, int)}
    return usage


def score(response: dict[str, Any]) -> dict[str, Any]:
    components: dict[str, bool] = {}
    for key, expected in EXPECTED.items():
        observed = response.get(key)
        if isinstance(expected, list):
            components[key] = sorted(observed or []) == sorted(expected)
        else:
            components[key] = observed == expected
    obligation = response.get("next_repair_obligation", "").lower()
    components["next_repair_obligation"] = all(token in obligation for token in ("kernel", "bridge", "nat.log"))
    return {"components": components, "correct": sum(components.values()), "possible": len(components)}


def run_arm(codex: str, label: str, files: list[str]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix=f"vela-321-{label}-") as temporary:
        root = Path(temporary)
        copy_inputs(root, files)
        output = root / "response.json"
        started = time.monotonic_ns()
        completed = subprocess.run(
            [
                codex,
                "exec",
                "--ephemeral",
                "--sandbox",
                "read-only",
                "--skip-git-repo-check",
                "--output-schema",
                str(SCHEMA),
                "--json",
                "--color",
                "never",
                "-o",
                str(output),
                "-C",
                str(root),
                prompt(files),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        elapsed = (time.monotonic_ns() - started) // 1_000_000
        response = build.load_json(output)
        observed = score(response)
        return {
            "arm": label,
            "duration_ms": elapsed,
            "input_descriptors": [build.descriptor(path) for path in files],
            "response": response,
            "score": observed,
            "usage": usage_from_events(completed.stdout),
        }


def validate_result(result: dict[str, Any]) -> None:
    candidate = copy.deepcopy(result)
    observed_root = candidate.pop("content_root", None)
    if observed_root != build.root(candidate):
        raise build.BuildError("cold-reader result root drift")
    if result.get("schema") != "vela.math.correction-cold-reader.v1" or result.get("authority_effect") != "none":
        raise build.BuildError("cold-reader schema or authority drift")
    if [arm.get("arm") for arm in result.get("arms", [])] != ["baseline", "treatment"]:
        raise build.BuildError("cold-reader arm inventory drift")
    for arm in result["arms"]:
        expected_files = list(BASELINE_FILES) + ([TREATMENT_FILE] if arm["arm"] == "treatment" else [])
        if arm["input_descriptors"] != [build.descriptor(path) for path in expected_files]:
            raise build.BuildError("cold-reader input drift")
        if arm["score"] != score(arm["response"]):
            raise build.BuildError("cold-reader score drift")
    if result.get("nonclaims") != [
        "The context-free readers were Codex CLI sessions operated by one experimenter, not independent human participants.",
        "A correct response does not establish scientific correctness, adoption, Verification, Decision, or Standing.",
        "The elapsed durations include model and tool latency and are not human reviewer minutes.",
    ]:
        raise build.BuildError("cold-reader nonclaim drift")


def evaluate_result(result: dict[str, Any]) -> dict[str, Any]:
    validate_result(result)
    baseline, treatment = result["arms"]
    baseline_usage, treatment_usage = baseline["usage"], treatment["usage"]
    return build.with_root({
        "schema": "vela.math.correction-cold-reader-evaluation.v1",
        "authority_effect": "none",
        "input_result_root": result["content_root"],
        "measures": {
            "baseline_correct": baseline["score"]["correct"],
            "baseline_possible": baseline["score"]["possible"],
            "treatment_correct": treatment["score"]["correct"],
            "treatment_possible": treatment["score"]["possible"],
            "correctness_lift": treatment["score"]["correct"] - baseline["score"]["correct"],
            "baseline_duration_ms": baseline["duration_ms"],
            "treatment_duration_ms": treatment["duration_ms"],
            "duration_delta_ms": treatment["duration_ms"] - baseline["duration_ms"],
            "baseline_input_tokens": baseline_usage.get("input_tokens"),
            "treatment_input_tokens": treatment_usage.get("input_tokens"),
            "input_token_delta": treatment_usage.get("input_tokens", 0) - baseline_usage.get("input_tokens", 0),
        },
        "disposition": {
            "interface": "correction-impact-v1",
            "status": "retain_source_locally",
            "reason": "This single agent-only rehearsal showed no correctness lift and increased elapsed latency and input-token burden. Keep the exact source-local view for traceability; do not promote it as a proven comprehension or efficiency improvement.",
        },
        "hypothesis_status": {
            "human_comprehension": "not_tested",
            "human_reviewer_minutes": "not_tested",
            "independent_reader_portability": "not_tested",
            "agent_context_free_reconstruction": "both_arms_complete_with_no_observed_accuracy_lift",
        },
        "nonclaims": [
            "One paired agent rehearsal is not a sample, an estimator of human effect, or independent validation.",
            "Elapsed model latency is not reviewer minutes.",
            "The disposition has no effect on Repository Standing or the historical human Decisions.",
        ],
    })


def validate_evaluation(evaluation: dict[str, Any], result: dict[str, Any]) -> None:
    candidate = copy.deepcopy(evaluation)
    observed_root = candidate.pop("content_root", None)
    if observed_root != build.root(candidate):
        raise build.BuildError("cold-reader evaluation root drift")
    if evaluation != evaluate_result(result):
        raise build.BuildError("cold-reader evaluation does not match retained result")


def run(codex: str) -> dict[str, Any]:
    before = subprocess.run(["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=REPO, check=True, stdout=subprocess.PIPE).stdout
    arms = [
        run_arm(codex, "baseline", list(BASELINE_FILES)),
        run_arm(codex, "treatment", [*BASELINE_FILES, TREATMENT_FILE]),
    ]
    after = subprocess.run(["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=REPO, check=True, stdout=subprocess.PIPE).stdout
    if before != after:
        raise build.BuildError("reader sessions changed the repository")
    result = build.with_root({
        "schema": "vela.math.correction-cold-reader.v1",
        "authority_effect": "none",
        "reader_class": "agent_context_free_cli",
        "arms": arms,
        "nonclaims": [
            "The context-free readers were Codex CLI sessions operated by one experimenter, not independent human participants.",
            "A correct response does not establish scientific correctness, adoption, Verification, Decision, or Standing.",
            "The elapsed durations include model and tool latency and are not human reviewer minutes.",
        ],
    })
    validate_result(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--codex", default=shutil.which("codex"))
    parser.add_argument("--evaluate-existing", action="store_true")
    parser.add_argument("--verify", action="store_true")
    arguments = parser.parse_args()
    if arguments.verify:
        retained = build.load_json(RESULT)
        validate_result(retained)
        validate_evaluation(build.load_json(EVALUATION), retained)
    elif arguments.evaluate_existing:
        retained = build.load_json(RESULT)
        validate_result(retained)
        EVALUATION.write_bytes(build.rendered(evaluate_result(retained)))
        validate_evaluation(build.load_json(EVALUATION), retained)
    else:
        if not arguments.codex:
            raise build.BuildError("codex executable not found")
        RESULT.write_bytes(build.rendered(run(arguments.codex)))
        retained = build.load_json(RESULT)
        validate_result(retained)
        EVALUATION.write_bytes(build.rendered(evaluate_result(retained)))
        validate_evaluation(build.load_json(EVALUATION), retained)
    print(build.load_json(EVALUATION)["content_root"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
