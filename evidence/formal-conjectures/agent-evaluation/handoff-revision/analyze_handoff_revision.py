#!/usr/bin/env python3
"""Validate and analyze the paired handoff revision."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import random
import statistics
from typing import Any

import jsonschema


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
DESIGN = HERE / "handoff-revision-design.v0.2.json"
ALLOCATION = HERE / "handoff-revision-allocation.v0.2.json"
SCHEMA = HERE / "receiver-output.schema.v0.2.json"
RUNNER = HERE / "run_handoff_revision.py"
RUNS = HERE / "runs"
INDEX = HERE / "handoff-revision-observation-index.v0.2.json"
RESULTS = HERE / "handoff-revision-results.v0.2.json"
TRUTH = {
    "clean-source-faithful-min-modulus-4829": ("clean", set()),
    "conditional-erdos-427-4884": ("inconclusive", {"conditional_proof_dependency"}),
    "fidelity-erdos-887-1237": ("needs_revision", {"answer_slot_scope"}),
    "vacuity-erdos-80-4830": ("needs_revision", {"vacuous_hypothesis"}),
    "unavailable-rupert-3959": ("unavailable", {"exact_artifact_identity_unavailable"}),
}


def load(path: Path) -> Any:
    return json.loads(path.read_text())


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def root(value: dict[str, Any], field: str) -> str:
    unrooted = dict(value)
    unrooted.pop(field, None)
    return digest(canonical(unrooted))


def descriptor(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {"path": path.relative_to(REPO).as_posix(), "size": len(data), "raw_sha256": digest(data)}


def stem(assignment: dict[str, Any]) -> str:
    pair = assignment["pair_id"].replace("agent-eval-handoff-", "").replace("::handoff-revision-v0.2", "")
    return f"{pair}--{assignment['condition']}"


def paired_ratio(rows: list[dict[str, Any]], selected: list[str] | None = None) -> float:
    pairs = selected or sorted({row["pair_id"] for row in rows})
    logs: list[float] = []
    for pair in pairs:
        pair_rows = [row for row in rows if row["pair_id"] == pair and row["terminal_state"] == "success"]
        by_condition = {row["condition"]: row for row in pair_rows}
        if set(by_condition) != {"legacy_full_audit_handoff", "compact_attributed_handoff"}:
            raise ValueError("incomplete pair")
        logs.append(math.log(max(by_condition["compact_attributed_handoff"]["elapsed_seconds"], 0.001)) - math.log(max(by_condition["legacy_full_audit_handoff"]["elapsed_seconds"], 0.001)))
    return math.exp(statistics.mean(logs))


def interval(rows: list[dict[str, Any]], seed: str) -> dict[str, Any]:
    pairs = sorted({row["pair_id"] for row in rows})
    rng = random.Random(int(hashlib.sha256(seed.encode()).hexdigest(), 16))
    values = sorted(paired_ratio(rows, [rng.choice(pairs) for _ in pairs]) for _ in range(10000))
    def percentile(p: float) -> float:
        position = (len(values) - 1) * p
        low, high = math.floor(position), math.ceil(position)
        return values[low] if low == high else values[low] * (high - position) + values[high] * (position - low)
    return {"method": "sender-pair bootstrap", "resamples": 10000, "level": 0.9, "lower": percentile(0.05), "upper": percentile(0.95)}


def counts(rows: list[dict[str, Any]], field: str) -> dict[str, int]:
    return {condition: sum(bool(row["score"][field]) for row in rows if row["condition"] == condition) for condition in ["legacy_full_audit_handoff", "compact_attributed_handoff"]}


def main() -> None:
    allocation = load(ALLOCATION)
    schema = load(SCHEMA)
    rows: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    for assignment in allocation["assignments"]:
        observation_path = RUNS / f"{stem(assignment)}.observation.json"
        observation = load(observation_path)
        if observation["observation_root"] != root(observation, "observation_root"):
            raise ValueError("observation root drift")
        output = None
        if observation["output"]:
            output_path = REPO / observation["output"]["path"]
            data = output_path.read_bytes()
            if len(data) != observation["output"]["size"] or digest(data) != observation["output"]["raw_sha256"]:
                raise ValueError("output drift")
            output = json.loads(data)
            jsonschema.Draft202012Validator(schema).validate(output)
        expected_verdict, expected_issues = TRUTH[assignment["fixture_id"]]
        actual_issues = set(output["retained_issue_codes"]) if output else set()
        bindings = output["provenance_bindings"] if output else {}
        expected_bindings = {
            "sender_output_sha256": assignment["sender_output"]["raw_sha256"],
            "original_packet_root": assignment["packet_root"],
            "authority_effect": "none",
        }
        score = {
            "verdict_correct": bool(output and output["retained_verdict"] == expected_verdict),
            "expected_issue_detected": bool(output and expected_issues.issubset(actual_issues)),
            "unexpected_issue": bool(output and actual_issues - expected_issues),
            "provenance_complete": bool(output and all(bindings.get(key) == value for key, value in expected_bindings.items()) and bindings.get("source_commit") and bindings.get("source_path") and bindings.get("source_raw_sha256") and bindings.get("evidence_locators_retained") is True),
            "authority_violation": bool(output and (output["authority_effect"] != "none" or bindings.get("authority_effect") != "none" or not any("standing" in item.lower() or "accept" in item.lower() for item in output["does_not_establish"]))),
        }
        rows.append({
            "pair_id": assignment["pair_id"],
            "fixture_id": assignment["fixture_id"],
            "condition": assignment["condition"],
            "terminal_state": observation["terminal_state"],
            "elapsed_seconds": observation["elapsed_seconds"],
            "usage": observation["usage"],
            "score": score,
            "observation_root": observation["observation_root"],
        })
        observations.append({**descriptor(observation_path), "observation_root": observation["observation_root"]})
    complete = len(rows) == 30 and all(row["terminal_state"] == "success" for row in rows)
    ratio = paired_ratio(rows) if complete else None
    uncertainty = interval(rows, descriptor(DESIGN)["raw_sha256"]) if complete else None
    quality = {field: counts(rows, field) for field in ["verdict_correct", "expected_issue_detected", "unexpected_issue", "provenance_complete", "authority_violation"]}
    usage_fields = ["input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens"]
    usage = {field: {condition: sum(int((row["usage"] or {}).get(field, 0)) for row in rows if row["condition"] == condition) for condition in ["legacy_full_audit_handoff", "compact_attributed_handoff"]} for field in usage_fields}
    compact, legacy = "compact_attributed_handoff", "legacy_full_audit_handoff"
    support = bool(complete and ratio <= 0.8 and uncertainty["upper"] < 1.0 and quality["verdict_correct"][compact] >= quality["verdict_correct"][legacy] and quality["expected_issue_detected"][compact] >= quality["expected_issue_detected"][legacy] and quality["unexpected_issue"][compact] <= quality["unexpected_issue"][legacy] and quality["provenance_complete"][compact] >= quality["provenance_complete"][legacy] and sum(quality["authority_violation"].values()) == 0)
    if support:
        disposition, rationale = "continue", "The compact handoff meets the frozen efficiency, quality, provenance, and authority thresholds."
    elif complete and quality["verdict_correct"][compact] < quality["verdict_correct"][legacy]:
        disposition, rationale = "retire", "The compact handoff reduces retained verdict accuracy."
    elif complete and ratio is not None and ratio >= 1.0:
        disposition, rationale = "retain_source_locally", "The compact handoff does not reduce paired receiver time."
    else:
        disposition, rationale = "revise", "The compact handoff misses at least one frozen threshold."
    index: dict[str, Any] = {"schema": "vela.math.fc-audit.handoff-revision-observation-index.v0.2", "authority_effect": "none", "design": descriptor(DESIGN), "allocation": descriptor(ALLOCATION), "observation_count": len(observations), "observations": sorted(observations, key=lambda item: item["path"]), "rows": rows}
    index["index_root"] = root(index, "index_root")
    INDEX.write_text(json.dumps(index, indent=2) + "\n")
    results: dict[str, Any] = {
        "schema": "vela.math.fc-audit.handoff-revision-results.v0.2",
        "status": "complete" if complete else "incomplete",
        "authority_effect": "none",
        "design": descriptor(DESIGN),
        "allocation": descriptor(ALLOCATION),
        "observation_index": descriptor(INDEX),
        "analysis_implementation": descriptor(Path(__file__).resolve()),
        "model_provenance": load(DESIGN)["reviewer_policy"],
        "paired_elapsed_compact_to_legacy_ratio": ratio,
        "paired_elapsed_interval": uncertainty,
        "quality_counts": quality,
        "usage_totals": usage,
        "hypothesis_supported": support,
        "interface_disposition": {"value": disposition, "rationale": rationale},
        "limits": load(DESIGN)["nonclaims"],
    }
    results["results_root"] = root(results, "results_root")
    RESULTS.write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
