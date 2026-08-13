#!/usr/bin/env python3
"""Build compact handoffs and the paired receiver allocation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
REPO = HERE.parents[3]
DESIGN = HERE / "handoff-revision-design.v0.2.json"
SOURCE_ALLOCATION = PARENT / "agent-allocation.v0.1.json"
RUNS = PARENT / "runs" / "sender"
HANDOFFS = HERE / "compact-handoffs"
SET_PATH = HERE / "compact-handoff-set.v0.2.json"
ALLOCATION_PATH = HERE / "handoff-revision-allocation.v0.2.json"


def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate key: {key}")
        value[key] = item
    return value


def load(path: Path) -> Any:
    return json.loads(path.read_text(), object_pairs_hook=reject_duplicates)


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def root(value: dict[str, Any], field: str) -> str:
    unrooted = dict(value)
    unrooted.pop(field, None)
    return "sha256:" + hashlib.sha256(canonical(unrooted)).hexdigest()


def descriptor(path: Path, root_field: str | None = None) -> dict[str, Any]:
    data = path.read_bytes()
    value: dict[str, Any] = {
        "path": path.relative_to(REPO).as_posix(),
        "size": len(data),
        "raw_sha256": "sha256:" + hashlib.sha256(data).hexdigest(),
    }
    if root_field:
        parsed = load(path)
        value[root_field] = parsed[root_field]
    return value


def stem(assignment: dict[str, Any]) -> str:
    return f"slot-{assignment['slot']:02d}--task-{assignment['task_order']:02d}--fixture-{assignment['fixture_position']:02d}"


def main() -> None:
    design = load(DESIGN)
    source = load(SOURCE_ALLOCATION)
    HANDOFFS.mkdir(exist_ok=True)
    expected_paths: set[Path] = set()
    handoffs: list[dict[str, Any]] = []
    assignments: list[dict[str, Any]] = []
    for assignment in source["assignments"]:
        if assignment["condition"] != "same-inputs-plus-fc-pr-audit":
            continue
        name = stem(assignment)
        observation_path = RUNS / f"{name}.observation.json"
        observation = load(observation_path)
        if observation["terminal_state"] != "success":
            raise ValueError("source sender did not complete")
        output_path = REPO / observation["output"]["path"]
        output = load(output_path)
        bundle_path = REPO / assignment["bundle"]["path"]
        bundle = load(bundle_path)
        source_identity = bundle["public_source"]
        audit_descriptors = bundle["condition_packet"]["treatment_evidence"]
        packet: dict[str, Any] = {
            "schema": "vela.math.fc-audit.compact-attributed-handoff.v0.2",
            "authority_effect": "none",
            "handoff_id": assignment["handoff_id"] + "::compact-v0.2",
            "fixture_id": assignment["fixture_id"],
            "original_packet_root": assignment["packet_root"],
            "source": {
                "repository": source_identity["repository"],
                "commit": source_identity["commit"],
                "path": source_identity["source_path"],
                "git_blob_sha1": source_identity["git_blob_sha1"],
                "raw_sha256": source_identity["raw_sha256"],
                "size": source_identity["size"],
            },
            "sender": {
                "actor_class": "agent",
                "task_context_id": assignment["sender_task_context_id"],
                "output": descriptor(output_path),
                "verdict": output["verdict"],
                "issue_codes": output["issue_codes"],
                "mechanical_status": output["mechanical_status"],
                "source_fidelity": output["source_fidelity"],
                "artifact_availability": output["artifact_availability"],
                "community_status": output["community_status"],
                "evidence_locators": output["evidence_locators"],
                "witness": output["witness"],
                "unsupported_claims": output["unsupported_claims"],
                "next_action": output["next_obligation"],
                "confidence": output["confidence"],
            },
            "audit_records": audit_descriptors,
            "authority": {
                "effect": "none",
                "does_not_establish": output["does_not_establish"],
            },
            "receiver_instruction": "Confirm or correct the retained verdict and issue codes, bind the exact provenance fields, state what remains unsupported, and give the next action. Request raw source or audit bytes by locator only if the compact packet cannot support that continuation.",
            "omitted_payloads": [
                "embedded source bytes",
                "embedded audit core and observation bytes",
                "GitHub API response bodies",
            ],
        }
        packet["handoff_root"] = root(packet, "handoff_root")
        handoff_path = HANDOFFS / f"{name}.json"
        expected_paths.add(handoff_path)
        handoff_path.write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n")
        handoff_descriptor = descriptor(handoff_path, "handoff_root")
        handoffs.append({"source_handoff_id": assignment["handoff_id"], **handoff_descriptor})
        for condition in ["legacy_full_audit_handoff", "compact_attributed_handoff"]:
            assignments.append({
                "pair_id": assignment["handoff_id"] + "::handoff-revision-v0.2",
                "source_handoff_id": assignment["handoff_id"],
                "source_slot": assignment["slot"],
                "source_task_order": assignment["task_order"],
                "fixture_id": assignment["fixture_id"],
                "condition": condition,
                "packet_root": assignment["packet_root"],
                "bundle": assignment["bundle"],
                "sender_observation": descriptor(observation_path, "observation_root"),
                "sender_output": descriptor(output_path),
                "compact_handoff": handoff_descriptor,
                "receiver_task_context_id": f"agent:codex-eval-receiver-v02-{condition}-s{assignment['slot']:02d}-{assignment['fixture_id']}",
            })
    actual_paths = set(HANDOFFS.glob("*.json"))
    if actual_paths != expected_paths:
        raise ValueError("compact handoff inventory drift")
    if len(handoffs) != 15 or len(assignments) != 30:
        raise ValueError("unexpected sample size")
    handoff_set: dict[str, Any] = {
        "schema": "vela.math.fc-audit.compact-handoff-set.v0.2",
        "authority_effect": "none",
        "design": descriptor(DESIGN),
        "handoff_count": len(handoffs),
        "handoffs": sorted(handoffs, key=lambda item: item["source_handoff_id"]),
    }
    handoff_set["handoff_set_root"] = root(handoff_set, "handoff_set_root")
    SET_PATH.write_text(json.dumps(handoff_set, indent=2) + "\n")
    allocation: dict[str, Any] = {
        "schema": "vela.math.fc-audit.handoff-revision-allocation.v0.2",
        "authority_effect": "none",
        "design": descriptor(DESIGN),
        "handoff_set": descriptor(SET_PATH, "handoff_set_root"),
        "assignment_count": len(assignments),
        "assignments": sorted(assignments, key=lambda item: (item["pair_id"], item["condition"])),
    }
    allocation["allocation_root"] = root(allocation, "allocation_root")
    ALLOCATION_PATH.write_text(json.dumps(allocation, indent=2) + "\n")


if __name__ == "__main__":
    main()
