#!/usr/bin/env python3
"""Build the immutable Erdős 887 Work Offer lifecycle projection."""

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
ISSUED_PACKET_SOURCE_PATH = HERE / "results/erdos-887-pilot-02-current-binding/target-packet.v1.json"
RESULT_PATH = HERE / "results/erdos-887-pilot-02-current-binding/result.v1.json"
REVIEW_PATH = REPO_ROOT / "evidence/formal-conjectures/reviews/erdos-887-gpt-5.6-sol-peer-statement-fidelity.v1.json"
PROPOSAL_PATH = REPO_ROOT / "records/proposals/sha256/44ff50ca8cf1bd6ebca04f05e631c4f75c2f8f1a6ba67c191d56375c29a8fc50.json"
CLAIM_PATH = REPO_ROOT / "records/claims/sha256/c445d8df3e41982ccb1d0628fc89060097f5a2a10040d73a8eb78cde226beea1.json"
DECISION_EVENT_PATH = REPO_ROOT / ".vela/authority/events/vev_272d414a6f4f6e20.json"
APPLICATION_EVENT_PATH = REPO_ROOT / ".vela/authority/events/vev_65af894447e0f2c8.json"
LIFECYCLE_PATH = HERE / "lifecycle/erdos-887-pr-1237-fidelity-repair.v1.json"
INDEX_PATH = HERE / "index.v1.json"

TARGET_ID = "erdos:887"
FIXTURE_ID = "fidelity-erdos-887-1237"
ISSUANCE_COMMIT = "7d5f9290018a03ce395092096db34b46fcffe1a1"
PROJECTION_SCHEMA = "vela.math.fc-pr-audit-projection.v1"
PACKET_SCHEMA = "vela.math.source-fidelity-target-packet.v1"
LIFECYCLE_SCHEMA = "vela.math.source-work-offer-lifecycle.v1"
INDEX_SCHEMA = "vela.math.source-work-offer-index.v1"
EXECUTION_BINDING_SCHEMA = "vela.execution-binding.v1"

# These commits mechanically rebound the same semantic offer after the issued
# packet had already produced the retained result. They remain in Git history,
# but none is a fresh issuance and none may be projected as open work.
RETIRED_REBINDINGS = (
    ("e2d37f3add5da1118bad527570f737b92429bd2f", "sha256:f0ce498c42f9ce63868c14f2698541a423a8b7c23e449c263f7380f997edc5da"),
    ("5df845d6be7b263b543430845280d597dbe34d57", "sha256:7956b85bd89185f8e1b6d4e5a827d2c8e37f86d466bf0f39ee9b6e24ac30c5b8"),
    ("a89d535b6ab9eb77339c0794a96de23c34e2701f", "sha256:89833e84d73a0c60e5bbc1a164388b1c22f1dbf536393024edf3b0679b635076"),
    ("d45fdf5be16ed11316bb91331e9a7b57aed928a8", "sha256:f50c6415da5a9a1bb6edcc8a17301432d3bfd59ab03ecc99c7e6735303ffdc2c"),
    ("aef1b6b794b28debc0c62a270c48c891e5c0790f", "sha256:2e9ab3d4de6479e671c340abaeead9af6934e95a40dda3909102b12b98dd2afb"),
    ("a8fb8d7f316ff22b96a64595fab9377e127c58f0", "sha256:549af622fa3dbbb2dd6a228f5a2cb8f60eed34a4626a39d14d751e4b0cf26d7a"),
    ("1042185e4355044455e36831bdb61d821ed0a709", "sha256:bcbcc9d4f90603df5e83af462b02076d0c50d850b10b38297231aef4eab95429"),
)


class WorkOfferError(ValueError):
    """Raised when retained Work Offer or lifecycle evidence is inconsistent."""


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
    if require_framed_lf and raw != _canonical_bytes(value) + b"\n":
        raise WorkOfferError(f"{path.relative_to(REPO_ROOT)} must contain canonical JSON")
    return value


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _root(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _raw_root(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _root_without(value: dict[str, Any], field: str) -> str:
    preimage = copy.deepcopy(value)
    preimage.pop(field, None)
    return _root(preimage)


def _is_full_sha256_root(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 71 and value.startswith("sha256:") and all(
        character in "0123456789abcdef" for character in value[7:]
    )


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO_ROOT, text=True).strip()


def _git_bytes(commit: str, path: Path) -> bytes:
    return subprocess.check_output(
        ["git", "show", f"{commit}:{path.relative_to(REPO_ROOT)}"],
        cwd=REPO_ROOT,
    )


def _descriptor(path: Path, value: dict[str, Any], raw: bytes, root_field: str) -> dict[str, Any]:
    return {
        "schema": value["schema"],
        "path": str(path.relative_to(REPO_ROOT)),
        "size": len(raw),
        "raw_sha256": _raw_root(raw),
        root_field: value[root_field],
    }


def _repository_binding() -> dict[str, str]:
    repository = _load(REPOSITORY_PATH, require_framed_lf=False)
    if repository.get("schema") != "vela.repository.v4":
        raise WorkOfferError("unsupported repository manifest schema")
    return {
        "repository_id": repository["repository_id"],
        "origin_id": repository["origin_id"],
        "repository_root": _root(repository),
    }


def _source_projection() -> tuple[dict[str, Any], dict[str, Any], str, str]:
    projection = _load(PROJECTION_PATH)
    if projection.get("schema") != PROJECTION_SCHEMA or projection.get("authority_effect") != "none":
        raise WorkOfferError("source projection schema or authority drift")
    if projection.get("root", {}).get("domain") != "projection" or projection["root"].get("value") != _root_without(projection, "root"):
        raise WorkOfferError("source projection root drift")
    matches = [record for record in projection.get("records", []) if record.get("fixture_id") == FIXTURE_ID]
    if len(matches) != 1:
        raise WorkOfferError("source record must occur exactly once")
    record = matches[0]
    if record.get("authority_effect") != "none" or record.get("standing_effect") != "none":
        raise WorkOfferError("source record cannot carry authority or Standing")
    source_commit = _git("log", "-1", "--format=%H", "--", str(PROJECTION_PATH.relative_to(REPO_ROOT)))
    return projection, record, source_commit, _git("show", "-s", "--format=%T", source_commit)


def _validate_component(name: str, descriptor: dict[str, Any]) -> None:
    root_fields = {
        "producer_profile": "profile_root",
        "verifier_capsule": "verifier_capsule_root",
        "result_contract": "result_contract_root",
    }
    root_field = root_fields[name]
    path = REPO_ROOT / descriptor["path"]
    value = _load(path)
    raw = path.read_bytes()
    if value.get("authority_effect") != "none" or value.get(root_field) != _root_without(value, root_field):
        raise WorkOfferError(f"issued {name} authority or root drift")
    expected = _descriptor(path, value, raw, root_field)
    if descriptor != {
        "schema": expected["schema"],
        "path": expected["path"],
        "size": expected["size"],
        "raw_sha256": expected["raw_sha256"],
        "root": expected[root_field],
    }:
        raise WorkOfferError(f"issued {name} descriptor drift")


def load_issued_packet() -> tuple[dict[str, Any], bytes]:
    packet = _load(ISSUED_PACKET_SOURCE_PATH)
    raw = ISSUED_PACKET_SOURCE_PATH.read_bytes()
    if packet.get("schema") != PACKET_SCHEMA or packet.get("authority_effect") != "none":
        raise WorkOfferError("issued packet schema or authority drift")
    if packet.get("packet_root") != _root_without(packet, "packet_root"):
        raise WorkOfferError("issued packet root drift")
    if packet.get("target", {}).get("id") != TARGET_ID:
        raise WorkOfferError("issued packet Target drift")
    if _git_bytes(ISSUANCE_COMMIT, PACKET_PATH) != raw:
        raise WorkOfferError("issued packet differs from its exact issuance commit")
    if _git("show", "-s", "--format=%T", packet["repository"]["source_commit"]) != packet["repository"]["source_tree"]:
        raise WorkOfferError("issued packet source tree drift")
    historical_projection = json.loads(
        _git_bytes(packet["repository"]["source_commit"], REPO_ROOT / packet["source"]["projection_path"]),
        object_pairs_hook=_reject_duplicate_keys,
    )
    if historical_projection.get("root", {}).get("value") != packet["source"]["projection_root"]:
        raise WorkOfferError("issued packet historical projection drift")
    matches = [record for record in historical_projection.get("records", []) if record.get("root", {}).get("value") == packet["source"]["record_root"]]
    if len(matches) != 1:
        raise WorkOfferError("issued packet historical source record drift")
    components = packet.get("execution_components")
    if not isinstance(components, dict) or components.get("authority_effect") != "none":
        raise WorkOfferError("issued packet execution component boundary drift")
    for name in ("producer_profile", "verifier_capsule", "result_contract"):
        _validate_component(name, components[name])
    return packet, raw


def _validate_rebinding_history() -> list[dict[str, str]]:
    recovered: list[dict[str, str]] = []
    for commit, packet_root in RETIRED_REBINDINGS:
        packet = json.loads(_git_bytes(commit, PACKET_PATH), object_pairs_hook=_reject_duplicate_keys)
        if packet.get("packet_root") != packet_root or packet_root != _root_without(packet, "packet_root"):
            raise WorkOfferError(f"retired rebind root drift at {commit}")
        recovered.append({
            "commit": commit,
            "packet_root": packet_root,
            "disposition": "retired_administrative_rebinding",
        })
    return recovered


def build_lifecycle(packet: dict[str, Any], packet_raw: bytes) -> dict[str, Any]:
    result = _load(RESULT_PATH)
    review = _load(REVIEW_PATH)
    proposal = _load(PROPOSAL_PATH, require_framed_lf=False)
    claim = _load(CLAIM_PATH, require_framed_lf=False)
    decision = _load(DECISION_EVENT_PATH, require_framed_lf=False)
    application = _load(APPLICATION_EVENT_PATH, require_framed_lf=False)
    result_raw = RESULT_PATH.read_bytes()
    review_raw = REVIEW_PATH.read_bytes()
    proposal_raw = PROPOSAL_PATH.read_bytes()
    claim_raw = CLAIM_PATH.read_bytes()
    decision_raw = DECISION_EVENT_PATH.read_bytes()
    application_raw = APPLICATION_EVENT_PATH.read_bytes()

    if result.get("packet_root") != packet["packet_root"] or result.get("result_root") != _root_without(result, "result_root"):
        raise WorkOfferError("completion result does not bind the issued packet")
    if review.get("outcome") != "pass" or review.get("subject", {}).get("target_id") != TARGET_ID:
        raise WorkOfferError("completion review is not a passing review of the Target")
    if review.get("inputs", {}).get("execution_result", {}).get("root") != result["result_root"]:
        raise WorkOfferError("completion review result binding drift")
    if review.get("subject", {}).get("proposal_root") != _raw_root(proposal_raw):
        raise WorkOfferError("completion review Proposal binding drift")
    event = decision.get("content", {})
    payload = event.get("payload", {})
    if event.get("kind") != "review.accepted" or payload.get("proposal_id") != review["subject"]["proposal_id"]:
        raise WorkOfferError("scientific Decision does not accept the reviewed Proposal")
    applied_event = application.get("content", {})
    applied_payload = applied_event.get("payload", {})
    if (
        applied_event.get("kind") != "claim.asserted"
        or applied_payload.get("proposal_id") != payload.get("proposal_id")
        or applied_event.get("transaction_id") != event.get("transaction_id")
        or applied_payload.get("repository_before") != payload.get("repository_before")
        or applied_payload.get("repository_after") != payload.get("repository_after")
    ):
        raise WorkOfferError("scientific Decision applied Event binding drift")
    if proposal.get("subject", {}).get("root") != _raw_root(claim_raw) or applied_payload.get("claim_root") != proposal["subject"]["root"]:
        raise WorkOfferError("scientific Decision Claim binding drift")
    lifecycle: dict[str, Any] = {
        "schema": LIFECYCLE_SCHEMA,
        "authority_effect": "none",
        "target_id": TARGET_ID,
        "presence": "superseded",
        "issued_offer": {
            "issuance_commit": ISSUANCE_COMMIT,
            "repository_root": packet["repository"]["repository_root"],
            "packet": _descriptor(PACKET_PATH, packet, packet_raw, "packet_root"),
        },
        "completion": {
            "contract_status": "not_satisfied",
            "closure_status": "closed_superseded",
            "closed_at": event["timestamp"],
            "contract_gap": "The issued packet required an independent human review. The retained qualifying review was performed by an independent AI-model reviewer, and later performer-neutral packet rebindings were not fresh executed issuances.",
            "result": {
                "path": str(RESULT_PATH.relative_to(REPO_ROOT)),
                "raw_sha256": _raw_root(result_raw),
                "result_root": result["result_root"],
                "check_result_root": result["check_result_root"],
            },
            "review": {
                "path": str(REVIEW_PATH.relative_to(REPO_ROOT)),
                "raw_sha256": _raw_root(review_raw),
                "outcome": review["outcome"],
                "reviewer": review["reviewer"],
                "independence": review["independence"],
                "method": review["method"],
            },
        },
        "decisions": {
            "scientific": {
                "domain": "scientific",
                "status": "accepted",
                "proposal_id": payload["proposal_id"],
                "proposal_root": _raw_root(proposal_raw),
                "claim_id": applied_payload["claim_id"],
                "claim_root": applied_payload["claim_root"],
                "event_id": decision["id"],
                "protocol_event_id": payload["applied_event_id"],
                "event_path": str(DECISION_EVENT_PATH.relative_to(REPO_ROOT)),
                "event_raw_sha256": _raw_root(decision_raw),
                "applied_event_id": application["id"],
                "applied_event_path": str(APPLICATION_EVENT_PATH.relative_to(REPO_ROOT)),
                "applied_event_raw_sha256": _raw_root(application_raw),
                "decided_at": event["timestamp"],
                "performer": {
                    "class": event["actor"]["type"],
                    "id": event["actor"]["id"],
                },
                "authority_principal": event["principal_id"],
                "reason": event["reason"],
            },
            "program": {
                "domain": "program",
                "status": "not_applicable",
                "authority_effect": "none",
                "reason": "The issued Work Offer carried no reward, payment, or resource-release commitment, so no program Decision exists.",
            },
            "deployment": {
                "domain": "deployment",
                "status": "not_applicable",
                "authority_effect": "none",
                "reason": "No upstream merge, procurement, or deployment Decision was part of this Work Offer.",
            },
        },
        "remap": {
            "state": "identified_not_offered",
            "next_obligation": {
                "id": "erdos:887:proof-discharge",
                "title": "Discharge the remaining proof placeholder for the corrected Erdős 887 declaration",
                "basis_claim_id": applied_payload["claim_id"],
                "basis_claim_root": applied_payload["claim_root"],
                "authority_effect": "none",
            },
            "reason": "The correction is retained in Math Standing, while the mathematical proposition remains unproved and no successor Work Offer has been issued.",
        },
        "retired_rebindings": _validate_rebinding_history(),
        "nonclaims": [
            "Closing this superseded Work Offer does not claim that its exact Completion Contract was satisfied.",
            "The scientific Decision remains valid and separate from the source-owned Work Offer contract gap.",
            "Neither the retained result nor its attributed agent review proves Erdős problem 887.",
            "The program and deployment domains have no Decision because neither domain was part of the issued contract.",
            "The identified next Obligation is not an open Work Offer and authorizes no upstream action.",
            "This lifecycle projection references the scientific Decision but carries no authority of its own.",
        ],
        "lifecycle_root_definition": "sha256 of canonical JSON after removing only lifecycle_root",
    }
    lifecycle["lifecycle_root"] = _root(lifecycle)
    return lifecycle


def build_index(packet: dict[str, Any], packet_raw: bytes, lifecycle: dict[str, Any], lifecycle_raw: bytes) -> dict[str, Any]:
    projection, record, source_commit, source_tree = _source_projection()
    binding = {
        "schema": EXECUTION_BINDING_SCHEMA,
        "packet_root": packet["packet_root"],
        "profile_root": packet["execution_components"]["producer_profile"]["root"],
        "verifier_capsule_root": packet["execution_components"]["verifier_capsule"]["root"],
        "result_contract_root": packet["execution_components"]["result_contract"]["root"],
    }
    index: dict[str, Any] = {
        "schema": INDEX_SCHEMA,
        "authority_effect": "none",
        "repository": _repository_binding(),
        "source": {
            "commit": source_commit,
            "tree": source_tree,
            "projection_path": str(PROJECTION_PATH.relative_to(REPO_ROOT)),
            "projection_root": projection["root"]["value"],
            "record_root": record["root"]["value"],
        },
        "claim_boundary": {"derived": True, "authoritative": False, "deletable": True},
        "targets": [{
            "id": TARGET_ID,
            "title": packet["target"]["title"],
            "presence": "superseded",
            "rank": 1,
            "lane": "source-fidelity-repair",
            "objective": packet["objective"],
            "verifier_profile": "lean-build-plus-attributed-source-fidelity-review.v1",
            "next_command": None,
            "execution_binding": binding,
            "packet": _descriptor(PACKET_PATH, packet, packet_raw, "packet_root"),
            "lifecycle": _descriptor(LIFECYCLE_PATH, lifecycle, lifecycle_raw, "lifecycle_root"),
        }],
        "nonclaims": [
            "This index is a disposable source-local work projection and carries no scientific authority.",
            "A superseded offer is not open work and may not be rebound to a later Repository root as a fresh issuance.",
            "Scientific, program, and deployment Decisions remain independent domains.",
        ],
        "index_root_definition": "sha256 of canonical JSON after removing only index_root",
    }
    index["index_root"] = _root(index)
    return index


def build() -> tuple[dict[str, Any], bytes, dict[str, Any], bytes, dict[str, Any], bytes]:
    packet, packet_raw = load_issued_packet()
    lifecycle = build_lifecycle(packet, packet_raw)
    lifecycle_raw = _canonical_bytes(lifecycle) + b"\n"
    index = build_index(packet, packet_raw, lifecycle, lifecycle_raw)
    index_raw = _canonical_bytes(index) + b"\n"
    return packet, packet_raw, lifecycle, lifecycle_raw, index, index_raw


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--print-target")
    parser.add_argument("--print-roots", action="store_true")
    args = parser.parse_args()
    packet, packet_raw, lifecycle, lifecycle_raw, index, index_raw = build()
    expected = ((PACKET_PATH, packet_raw), (LIFECYCLE_PATH, lifecycle_raw), (INDEX_PATH, index_raw))
    if args.check:
        for path, raw in expected:
            if not path.exists() or path.read_bytes() != raw:
                raise SystemExit(f"{path.relative_to(REPO_ROOT)} does not match the immutable lifecycle projection")
    else:
        for path, raw in expected:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
    if args.print_target is not None:
        if args.print_target != TARGET_ID:
            raise SystemExit(f"unknown Target: {args.print_target}")
        print(_canonical_bytes(index["targets"][0]).decode("utf-8"))
    if args.print_roots:
        print(json.dumps({
            "index_root": index["index_root"],
            "lifecycle_root": lifecycle["lifecycle_root"],
            **index["targets"][0]["execution_binding"],
        }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
