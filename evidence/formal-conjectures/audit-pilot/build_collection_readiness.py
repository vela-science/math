#!/usr/bin/env python3
"""Build the frozen, participant-free EVAL-01 collection materials."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SELECTION = HERE / "phase-0-fixture-selection.v0.1.json"
DESIGN = HERE / "precollection-design.v0.1.json"
METHOD = REPO / "methods/formal-conjectures/audit-baseline.v0.1.json"
MATERIALS = HERE / "collection-materials.v0.1.json"
PACKETS = HERE / "condition-packet-set.v0.1.json"
READINESS = HERE / "collection-readiness.v0.1.json"
AUDIT_FIXTURES = (
    REPO
    / "evidence/formal-conjectures/source-adapter/retained-source/audit/pr-audit-v1/fixtures"
)


class CollectionBuildError(ValueError):
    pass


def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise CollectionBuildError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
    if not isinstance(value, dict):
        raise CollectionBuildError(f"{path.relative_to(REPO)} must contain one object")
    return value


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def framed(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def semantic_root(value: dict[str, object], field: str) -> str:
    payload = copy.deepcopy(value)
    payload.pop(field, None)
    return "sha256:" + hashlib.sha256(canonical(payload)).hexdigest()


def descriptor(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    return {
        "path": path.relative_to(REPO).as_posix(),
        "raw_sha256": "sha256:" + hashlib.sha256(raw).hexdigest(),
        "size": len(raw),
    }


def descriptor_for_bytes(path: Path, raw: bytes, root: str, schema: str) -> dict[str, object]:
    return {
        "path": path.relative_to(REPO).as_posix(),
        "raw_sha256": "sha256:" + hashlib.sha256(raw).hexdigest(),
        "root": root,
        "schema": schema,
        "size": len(raw),
    }


def source_paths(fixture: dict[str, object]) -> list[Path]:
    number = fixture["pull_request"]["number"]
    candidates = [
        HERE / f"source-snapshots/github-pr-{number}.json",
        HERE / f"source-snapshots/github-pr-{number}-files-observation.json",
        HERE / f"source-snapshots/github-pr-{number}-reviews.json",
        HERE / f"source-snapshots/github-pr-{number}-check-observation.json",
    ]
    if fixture["id"] == "vacuity-erdos-80-4830":
        candidates.extend(
            [
                HERE / "source-snapshots/github-pr-4877.json",
                HERE / "source-snapshots/github-pr-4877-reviews.json",
            ]
        )
    unique = {path.resolve(): path for path in candidates if path.exists()}
    return sorted(unique.values(), key=lambda path: path.relative_to(REPO).as_posix())


def build_materials(design: dict[str, object], method: dict[str, object]) -> dict[str, object]:
    materials: dict[str, object] = {
        "schema": "vela.math.fc-audit.collection-materials.v0.1",
        "status": "materials_frozen_no_participants_contacted",
        "authority_effect": "none",
        "design": descriptor(DESIGN),
        "method": descriptor(METHOD),
        "consent": {
            "title": "Formal Conjectures audit handoff study",
            "purpose": "Measure whether one retained audit record changes the time and accuracy of reviewing the same five public Formal Conjectures pull requests.",
            "participation": "Participation is voluntary. You may skip a task or stop without giving a reason. Stopping has no effect on repository access, contributor status, or scientific authority.",
            "tasks": "You will inspect public Lean source, public review evidence, and one rooted condition packet. A paired receiver will continue from the packet without private sender context.",
            "time_caps": {
                "sender_review_seconds": 5400,
                "receiver_continuation_and_reproduction_seconds": 3600,
            },
            "data_collected": [
                "a study-random pseudonym and declared Lean or Formal Conjectures experience",
                "task timestamps, active and wait durations, terminal states, findings, commands, and public artifact roots",
                "handoff linkage and whether the receiver used only the condition packet",
            ],
            "public_release": "The public dataset will contain redacted pseudonymous task fields and authorized evidence excerpts. It will exclude names, contact details, account identifiers, credentials, private messages, and the re-identification key.",
            "private_custody": "The study custodian will keep consent receipts, contact details, and any re-identification key encrypted outside Git with access limited to the evaluation owner.",
            "retention": "The custodian will delete private raw material and the re-identification key no later than 180 days after the last enrolled session. A participant may request earlier withdrawal before the redacted aggregate is frozen, where deletion remains feasible.",
            "risks": "The tasks require time and may expose errors in public technical work. Do not provide secrets, private repository material, or unpublished correspondence.",
            "benefits_and_compensation": "The study promises no scientific, contributor, or authority benefit. Any compensation must be stated and accepted before consent; none is assumed by this packet.",
            "contact_and_incidents": "The invitation must name the study custodian and a private contact channel before consent. Stop the session and contact that custodian if a packet contains private data, a credential, or the wrong fixture.",
            "affirmations": [
                "I am an adult and meet the packet eligibility rules.",
                "I understand what the public dataset may contain and how private data will be retained and deleted.",
                "I consent to this session and know I may stop or withdraw under the stated rule.",
            ],
        },
        "private_custody_plan": {
            "custodian_assignment": "The program owner must name one human custodian before recruitment.",
            "storage": "Use an encrypted, access-controlled location outside every public or private Git worktree. Do not place the re-identification key beside pseudonymous observation exports.",
            "minimum_access": ["named study custodian", "one named backup only when required"],
            "public_repository_prohibitions": method["participant_data_handling"]["public_packet_prohibitions"],
            "incident_response": method["participant_data_handling"]["incident_rule"],
            "deletion_proof": "Retain a public-safe deletion receipt with date, material classes removed, custodian id, and any lawful or consent-based exception. Do not retain participant identities in that receipt.",
        },
        "allocation_receipt_format": {
            "schema": "vela.math.fc-audit.allocation-receipt.v0.1",
            "required_fields": [
                "schema",
                "design_raw_sha256",
                "condition_packet_set_root",
                "seed_commitment",
                "revealed_seed",
                "algorithm",
                "eligible_dyad_pseudonyms",
                "slot_assignments",
                "created_at",
                "receipt_root",
            ],
            "algorithm": design["counterbalance_schedule"]["assignment"],
            "identity_rule": "Use study-random pseudonyms. Keep names, contact details, and the re-identification key outside this receipt and outside Git.",
            "outcome_blind_rule": "Freeze and root the receipt before any condition outcome is inspected.",
        },
        "session_opening_checklist": [
            "Confirm the participant signed the exact consent text and still wishes to proceed.",
            "Confirm eligibility and prior-exposure fields before revealing a packet.",
            "Confirm the packet id, fixture, condition, root, and assigned slot against the frozen allocation receipt.",
            "Deliver only the assigned packet object in an isolated file; do not expose this repository, the packet set, ground truth, or the other condition.",
            "Start separate active-time and wait-time clocks; disclose one task packet at a time.",
            "Stop on a consent, privacy, credential, wrong-packet, or authority-boundary incident.",
        ],
        "does_not_establish": [
            "That a participant has been recruited, contacted, consented, enrolled, or allocated.",
            "That private custody has been activated or a human custodian has accepted the role.",
            "Any H2 or H5 result, interface disposition, Vela Verification, Decision, Event, or Standing.",
        ],
    }
    materials["materials_root"] = semantic_root(materials, "materials_root")
    return materials


def build_packets(selection: dict[str, object], method: dict[str, object]) -> dict[str, object]:
    tasks = [
        {"id": item["id"], "prompt": item["prompt"], "stop_condition": item["stop_condition"]}
        for item in method["tasks"]
    ]
    packets: list[dict[str, object]] = []
    for fixture in selection["fixtures"]:
        shared = {
            "fixture_id": fixture["id"],
            "task_wording": tasks,
            "pull_request": fixture["pull_request"],
            "source_repository_url": "https://github.com/google-deepmind/formal-conjectures.git",
            "source_setup_commands": [
                ["git", "clone", "--filter=blob:none", "https://github.com/google-deepmind/formal-conjectures.git", "$SOURCE_CHECKOUT"],
                ["git", "-C", "$SOURCE_CHECKOUT", "checkout", "--detach", fixture["pull_request"]["head_commit"]],
            ],
            "public_source_command": [
                "git",
                "-C",
                "$SOURCE_CHECKOUT",
                "show",
                f"{fixture['pull_request']['head_commit']}:{fixture['pull_request']['changed_paths'][0]}",
            ],
            "shared_evidence": [descriptor(path) for path in source_paths(fixture)],
            "access_limits": "Public source and the files named by this packet only. Do not use private operator context or outcome labels from another condition.",
        }
        for condition in ("plain-git-and-current-review-artifacts", "same-inputs-plus-fc-pr-audit"):
            packet: dict[str, object] = {
                "schema": "vela.math.fc-audit.condition-packet.v0.1",
                "packet_id": f"{fixture['id']}::{condition}",
                "condition": condition,
                "authority_effect": "none",
                **copy.deepcopy(shared),
                "treatment_evidence": [],
                "does_not_establish": [
                    "The packet label does not reveal the expected fixture outcome to the participant.",
                    "A review answer is not a Formal Conjectures maintainer action or Vela Decision.",
                ],
            }
            if condition == "same-inputs-plus-fc-pr-audit":
                fixture_dir = AUDIT_FIXTURES / fixture["id"]
                packet["treatment_evidence"] = [
                    descriptor(fixture_dir / "expected-core.json"),
                    descriptor(fixture_dir / "expected-observation.json"),
                ]
            packet["packet_root"] = semantic_root(packet, "packet_root")
            packets.append(packet)
    result: dict[str, object] = {
        "schema": "vela.math.fc-audit.condition-packet-set.v0.1",
        "status": "frozen_not_allocated",
        "authority_effect": "none",
        "design": descriptor(DESIGN),
        "selection": descriptor(SELECTION),
        "packet_count": len(packets),
        "packets": packets,
        "matching_rule": "Each control and treatment pair has the same source identity, shared evidence, task wording, and access limits. Treatment adds only the two retained audit records.",
        "delivery_rule": "The operator copies one assigned packet object into an isolated participant file and verifies its packet_root before disclosure. Participants do not receive this set, fixture selection, ground truth, or the other condition.",
        "does_not_establish": [
            "That any packet has been disclosed or assigned to a participant.",
            "That the audit improves review or handoff.",
        ],
    }
    result["packet_set_root"] = semantic_root(result, "packet_set_root")
    return result


def build() -> dict[Path, tuple[dict[str, object], bytes]]:
    selection = load(SELECTION)
    design = load(DESIGN)
    method = load(METHOD)
    materials = build_materials(design, method)
    packets = build_packets(selection, method)
    materials_raw = framed(materials)
    packets_raw = framed(packets)
    readiness: dict[str, object] = {
        "schema": "vela.math.fc-audit.collection-readiness.v0.1",
        "status": "materials_frozen_collection_blocked_on_people_and_custody_activation",
        "authority_effect": "none",
        "design": descriptor(DESIGN),
        "fixture_selection": descriptor(SELECTION),
        "materials": descriptor_for_bytes(
            MATERIALS, materials_raw, materials["materials_root"], materials["schema"]
        ),
        "condition_packets": descriptor_for_bytes(
            PACKETS, packets_raw, packets["packet_set_root"], packets["schema"]
        ),
        "gates": {
            "ground_truth_complete": True,
            "consent_materials_frozen": True,
            "condition_packets_frozen": True,
            "allocation_receipt_format_frozen": True,
            "private_custody_plan_frozen": True,
            "human_custodian_assigned": False,
            "participants_recruited": False,
            "participants_consented": False,
            "allocation_receipt_instantiated": False,
            "private_custody_activated": False,
            "collection_open": False,
        },
        "current_blockers": [
            "The program owner has not named a human study custodian or activated encrypted private custody.",
            "No participant has been recruited, contacted, consented, or enrolled.",
            "No participant-specific pseudonyms or dyads exist, so the allocation receipt cannot be instantiated.",
        ],
        "opening_rule": "A later rooted readiness record may open collection only after every false gate becomes true without changing the frozen design, materials, or packet-set roots.",
        "does_not_establish": [
            "Authorization to recruit, contact, enroll, or collect data from any person.",
            "Any observation, result, effect estimate, interface disposition, or scientific authority action.",
        ],
    }
    readiness["readiness_root"] = semantic_root(readiness, "readiness_root")
    return {
        MATERIALS: (materials, materials_raw),
        PACKETS: (packets, packets_raw),
        READINESS: (readiness, framed(readiness)),
    }


def emit_patch(outputs: dict[Path, tuple[dict[str, object], bytes]]) -> None:
    print("*** Begin Patch")
    for path, (_, raw) in outputs.items():
        print(f"*** Add File: {path}")
        for line in raw.decode().splitlines():
            print("+" + line)
    print("*** End Patch")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--emit-patch", action="store_true")
    parser.add_argument("--print-roots", action="store_true")
    args = parser.parse_args()
    outputs = build()
    if args.emit_patch:
        emit_patch(outputs)
        return 0
    if args.check:
        for path, (_, raw) in outputs.items():
            if not path.exists() or path.read_bytes() != raw:
                raise CollectionBuildError(f"{path.relative_to(REPO)} drift")
    if args.print_roots:
        for path, (document, _) in outputs.items():
            root_field = next(key for key in document if key.endswith("_root"))
            print(f"{path.relative_to(REPO)} {document[root_field]}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CollectionBuildError as error:
        print(f"collection readiness error: {error}", file=sys.stderr)
        raise SystemExit(1)
