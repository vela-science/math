#!/usr/bin/env python3
"""Build matched, self-contained, rooted inputs for the agent evaluation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PACKETS_PATH = REPO / "evidence/formal-conjectures/audit-pilot/condition-packet-set.v0.1.json"
DESIGN_PATH = HERE / "agent-evaluation-design.v0.1.json"
SOURCE_MANIFEST_PATH = HERE / "public-source-manifest.v0.1.json"
BUNDLE_DIR = HERE / "condition-bundles"
BUNDLE_SET_PATH = HERE / "condition-bundle-set.v0.1.json"
ALLOCATION_PATH = HERE / "agent-allocation.v0.1.json"


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


def inline_json(descriptor: dict[str, object]) -> dict[str, object]:
    path = REPO / descriptor["path"]
    data = path.read_bytes()
    if len(data) != descriptor["size"]:
        raise ValueError(f"size drift for {descriptor['path']}")
    if "sha256:" + hashlib.sha256(data).hexdigest() != descriptor["raw_sha256"]:
        raise ValueError(f"root drift for {descriptor['path']}")
    return {**descriptor, "content": load_json(path)}


def main() -> None:
    design = load_json(DESIGN_PATH)
    packets = load_json(PACKETS_PATH)
    source_manifest = load_json(SOURCE_MANIFEST_PATH)
    if source_manifest["manifest_root"] != semantic_root(source_manifest, "manifest_root"):
        raise ValueError("source manifest root drift")
    source_by_fixture = {item["fixture_id"]: item for item in source_manifest["artifacts"]}
    BUNDLE_DIR.mkdir(parents=True, exist_ok=True)
    descriptors: list[dict[str, object]] = []
    expected_names: set[str] = set()
    for packet in packets["packets"]:
        if packet["packet_root"] != semantic_root(packet, "packet_root"):
            raise ValueError(f"condition packet root drift: {packet['packet_id']}")
        source = source_by_fixture.get(packet["fixture_id"])
        if source is None:
            raise ValueError(f"missing public source for {packet['fixture_id']}")
        source_path = REPO / source["local_path"]
        source_data = source_path.read_bytes()
        if len(source_data) != source["size"]:
            raise ValueError("public source size drift")
        if "sha256:" + hashlib.sha256(source_data).hexdigest() != source["raw_sha256"]:
            raise ValueError("public source root drift")
        bundle: dict[str, object] = {
            "schema": "vela.math.fc-audit.agent-condition-bundle.v0.1",
            "authority_effect": "none",
            "fixture_id": packet["fixture_id"],
            "condition": packet["condition"],
            "packet_root": packet["packet_root"],
            "condition_packet": packet,
            "public_source": {
                **source,
                "content_utf8": source_data.decode("utf-8"),
            },
            "shared_evidence": [inline_json(item) for item in packet["shared_evidence"]],
            "treatment_evidence": [inline_json(item) for item in packet["treatment_evidence"]],
            "access_limits": [
                "Use only this bundle.",
                "Do not use network, repository, browser, memory, or private operator context.",
                "Do not infer acceptance or Standing from a review, check, merge, or audit disposition."
            ],
        }
        bundle["bundle_root"] = semantic_root(bundle, "bundle_root")
        name = packet["packet_id"].replace("::", "--") + ".json"
        expected_names.add(name)
        output_path = BUNDLE_DIR / name
        output_path.write_text(json.dumps(bundle, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        descriptors.append({**raw_descriptor(output_path), "fixture_id": packet["fixture_id"], "condition": packet["condition"], "packet_root": packet["packet_root"], "bundle_root": bundle["bundle_root"]})
    for path in BUNDLE_DIR.glob("*.json"):
        if path.name not in expected_names:
            raise ValueError(f"stale condition bundle: {path.name}")
    bundle_set: dict[str, object] = {
        "schema": "vela.math.fc-audit.agent-condition-bundle-set.v0.1",
        "authority_effect": "none",
        "design": raw_descriptor(DESIGN_PATH),
        "source_manifest": raw_descriptor(SOURCE_MANIFEST_PATH),
        "condition_packet_set": raw_descriptor(PACKETS_PATH),
        "bundle_count": len(descriptors),
        "bundles": sorted(descriptors, key=lambda item: (item["fixture_id"], item["condition"])),
    }
    bundle_set["bundle_set_root"] = semantic_root(bundle_set, "bundle_set_root")
    BUNDLE_SET_PATH.write_text(json.dumps(bundle_set, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    human_design = load_json(REPO / "evidence/formal-conjectures/audit-pilot/precollection-design.v0.1.json")
    fixture_ids = human_design["fixture_by_condition_allocation"]["fixture_ids"]
    by_key = {(item["fixture_id"], item["condition"]): item for item in descriptors}
    condition_names = human_design["counterbalance_schedule"]["condition_key"]
    assignments: list[dict[str, object]] = []
    for slot_record in human_design["counterbalance_schedule"]["slots"]:
        slot = slot_record["slot"]
        order_by_position = {fixture_position: order for order, fixture_position in enumerate(slot_record["task_order"], start=1)}
        for fixture_position, fixture_id in enumerate(fixture_ids, start=1):
            condition = condition_names[slot_record["conditions"][fixture_position - 1]]
            descriptor = by_key[(fixture_id, condition)]
            slug = fixture_id.replace("_", "-")
            assignments.append(
                {
                    "slot": slot,
                    "fixture_position": fixture_position,
                    "task_order": order_by_position[fixture_position],
                    "fixture_id": fixture_id,
                    "condition": condition,
                    "packet_root": descriptor["packet_root"],
                    "bundle": {
                        "path": descriptor["path"],
                        "raw_sha256": descriptor["raw_sha256"],
                        "size": descriptor["size"],
                        "bundle_root": descriptor["bundle_root"],
                    },
                    "handoff_id": f"agent-eval-handoff-s{slot:02d}-{fixture_position:02d}",
                    "sender_task_context_id": f"agent:codex-eval-sender-s{slot:02d}-{slug}",
                    "receiver_task_context_id": f"agent:codex-eval-receiver-s{slot:02d}-{slug}",
                }
            )
    allocation: dict[str, object] = {
        "schema": "vela.math.fc-audit.agent-allocation.v0.1",
        "authority_effect": "none",
        "design": raw_descriptor(DESIGN_PATH),
        "bundle_set": raw_descriptor(BUNDLE_SET_PATH),
        "assignment_count": len(assignments),
        "assignments": sorted(assignments, key=lambda item: (item["slot"], item["task_order"])),
        "rule": "All assignments are frozen before model execution; failures are retained and no task is retried or replaced based on outcome."
    }
    allocation["allocation_root"] = semantic_root(allocation, "allocation_root")
    ALLOCATION_PATH.write_text(json.dumps(allocation, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
