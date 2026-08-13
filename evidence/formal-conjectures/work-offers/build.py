#!/usr/bin/env python3
"""Build and inspect the current source-local Formal Conjectures work offer."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
PROJECTION_PATH = REPO_ROOT / "evidence/formal-conjectures/source-adapter/projection.v1.json"
REPOSITORY_PATH = REPO_ROOT / ".vela/repository.json"
PACKET_PATH = HERE / "packets/erdos-887-pr-1237-fidelity-repair.v1.json"
INDEX_PATH = HERE / "index.v1.json"
EXECUTION_DIR = HERE / "execution/erdos-887-pr-1237-fidelity-repair"
PRODUCER_PROFILE_PATH = EXECUTION_DIR / "producer-profile.v1.json"
VERIFIER_CAPSULE_PATH = EXECUTION_DIR / "verifier-capsule.v1.json"
RESULT_CONTRACT_PATH = EXECUTION_DIR / "result-contract.v1.json"
VERIFY_BINDING_PATH = EXECUTION_DIR / "verify_binding.py"

TARGET_ID = "erdos:887"
FIXTURE_ID = "fidelity-erdos-887-1237"
PROJECTION_SCHEMA = "vela.math.fc-pr-audit-projection.v1"
PACKET_SCHEMA = "vela.math.source-fidelity-target-packet.v1"
INDEX_SCHEMA = "vela.math.source-work-offer-index.v1"
PRODUCER_PROFILE_SCHEMA = "vela.math.source-work-producer-profile.v1"
VERIFIER_CAPSULE_SCHEMA = "vela.math.source-fidelity-verifier-capsule.v1"
RESULT_CONTRACT_SCHEMA = "vela.math.fidelity-repair-result-contract.v1"
EXECUTION_BINDING_SCHEMA = "vela.execution-binding.v1"
RESULT_REQUIRED_FIELDS = [
    "schema",
    "authority_effect",
    "target_id",
    "packet_root",
    "producer",
    "result_status",
    "artifacts",
    "source_patch_root",
    "check_result_root",
    "semantic_review",
    "source_roots",
    "nonclaims",
    "result_root",
]


class WorkOfferError(ValueError):
    """Raised when the source projection cannot produce an exact work offer."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise WorkOfferError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _load(path: Path, *, require_framed_lf: bool = True) -> dict[str, Any]:
    raw = path.read_bytes()
    if require_framed_lf and (not raw.endswith(b"\n") or raw.endswith(b"\n\n")):
        raise WorkOfferError(f"{path.relative_to(REPO_ROOT)} must have exactly one trailing LF")
    try:
        value = json.loads(raw, object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise WorkOfferError(f"invalid JSON at {path.relative_to(REPO_ROOT)}: {error}") from error
    if not isinstance(value, dict):
        raise WorkOfferError(f"{path.relative_to(REPO_ROOT)} must contain an object")
    return value


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _root(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _raw_root(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _is_full_sha256_root(value: Any) -> bool:
    return (
        isinstance(value, str)
        and value.startswith("sha256:")
        and len(value) == 71
        and all(character in "0123456789abcdef" for character in value[7:])
    )


def _root_without(value: dict[str, Any], field: str) -> str:
    preimage = copy.deepcopy(value)
    preimage.pop(field, None)
    return _root(preimage)


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO_ROOT, text=True).strip()


def _source_projection() -> tuple[dict[str, Any], dict[str, Any], str, str]:
    projection = _load(PROJECTION_PATH)
    if projection.get("schema") != PROJECTION_SCHEMA:
        raise WorkOfferError("unsupported source projection schema")
    if projection.get("authority_effect") != "none":
        raise WorkOfferError("source projection cannot carry authority")
    projection_root = projection.get("root")
    if not isinstance(projection_root, dict) or projection_root.get("domain") != "projection":
        raise WorkOfferError("source projection root domain drift")
    if projection_root.get("value") != _root_without(projection, "root"):
        raise WorkOfferError("source projection root drift")
    records = projection.get("records")
    if not isinstance(records, list):
        raise WorkOfferError("source projection record inventory is missing")
    matches = [record for record in records if isinstance(record, dict) and record.get("fixture_id") == FIXTURE_ID]
    if len(matches) != 1:
        raise WorkOfferError("clean-candidate source record must occur exactly once")
    record = matches[0]
    if record.get("authority_effect") != "none" or record.get("standing_effect") != "none":
        raise WorkOfferError("source record cannot carry authority or Standing")
    if record.get("automatic_verification") is not False:
        raise WorkOfferError("source record cannot convert automatically to Verification")
    if record.get("source_axis", {}).get("advisory_disposition") != "needs_revision":
        raise WorkOfferError("repair work must remain grounded in the adverse source audit")
    semantic_failures = [
        check for check in record["source_axis"].get("checks", [])
        if check.get("kind") == "semantic" and check.get("outcome") == "fail" and check.get("severity") == "meaning"
    ]
    if len(semantic_failures) != 1 or semantic_failures[0].get("property") != "answer-slot-scope-fidelity":
        raise WorkOfferError("repair work requires the exact answer-slot scope fidelity failure")
    source_commit = _git("log", "-1", "--format=%H", "--", str(PROJECTION_PATH.relative_to(REPO_ROOT)))
    source_tree = _git("show", "-s", "--format=%T", source_commit)
    return projection, record, source_commit, source_tree


def _repository_binding() -> dict[str, str]:
    repository = _load(REPOSITORY_PATH, require_framed_lf=False)
    if repository.get("schema") != "vela.repository.v4":
        raise WorkOfferError("unsupported repository manifest schema")
    return {
        "repository_id": repository["repository_id"],
        "origin_id": repository["origin_id"],
        "repository_root": _root(repository),
    }


def build_execution_components() -> list[tuple[str, Path, dict[str, Any], bytes]]:
    producer_profile: dict[str, Any] = {
        "schema": PRODUCER_PROFILE_SCHEMA,
        "authority_effect": "none",
        "target_id": TARGET_ID,
        "eligible_producer_classes": ["agent", "ci"],
        "input_contract": {
            "packet_schema": PACKET_SCHEMA,
            "exact_packet_root_required": True,
            "source_access": "public_only",
            "participant_private_data_allowed": False,
        },
        "execution_contract": {
            "workspace": "disposable source checkout or equivalent isolated worktree",
            "retained_check_network": "not_required",
            "required_tools": ["git", "python3", "lake", "lean"],
            "required_outputs": [
                "rooted source patch",
                "rooted Lean check result",
                "rooted result manifest",
                "witness-backed semantic rationale awaiting a named human reviewer",
            ],
        },
        "permissions": {
            "allowed": [
                "Read the exact public packet and retained public source bytes.",
                "Prepare a bounded source patch and public check evidence.",
                "Export canonical unsigned Submission bytes for a separate local signer.",
            ],
            "forbidden": [
                "Post, edit, review, or merge anything upstream without separate explicit authorization.",
                "Access Repository authority credentials or sign for another actor.",
                "Create a Vela Verification, Decision, Event, or Standing change.",
                "Represent same-operator checking as independent review.",
            ],
        },
        "required_provenance": [
            "operator_id",
            "provider",
            "runtime",
            "source_root",
            "packet_root",
            "output_roots",
            "timestamps",
            "access_limits",
            "independence_disclosure",
        ],
        "custody": {
            "access": "public",
            "proof_artifacts_may_be_public": True,
            "participant_private_data_allowed": False,
        },
        "nonclaims": [
            "This profile describes eligible activity-plane production and grants no scientific or Repository authority.",
            "Conformance to this profile is not a Vela Verification, human Decision, or change to Standing.",
        ],
        "profile_root_definition": "sha256 of canonical JSON after removing only profile_root",
    }
    producer_profile["profile_root"] = _root(producer_profile)

    verifier_capsule: dict[str, Any] = {
        "schema": VERIFIER_CAPSULE_SCHEMA,
        "authority_effect": "none",
        "target_id": TARGET_ID,
        "implementation": {
            "path": str(VERIFY_BINDING_PATH.relative_to(REPO_ROOT)),
            "raw_sha256": _raw_root(VERIFY_BINDING_PATH.read_bytes()),
            "command": [
                "python3",
                "-B",
                str(VERIFY_BINDING_PATH.relative_to(REPO_ROOT)),
            ],
            "result_argument": ["--result", "PATH"],
            "dependencies": "python standard library only",
            "network": "not_required",
        },
        "bounded_property": "Validate canonical framing, public custody, exact component descriptors, and the full vela.execution-binding.v1 for the Erdős 887 offer; when a result path is supplied, additionally validate its current packet binding, positive result state, pending semantic-review boundary, and result root.",
        "checks": [
            "Reject duplicate JSON keys and non-canonical JSON framing.",
            "Reject a changed Target, packet root, source patch, Lean check result, or result root.",
            "Reject any authority effect or fabricated completed human source-fidelity review.",
            "Require the candidate_ready_for_human_review result state and pending named-human review boundary.",
        ],
        "expected_exit_codes": {"pass": 0, "refusal": "nonzero"},
        "custody": {
            "access": "public",
            "inputs_must_be_public": True,
            "participant_private_data_allowed": False,
        },
        "does_not_establish": [
            "The capsule does not prove Erdős problem 887 or establish informal statement fidelity.",
            "The capsule does not establish reviewer independence, upstream acceptance, Vela Verification, human Decision, or Math Standing.",
        ],
        "verifier_capsule_root_definition": "sha256 of canonical JSON after removing only verifier_capsule_root",
    }
    verifier_capsule["verifier_capsule_root"] = _root(verifier_capsule)

    result_contract: dict[str, Any] = {
        "schema": RESULT_CONTRACT_SCHEMA,
        "authority_effect": "none",
        "target_id": TARGET_ID,
        "result": {
            "schema": "vela.math.fidelity-repair-result.v1",
            "media_type": "application/json",
            "maximum_bytes": 65536,
            "canonical_framing": "canonical JSON plus exactly one trailing LF",
            "required_fields": RESULT_REQUIRED_FIELDS,
        },
        "positive_result": {
            "result_status": "candidate_ready_for_human_review",
            "semantic_review": {
                "required": True,
                "status": "pending",
                "independent": False,
                "reviewer": None,
            },
            "required_artifacts": ["source_patch", "lean_check"],
        },
        "root_requirements": [
            "The packet, patch, Lean check, result, source base, and source result use full lowercase sha256 roots.",
            "The result packet_root must equal the packet executed by the producer.",
            "The result root omits only result_root from its canonical preimage.",
        ],
        "custody": {
            "access": "public",
            "proof_artifacts_may_be_public": True,
            "participant_private_data_allowed": False,
        },
        "nonclaims": [
            "A contract-conforming result is only a candidate for named human source-fidelity review.",
            "A positive result is not upstream acceptance, Vela Verification, human Decision, Event, or Math Standing.",
        ],
        "result_contract_root_definition": "sha256 of canonical JSON after removing only result_contract_root",
    }
    result_contract["result_contract_root"] = _root(result_contract)

    values = [
        ("producer_profile", PRODUCER_PROFILE_PATH, producer_profile, _canonical_bytes(producer_profile) + b"\n"),
        ("verifier_capsule", VERIFIER_CAPSULE_PATH, verifier_capsule, _canonical_bytes(verifier_capsule) + b"\n"),
        ("result_contract", RESULT_CONTRACT_PATH, result_contract, _canonical_bytes(result_contract) + b"\n"),
    ]
    return values


def _component_descriptors(
    components: list[tuple[str, Path, dict[str, Any], bytes]],
) -> dict[str, dict[str, Any]]:
    root_fields = {
        "producer_profile": "profile_root",
        "verifier_capsule": "verifier_capsule_root",
        "result_contract": "result_contract_root",
    }
    return {
        name: {
            "schema": value["schema"],
            "path": str(path.relative_to(REPO_ROOT)),
            "root": value[root_fields[name]],
            "raw_sha256": _raw_root(raw),
            "size": len(raw),
        }
        for name, path, value, raw in components
    }


def _validate_execution_components(
    components: list[tuple[str, Path, dict[str, Any], bytes]],
) -> None:
    expected = {
        "producer_profile": (PRODUCER_PROFILE_PATH, PRODUCER_PROFILE_SCHEMA, "profile_root"),
        "verifier_capsule": (VERIFIER_CAPSULE_PATH, VERIFIER_CAPSULE_SCHEMA, "verifier_capsule_root"),
        "result_contract": (RESULT_CONTRACT_PATH, RESULT_CONTRACT_SCHEMA, "result_contract_root"),
    }
    if [name for name, _, _, _ in components] != list(expected):
        raise WorkOfferError("execution component inventory drift")
    for name, path, value, raw in components:
        expected_path, schema, root_field = expected[name]
        if path != expected_path or value.get("schema") != schema:
            raise WorkOfferError(f"{name} identity drift")
        if value.get("authority_effect") != "none":
            raise WorkOfferError(f"{name} cannot carry authority")
        custody = value.get("custody")
        if not isinstance(custody, dict) or custody.get("access") != "public":
            raise WorkOfferError(f"{name} must remain public")
        if custody.get("participant_private_data_allowed") is not False:
            raise WorkOfferError(f"{name} cannot admit participant private data")
        if raw != _canonical_bytes(value) + b"\n":
            raise WorkOfferError(f"{name} canonical framing drift")
        root = value.get(root_field)
        if not _is_full_sha256_root(root) or root != _root_without(value, root_field):
            raise WorkOfferError(f"{name} root drift")


def build_packet(components: list[tuple[str, Path, dict[str, Any], bytes]]) -> dict[str, Any]:
    _validate_execution_components(components)
    projection, record, source_commit, source_tree = _source_projection()
    repository = _repository_binding()
    native = record["native_identity"]
    source_records = record["source_records"]
    packet: dict[str, Any] = {
        "schema": PACKET_SCHEMA,
        "authority_effect": "none",
        "target": {
            "id": TARGET_ID,
            "title": "Repair the answer-slot scope defect in the Erdős 887 formalization",
            "source_fixture_id": FIXTURE_ID,
        },
        "repository": {
            **repository,
            "source_commit": source_commit,
            "source_tree": source_tree,
        },
        "source": {
            "projection_path": str(PROJECTION_PATH.relative_to(REPO_ROOT)),
            "projection_root": projection["root"]["value"],
            "record_root": record["root"]["value"],
            "audit_core_root": source_records["core"]["record_root"]["value"],
            "audit_observation_root": source_records["observation"]["record_root"]["value"],
            "repository": native["repository"]["url"],
            "pull_request": native["pull_request"]["number"],
            "pull_request_url": native["pull_request"]["url"],
            "head_commit": native["head"]["commit_oid"],
            "head_tree": native["head"]["tree_oid"],
            "changed_paths": [change["path"] for change in native["changes"]],
            "observed_disposition": record["source_axis"]["advisory_disposition"],
            "basis_check_id": "answer-slot-scope",
        },
        "objective": "Produce an exact, reviewable correction for the answer slot occurring under the C and n binders in FormalConjectures/ErdosProblems/887.lean, preserve the intended absolute-K statement, and return rooted source and check evidence for independent human review.",
        "completion_contract": {
            "required": [
                "Review only the exact retained PR head, tree, changed path, and roots named by this packet.",
                "Retain the proposed source patch, exact base and result roots, and a network-independent Lean check command.",
                "Demonstrate that the answer slot selects one absolute K rather than a value under the C and n binders.",
                "Return witness-backed semantic review with exact locators, naming the human reviewer and whether that review is independent of the producer.",
                "Keep upstream PR state, source-audit disposition, Vela Verification, human Decision, and Math Standing separate.",
            ],
            "forbidden": [
                "Posting or editing any upstream comment, review, or issue without separate explicit authorization.",
                "Treating CI success, compilation, a source-audit pass, or the activity result as scientific acceptance.",
                "Creating a Vela Verification, Decision, Event, or Standing change from this activity packet.",
                "Accessing Repository authority credentials or signing on behalf of an authorized human.",
            ],
        },
        "expected_return": {
            "schema": "vela.math.fidelity-repair-result.v1",
            "media_type": "application/json",
            "maximum_bytes": 65536,
            "required_fields": RESULT_REQUIRED_FIELDS,
        },
        "custody": {
            "access": "public",
            "proof_artifacts_may_be_public": True,
            "participant_private_data_allowed": False,
        },
        "execution_components": {
            "authority_effect": "none",
            **_component_descriptors(components),
        },
        "nonclaims": [
            "This source-local Target packet is not a Vela protocol object.",
            "The retained source audit reports needs_revision despite a successful exact-head build.",
            "Completing or reviewing the repair does not itself create a Vela Verification or human Decision.",
            "No Workspace action or source review changes Math Standing.",
        ],
        "packet_root_definition": "sha256 of canonical JSON after removing only packet_root",
    }
    packet["packet_root"] = _root(packet)
    return packet


def build_index(packet: dict[str, Any], packet_raw: bytes) -> dict[str, Any]:
    if packet.get("packet_root") != _root_without(packet, "packet_root"):
        raise WorkOfferError("packet root drift before index construction")
    component_set = packet.get("execution_components")
    if not isinstance(component_set, dict) or component_set.get("authority_effect") != "none":
        raise WorkOfferError("packet execution component boundary drift")
    for name in ("producer_profile", "verifier_capsule", "result_contract"):
        descriptor = component_set.get(name)
        if not isinstance(descriptor, dict) or not _is_full_sha256_root(descriptor.get("root")):
            raise WorkOfferError(f"packet {name} descriptor drift")
    projection, record, source_commit, source_tree = _source_projection()
    repository = _repository_binding()
    index: dict[str, Any] = {
        "schema": INDEX_SCHEMA,
        "authority_effect": "none",
        "repository": repository,
        "source": {
            "commit": source_commit,
            "tree": source_tree,
            "projection_path": str(PROJECTION_PATH.relative_to(REPO_ROOT)),
            "projection_root": projection["root"]["value"],
            "record_root": record["root"]["value"],
        },
        "claim_boundary": {
            "derived": True,
            "authoritative": False,
            "deletable": True,
        },
        "targets": [
            {
                "id": TARGET_ID,
                "title": packet["target"]["title"],
                "presence": "open",
                "rank": 1,
                "lane": "source-fidelity-repair",
                "objective": packet["objective"],
                "verifier_profile": "lean-build-plus-human-source-fidelity-review.v1",
                "execution_binding": {
                    "schema": EXECUTION_BINDING_SCHEMA,
                    "packet_root": packet["packet_root"],
                    "profile_root": packet["execution_components"]["producer_profile"]["root"],
                    "verifier_capsule_root": packet["execution_components"]["verifier_capsule"]["root"],
                    "result_contract_root": packet["execution_components"]["result_contract"]["root"],
                },
                "next_command": f"python3 -B {HERE.relative_to(REPO_ROOT)}/build.py --check --print-target {TARGET_ID}",
                "packet": {
                    "schema": packet["schema"],
                    "path": str(PACKET_PATH.relative_to(REPO_ROOT)),
                    "size": len(packet_raw),
                    "raw_sha256": _raw_root(packet_raw),
                    "packet_root": packet["packet_root"],
                },
            }
        ],
        "nonclaims": [
            "This index is a disposable source-local work projection and carries no scientific authority.",
            "An open offer is not a Vela Proposal, Verification, Decision, or change to Standing.",
            "The Web activity plane may retain this exact Target and packet root but cannot decide it.",
        ],
        "index_root_definition": "sha256 of canonical JSON after removing only index_root",
    }
    index["index_root"] = _root(index)
    return index


def build() -> tuple[list[tuple[str, Path, dict[str, Any], bytes]], dict[str, Any], bytes, dict[str, Any], bytes]:
    components = build_execution_components()
    packet = build_packet(components)
    packet_raw = _canonical_bytes(packet) + b"\n"
    index = build_index(packet, packet_raw)
    index_raw = _canonical_bytes(index) + b"\n"
    return components, packet, packet_raw, index, index_raw


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--print-target")
    parser.add_argument("--print-roots", action="store_true")
    args = parser.parse_args()
    components, packet, packet_raw, index, index_raw = build()
    if args.check:
        for _, path, _, raw in components:
            if path.read_bytes() != raw:
                raise SystemExit(f"{path.relative_to(REPO_ROOT)} does not match the deterministic execution component")
        if PACKET_PATH.read_bytes() != packet_raw:
            raise SystemExit("target packet does not match exact source inputs")
        if INDEX_PATH.read_bytes() != index_raw:
            raise SystemExit("work-offer index does not match exact source inputs")
    else:
        EXECUTION_DIR.mkdir(parents=True, exist_ok=True)
        for _, path, _, raw in components:
            path.write_bytes(raw)
        PACKET_PATH.parent.mkdir(parents=True, exist_ok=True)
        PACKET_PATH.write_bytes(packet_raw)
        INDEX_PATH.write_bytes(index_raw)
    if args.print_target is not None:
        if args.print_target != TARGET_ID:
            raise SystemExit(f"unknown Target: {args.print_target}")
        print(packet_raw.decode("utf-8"), end="")
    if args.print_roots:
        print(json.dumps({
            "index_root": index["index_root"],
            **index["targets"][0]["execution_binding"],
        }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
