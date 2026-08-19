#!/usr/bin/env python3
"""Validate and render the frozen, non-authoritative comparison."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent
INPUTS = (
    "audit.json",
    "candidates.json",
    "comparison.json",
    "rubric.json",
    "vela-baseline.json",
)
SYSTEMS = ("far_git_pipeline", "probxiv_public_registry", "vela_math_repository")
DIMENSIONS = (
    "discovery_and_allocation",
    "source_statement_fidelity",
    "problem_result_scope",
    "open_status_and_observation_time",
    "duplicate_or_known_result_detection",
    "evidence_axes",
    "performer_verifier_authority_separation",
    "correction_and_replay",
    "provider_loss_and_cold_successor",
)
CANDIDATES = (
    "far-erdos-635-known",
    "far-gap-p-many-one-reviewed",
    "probxiv-ramsey-machine-reviewed",
    "probxiv-erdos-7-retracted",
    "probxiv-directed-3-torus-formal-check",
)
FINDINGS = {"full", "partial", "absent", "not_evaluated"}
BANNED_KEYS = {"body", "page_text", "paper_text", "solution_text", "proof_text"}
BANNED_SCORING_KEYS = {"score", "scores", "winner", "ranking"}


class InvalidComparison(ValueError):
    pass


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def sha256(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def load_inputs(base: Path = BASE) -> dict[str, Any]:
    return {name: json.loads((base / name).read_text()) for name in INPUTS}


def walk_keys(value: Any) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in BANNED_KEYS:
                raise InvalidComparison(f"external body field forbidden: {key}")
            if key in BANNED_SCORING_KEYS:
                raise InvalidComparison(f"aggregate scoring field forbidden: {key}")
            walk_keys(item)
    elif isinstance(value, list):
        for item in value:
            walk_keys(item)


def enforce_rights_shape(value: Any, path: str = "external") -> None:
    if isinstance(value, str):
        if len(value) > 512:
            raise InvalidComparison(f"oversized retained external text: {path}")
    elif isinstance(value, dict):
        for key, item in value.items():
            enforce_rights_shape(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            enforce_rights_shape(item, f"{path}[{index}]")


def validate_locator(locator: str, base: Path) -> None:
    if locator.startswith("https://"):
        return
    if not (base / locator).resolve().exists():
        raise InvalidComparison(f"missing local evidence locator: {locator}")


def verify_files(base: Path = BASE) -> dict[str, Any]:
    values = load_inputs(base)
    walk_keys(values)

    audit = values["audit.json"]
    candidates = values["candidates.json"]
    comparison = values["comparison.json"]
    rubric = values["rubric.json"]
    vela_baseline = values["vela-baseline.json"]
    if audit.get("schema") != "vela-math.far-probxiv-audit.v1":
        raise InvalidComparison("audit schema")
    if candidates.get("schema") != "vela-math.far-probxiv-candidate-set.v1":
        raise InvalidComparison("candidate schema")
    if comparison.get("schema") != "vela-math.far-probxiv-comparison.v1":
        raise InvalidComparison("comparison schema")
    if rubric.get("schema") != "vela-math.far-probxiv-rubric.v1":
        raise InvalidComparison("rubric schema")
    if vela_baseline.get("schema") != "vela-math.result-boundary-baseline.v1":
        raise InvalidComparison("Vela baseline schema")
    for value in values.values():
        if value.get("authority_effect") != "none":
            raise InvalidComparison("all evaluation inputs must have authority_effect none")
    enforce_rights_shape(audit)
    enforce_rights_shape(candidates)
    if len(canonical(audit)) > 16_384 or len(canonical(candidates)) > 32_768:
        raise InvalidComparison("oversized retained external record set")

    candidate_rows = candidates.get("candidates")
    if not isinstance(candidate_rows, list):
        raise InvalidComparison("candidate rows")
    if tuple(row.get("id") for row in candidate_rows) != CANDIDATES:
        raise InvalidComparison("candidate identity or order drift")
    for row in candidate_rows:
        if len(canonical(row)) > 4_096:
            raise InvalidComparison(f"oversized retained candidate record: {row.get('id')}")
        mapping = row.get("vela_mapping")
        if not isinstance(mapping, dict) or mapping.get("authority_effect") != "none":
            raise InvalidComparison(f"candidate authority drift: {row.get('id')}")
        if mapping.get("decision_event_standing") not in {
            "absent",
            "ProbXiv retracted status is not a Vela Decision or Standing",
        }:
            raise InvalidComparison(f"external authority implication: {row.get('id')}")
        validate_locator(row["occurrence"], base)

    if tuple(comparison.get("dimensions", ())) != DIMENSIONS:
        raise InvalidComparison("dimension contract drift")
    systems = comparison.get("systems")
    if not isinstance(systems, dict) or tuple(systems.keys()) != SYSTEMS:
        raise InvalidComparison("system contract drift")
    for system, rows in systems.items():
        if tuple(row.get("dimension") for row in rows) != DIMENSIONS:
            raise InvalidComparison(f"dimension coverage drift: {system}")
        for row in rows:
            if row.get("finding") not in FINDINGS:
                raise InvalidComparison(f"finding vocabulary: {system}")
            if row.get("basis") not in {"observed", "inferred"}:
                raise InvalidComparison(f"basis vocabulary: {system}")
            evidence = row.get("evidence")
            if not isinstance(evidence, list) or not evidence:
                raise InvalidComparison(f"evidence missing: {system}/{row.get('dimension')}")
            for locator in evidence:
                validate_locator(locator, base)

    rubric_dimensions = rubric.get("dimensions")
    if not isinstance(rubric_dimensions, list) or tuple(row.get("id") for row in rubric_dimensions) != DIMENSIONS:
        raise InvalidComparison("rubric dimension drift")
    for index, rubric_row in enumerate(rubric_dimensions):
        criteria = rubric_row.get("criteria")
        if not isinstance(criteria, list) or len(criteria) != 2:
            raise InvalidComparison(f"rubric criteria drift: {rubric_row.get('id')}")
        criterion_ids = tuple(item.get("id") for item in criteria)
        if len(set(criterion_ids)) != 2 or any(not item.get("description") for item in criteria):
            raise InvalidComparison(f"rubric criteria invalid: {rubric_row.get('id')}")
        assessments = rubric_row.get("assessments")
        if not isinstance(assessments, dict) or tuple(assessments.keys()) != SYSTEMS:
            raise InvalidComparison(f"rubric system drift: {rubric_row.get('id')}")
        for system in SYSTEMS:
            values_for_system = assessments[system]
            if tuple(values_for_system.keys()) != criterion_ids or any(
                not isinstance(value, bool) for value in values_for_system.values()
            ):
                raise InvalidComparison(f"rubric assessment drift: {rubric_row.get('id')}/{system}")
            count = sum(values_for_system.values())
            derived = "absent" if count == 0 else "full" if count == len(criteria) else "partial"
            if comparison["systems"][system][index]["finding"] != derived:
                raise InvalidComparison(f"finding not derived from rubric: {rubric_row.get('id')}/{system}")

    replay = vela_baseline.get("replay", {})
    reader = vela_baseline.get("reader", {})
    if reader.get("version") != "0.977.3" or reader.get("sha256") != "3a1173918bdcb887155bab681411bf5e9ff64d925fe1b50369ac37ab020b94ad":
        raise InvalidComparison("Vela reader identity drift")
    expected_review_baseline = vela_baseline.get("correction_transition", {}).get("review_event", {})
    if expected_review_baseline.get("proposal_kind") != "claim.revise":
        raise InvalidComparison("Vela review proposal kind baseline drift")
    if expected_review_baseline.get("proposal_id") != "vpr_b5ca521d2a892eee":
        raise InvalidComparison("Vela review proposal baseline drift")
    math_source = next(source for source in audit["sources"] if source["id"] == "vela-math-baseline")
    if replay.get("git_commit") != math_source.get("version") or replay.get("git_tree") != math_source.get("tree"):
        raise InvalidComparison("Vela replay source drift")
    if replay.get("repository_root") != "sha256:a956b84c437202e5a02cc9e036a621bd14a302b34a75758115730bdbb77c52a4":
        raise InvalidComparison("Vela replay root drift")
    if replay.get("counts", {}).get("accepted_claims") != 3 or replay.get("counts", {}).get("pending_claims") != 0:
        raise InvalidComparison("Vela replay count drift")
    for key in ("review_event", "standing_event"):
        expected = vela_baseline["correction_transition"][key]
        event_path = (base / expected["path"]).resolve()
        event = json.loads(event_path.read_text())
        content = event.get("content", {})
        if event.get("id") != expected["id"] or content.get("kind") != expected["kind"]:
            raise InvalidComparison(f"Vela correction event drift: {key}")
        if content.get("timestamp") != expected["timestamp"]:
            raise InvalidComparison(f"Vela correction time drift: {key}")
    review = json.loads(
        (base / vela_baseline["correction_transition"]["review_event"]["path"]).resolve().read_text()
    )["content"]
    expected_review = expected_review_baseline
    if review["target"]["id"] != expected_review["proposal_id"]:
        raise InvalidComparison("Vela review proposal drift")
    if review["payload"]["proposal_kind"] != expected_review["proposal_kind"]:
        raise InvalidComparison("Vela review proposal kind drift")
    standing = json.loads(
        (base / vela_baseline["correction_transition"]["standing_event"]["path"]).resolve().read_text()
    )["content"]
    expected_standing = vela_baseline["correction_transition"]["standing_event"]
    if standing["target"]["id"] != expected_standing["predecessor_claim_id"]:
        raise InvalidComparison("Vela correction predecessor drift")
    for field in ("claim_id", "repository_before", "repository_after"):
        expected_field = "successor_claim_id" if field == "claim_id" else field
        if standing["payload"][field] != expected_standing[expected_field]:
            raise InvalidComparison(f"Vela correction payload drift: {field}")

    roots = {name: sha256(canonical(values[name])) for name in INPUTS}
    roots["implementation"] = sha256(Path(__file__).read_bytes())
    roots["evaluation_root"] = sha256(canonical({name: values[name] for name in INPUTS}))
    return {"values": values, "roots": roots}


def build_report(base: Path = BASE) -> dict[str, Any]:
    verified = verify_files(base)
    values = verified["values"]
    comparison = values["comparison.json"]
    counts = {
        system: dict(sorted(Counter(row["finding"] for row in rows).items()))
        for system, rows in comparison["systems"].items()
    }
    matrix = []
    for index, dimension in enumerate(DIMENSIONS):
        matrix.append(
            {
                "dimension": dimension,
                "findings": {
                    system: comparison["systems"][system][index]["finding"] for system in SYSTEMS
                },
            }
        )
    return {
        "schema": "vela-math.far-probxiv-report.v1",
        "authority_effect": "none",
        "candidate_count": len(CANDIDATES),
        "dimension_count": len(DIMENSIONS),
        "input_roots": verified["roots"],
        "finding_counts": counts,
        "matrix": matrix,
        "thesis": comparison["thesis"],
        "limitations": [
            "This is an internal primary-source audit and deterministic aggregation, not an independent evaluation.",
            "Findings compare public contracts and current artifacts, not mathematical correctness or research productivity.",
            "No aggregate score or winner is computed because the systems own different product boundaries.",
            "No FAR or ProbXiv candidate has a Vela Submission, Verification, Decision, Event, or Standing here."
        ]
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("verify")
    report = subparsers.add_parser("report")
    report.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.command == "verify":
        verified = verify_files()
        print(f"candidate-set: {verified['roots']['candidates.json']}")
        print(f"evaluation: {verified['roots']['evaluation_root']}")
        print(f"comparison: ok ({len(CANDIDATES)} candidates, {len(DIMENSIONS)} dimensions)")
        return

    output = build_report()
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(f"report: {sha256(canonical(output))}")


if __name__ == "__main__":
    main()
