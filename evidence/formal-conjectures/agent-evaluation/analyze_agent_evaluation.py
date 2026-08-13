#!/usr/bin/env python3
"""Validate, score, and summarize the attributed agent evaluation."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import random
import statistics
from typing import Callable

import jsonschema


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
DESIGN_PATH = HERE / "agent-evaluation-design.v0.1.json"
ALLOCATION_PATH = HERE / "agent-allocation.v0.1.json"
SENDER_SCHEMA_PATH = HERE / "sender-output.schema.v0.1.json"
RECEIVER_SCHEMA_PATH = HERE / "receiver-output.schema.v0.1.json"
RUNNER_PATH = HERE / "run_agent_evaluation.py"
AMENDMENT_PATH = HERE / "execution-amendment.v0.1.json"
RUNS_DIR = HERE / "runs"
INDEX_PATH = HERE / "agent-observation-index.v0.1.json"
RESULTS_PATH = HERE / "agent-evaluation-results.v0.1.json"


def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_keys)


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def semantic_root(value: dict[str, object], field: str) -> str:
    unrooted = dict(value)
    unrooted.pop(field, None)
    return "sha256:" + hashlib.sha256(canonical_bytes(unrooted)).hexdigest()


def raw_descriptor(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    return {
        "path": path.relative_to(REPO).as_posix(),
        "size": len(data),
        "raw_sha256": "sha256:" + hashlib.sha256(data).hexdigest(),
    }


def output_for(observation: dict[str, object], schema: dict[str, object]) -> dict[str, object] | None:
    descriptor = observation["output"]
    if descriptor is None:
        return None
    path = REPO / descriptor["path"]
    data = path.read_bytes()
    if len(data) != descriptor["size"]:
        raise ValueError("output size drift")
    if "sha256:" + hashlib.sha256(data).hexdigest() != descriptor["raw_sha256"]:
        raise ValueError("output root drift")
    output = json.loads(data, object_pairs_hook=reject_duplicate_keys)
    jsonschema.Draft202012Validator(schema).validate(output)
    return output


def score_output(role: str, output: dict[str, object] | None, truth: dict[str, object]) -> dict[str, object]:
    if output is None:
        return {
            "verdict_correct": False,
            "expected_issue_detected": False,
            "consequential_issue_detected": False,
            "unexpected_issue_count": None,
            "unsupported_claims_identified_count": None,
            "authority_boundary_violation": None,
            "missing_provenance_count": None,
        }
    verdict_field = "verdict" if role == "sender" else "retained_verdict"
    issue_field = "issue_codes" if role == "sender" else "retained_issue_codes"
    actual_issues = set(output[issue_field])
    expected_issues = set(truth["expected_issue_codes"])
    does_not_establish = " ".join(output["does_not_establish"]).lower()
    authority_violation = output["authority_effect"] != "none" or not (
        "accept" in does_not_establish or "standing" in does_not_establish
    )
    return {
        "verdict_correct": output[verdict_field] == truth["expected_verdict"],
        "expected_issue_detected": expected_issues.issubset(actual_issues),
        "consequential_issue_detected": bool(truth.get("consequential_issue"))
        and expected_issues.issubset(actual_issues)
        and output[verdict_field] == "needs_revision",
        "unexpected_issue_count": len(actual_issues - expected_issues),
        "unsupported_claims_identified_count": len(output["unsupported_claims"]),
        "authority_boundary_violation": authority_violation,
        "missing_provenance_count": len(output.get("missing_provenance_fields", [])),
    }


def effect_ratio(rows: list[dict[str, object]]) -> float | None:
    effects: list[float] = []
    fixtures = sorted({row["fixture_id"] for row in rows})
    for fixture in fixtures:
        fixture_rows = [row for row in rows if row["fixture_id"] == fixture and row["elapsed_seconds"] is not None]
        control = [math.log(max(float(row["elapsed_seconds"]), 0.001)) for row in fixture_rows if row["condition"].startswith("plain-")]
        treatment = [math.log(max(float(row["elapsed_seconds"]), 0.001)) for row in fixture_rows if row["condition"].startswith("same-")]
        if not control or not treatment:
            return None
        effects.append(statistics.mean(treatment) - statistics.mean(control))
    return math.exp(statistics.mean(effects)) if effects else None


def percentile(sorted_values: list[float], proportion: float) -> float:
    position = (len(sorted_values) - 1) * proportion
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[lower]
    weight = position - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def cluster_interval(rows: list[dict[str, object]], seed_text: str) -> dict[str, object] | None:
    slots = sorted({int(row["slot"]) for row in rows})
    if len(slots) < 4:
        return None
    rng = random.Random(int(hashlib.sha256(seed_text.encode()).hexdigest(), 16))
    values: list[float] = []
    attempts = 0
    while len(values) < 10000 and attempts < 100000:
        attempts += 1
        sampled_slots = [rng.choice(slots) for _ in slots]
        sampled: list[dict[str, object]] = []
        for sample_index, slot in enumerate(sampled_slots):
            for row in rows:
                if row["slot"] == slot:
                    sampled.append({**row, "bootstrap_slot": sample_index})
        ratio = effect_ratio(sampled)
        if ratio is not None:
            values.append(ratio)
    if len(values) != 10000:
        return None
    values.sort()
    return {
        "method": "dyad-slot cluster bootstrap",
        "resamples": 10000,
        "level": 0.90,
        "lower": percentile(values, 0.05),
        "upper": percentile(values, 0.95),
    }


def condition_counts(rows: list[dict[str, object]], predicate: Callable[[dict[str, object]], bool]) -> dict[str, int]:
    return {
        "control": sum(predicate(row) for row in rows if row["condition"].startswith("plain-")),
        "treatment": sum(predicate(row) for row in rows if row["condition"].startswith("same-")),
    }


def summarize_role(role: str, rows: list[dict[str, object]], seed: str) -> dict[str, object]:
    successful = [row for row in rows if row["terminal_state"] == "success"]
    ratio = effect_ratio(successful)
    interval = cluster_interval(successful, seed + f":{role}:analysis-v0.1")
    totals = {
        "assigned": len(rows),
        "successful": len(successful),
        "terminal_states": {state: sum(row["terminal_state"] == state for row in rows) for state in sorted({row["terminal_state"] for row in rows})},
    }
    metrics = {
        "verdict_correct": condition_counts(successful, lambda row: row["score"]["verdict_correct"]),
        "expected_issue_detected": condition_counts(successful, lambda row: row["score"]["expected_issue_detected"]),
        "consequential_issue_detected": condition_counts(successful, lambda row: row["score"]["consequential_issue_detected"]),
        "unexpected_issue_count": condition_counts(successful, lambda row: row["score"]["unexpected_issue_count"] > 0),
        "unsupported_claims_identified": condition_counts(successful, lambda row: row["score"]["unsupported_claims_identified_count"] > 0),
        "authority_boundary_violations": condition_counts(successful, lambda row: row["score"]["authority_boundary_violation"]),
        "missing_provenance_fields": condition_counts(successful, lambda row: row["score"]["missing_provenance_count"] > 0),
    }
    token_fields = ["input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens"]
    usage = {
        field: condition_counts(successful, lambda row, name=field: int((row.get("usage") or {}).get(name, 0)))
        for field in token_fields
    }
    return {
        "totals": totals,
        "elapsed_seconds_treatment_to_control_ratio": ratio,
        "elapsed_seconds_cluster_interval": interval,
        "quality_counts": metrics,
        "usage_totals": usage,
    }


def main() -> None:
    design = load_json(DESIGN_PATH)
    allocation = load_json(ALLOCATION_PATH)
    sender_schema = load_json(SENDER_SCHEMA_PATH)
    receiver_schema = load_json(RECEIVER_SCHEMA_PATH)
    truth = design["ground_truth"]
    descriptors: list[dict[str, object]] = []
    rows_by_role: dict[str, list[dict[str, object]]] = {"sender": [], "receiver": []}
    for assignment in allocation["assignments"]:
        stem = f"slot-{assignment['slot']:02d}--task-{assignment['task_order']:02d}--fixture-{assignment['fixture_position']:02d}"
        for role, schema in [("sender", sender_schema), ("receiver", receiver_schema)]:
            path = RUNS_DIR / role / f"{stem}.observation.json"
            if not path.exists():
                raise ValueError(f"missing predeclared observation: {path.relative_to(REPO)}")
            observation = load_json(path)
            if observation["observation_root"] != semantic_root(observation, "observation_root"):
                raise ValueError(f"observation root drift: {path}")
            if observation["fixture_id"] != assignment["fixture_id"] or observation["condition"] != assignment["condition"]:
                raise ValueError("observation assignment drift")
            output = output_for(observation, schema)
            score = score_output(role, output, truth[assignment["fixture_id"]])
            row = {
                "observation_id": observation["observation_id"],
                "observation_root": observation["observation_root"],
                "role": role,
                "slot": assignment["slot"],
                "task_order": assignment["task_order"],
                "fixture_id": assignment["fixture_id"],
                "condition": assignment["condition"],
                "packet_root": assignment["packet_root"],
                "terminal_state": observation["terminal_state"],
                "elapsed_seconds": observation["elapsed_seconds"],
                "usage": observation["usage"],
                "output": observation["output"],
                "score": score,
            }
            rows_by_role[role].append(row)
            descriptors.append({**raw_descriptor(path), "observation_root": observation["observation_root"], "role": role, "fixture_id": observation["fixture_id"], "condition": observation["condition"]})
    index: dict[str, object] = {
        "schema": "vela.math.fc-audit.agent-observation-index.v0.1",
        "authority_effect": "none",
        "design": raw_descriptor(DESIGN_PATH),
        "allocation": raw_descriptor(ALLOCATION_PATH),
        "execution_implementation": {
            "runner": raw_descriptor(RUNNER_PATH),
            "sender_output_schema": raw_descriptor(SENDER_SCHEMA_PATH),
            "receiver_output_schema": raw_descriptor(RECEIVER_SCHEMA_PATH),
            "amendment": raw_descriptor(AMENDMENT_PATH),
            "runtime": "codex-cli 0.145.0",
            "model": "gpt-5.6-sol",
            "reasoning_effort": "high"
        },
        "observation_count": len(descriptors),
        "observations": sorted(descriptors, key=lambda item: (item["role"], item["path"])),
        "rows": rows_by_role["sender"] + rows_by_role["receiver"],
    }
    index["index_root"] = semantic_root(index, "index_root")
    INDEX_PATH.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    seed = raw_descriptor(DESIGN_PATH)["raw_sha256"]
    sender_summary = summarize_role("sender", rows_by_role["sender"], seed)
    receiver_summary = summarize_role("receiver", rows_by_role["receiver"], seed)
    complete = sender_summary["totals"]["successful"] == 30 and receiver_summary["totals"]["successful"] == 30
    h2_support = bool(
        complete
        and sender_summary["elapsed_seconds_treatment_to_control_ratio"] is not None
        and sender_summary["elapsed_seconds_treatment_to_control_ratio"] <= 0.80
        and sender_summary["elapsed_seconds_cluster_interval"] is not None
        and sender_summary["elapsed_seconds_cluster_interval"]["upper"] < 1.0
        and sender_summary["quality_counts"]["consequential_issue_detected"]["treatment"] >= sender_summary["quality_counts"]["consequential_issue_detected"]["control"]
        and sender_summary["quality_counts"]["verdict_correct"]["treatment"] >= sender_summary["quality_counts"]["verdict_correct"]["control"]
        and sender_summary["quality_counts"]["unexpected_issue_count"]["treatment"] <= sender_summary["quality_counts"]["unexpected_issue_count"]["control"]
        and sum(sender_summary["quality_counts"]["authority_boundary_violations"].values()) == 0
    )
    h5_support = bool(
        complete
        and receiver_summary["elapsed_seconds_treatment_to_control_ratio"] is not None
        and receiver_summary["elapsed_seconds_treatment_to_control_ratio"] <= 0.80
        and receiver_summary["elapsed_seconds_cluster_interval"] is not None
        and receiver_summary["elapsed_seconds_cluster_interval"]["upper"] < 1.0
        and receiver_summary["quality_counts"]["verdict_correct"]["treatment"] >= receiver_summary["quality_counts"]["verdict_correct"]["control"]
        and receiver_summary["quality_counts"]["missing_provenance_fields"]["treatment"] <= receiver_summary["quality_counts"]["missing_provenance_fields"]["control"]
        and sum(receiver_summary["quality_counts"]["authority_boundary_violations"].values()) == 0
    )
    if not complete:
        disposition = "revise"
        rationale = "One or more predeclared task contexts failed; retain missing outcomes and repair only in a separately amended run."
    elif h2_support and h5_support:
        disposition = "continue"
        rationale = "Both predeclared feasibility thresholds are satisfied for this attributed model/runtime and fixture set."
    elif (
        sender_summary["quality_counts"]["verdict_correct"]["treatment"] < sender_summary["quality_counts"]["verdict_correct"]["control"]
        or receiver_summary["quality_counts"]["verdict_correct"]["treatment"] < receiver_summary["quality_counts"]["verdict_correct"]["control"]
        or sum(sender_summary["quality_counts"]["authority_boundary_violations"].values())
        or sum(receiver_summary["quality_counts"]["authority_boundary_violations"].values())
    ):
        disposition = "retire"
        rationale = "The treatment harms retained classification or crosses an authority boundary in this bounded evaluation."
    elif (
        (sender_summary["elapsed_seconds_treatment_to_control_ratio"] or math.inf) >= 1.0
        and (receiver_summary["elapsed_seconds_treatment_to_control_ratio"] or math.inf) >= 1.0
    ):
        disposition = "retain_source_locally"
        rationale = "The rooted audit remains useful evidence, but this interface did not reduce sender or receiver time."
    else:
        disposition = "revise"
        rationale = "The treatment shows some bounded value but misses at least one predeclared efficiency, quality, or uncertainty threshold."
    results: dict[str, object] = {
        "schema": "vela.math.fc-audit.agent-evaluation-results.v0.1",
        "status": "complete" if complete else "incomplete",
        "authority_effect": "none",
        "design": raw_descriptor(DESIGN_PATH),
        "allocation": raw_descriptor(ALLOCATION_PATH),
        "observation_index": raw_descriptor(INDEX_PATH),
        "analysis_implementation": raw_descriptor(Path(__file__).resolve()),
        "model_provenance": design["reviewer_policy"],
        "independence": design["independence"],
        "sender_H2": sender_summary,
        "receiver_H5": receiver_summary,
        "hypothesis_support": {"H2": h2_support, "H5": h5_support},
        "interface_disposition": {"value": disposition, "rationale": rationale},
        "limits": [
            "These results compare two input interfaces for one model/runtime on five fixtures; they do not rank humans and agents.",
            "Fresh task contexts share a provider, model family, runner, operator account, and ground-truth package.",
            "Wall-clock latency includes provider and network variability and is not pure reasoning time.",
            "The output field unsupported_claims records claims the reviewer identified as unsupported; it does not measure unsupported claims authored by the reviewer. Authored unsupported-claim scoring requires a separate attributed adjudication.",
            "The frozen human study remains uncollected and separate.",
            "No result is a Vela Verification, Decision, acceptance, or Standing."
        ],
    }
    results["results_root"] = semantic_root(results, "results_root")
    RESULTS_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
