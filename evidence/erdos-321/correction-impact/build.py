#!/usr/bin/env python3
"""Build and validate the bounded Erdős 321 correction-impact record."""

from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import math
from pathlib import Path
import subprocess
from typing import Any


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OUTPUT = HERE / "correction-impact.v1.json"
CORE_READER_COMMIT = "f61abcee4edd2d8a33fa181f4aac6eade82c6edf"
CORE_READER_VERSION = "0.973.0"

REPLAY_STAGES = (
    {
        "label": "before_predecessor_rejection",
        "commit": "c49081f9fec5e7054623343691f90f6a4e985056",
        "tree": "de7c5d1a488cd64fb06bda94bb8877bd33ae78ec",
        "repository_root": "sha256:f89e9b08554d59a7fdaf553104aec1d5d176eb2ccd2f222d56b9fdb0a880d591",
        "counts": {"accepted_claims": 0, "artifacts": 3, "pending_claims": 3, "proposal_withdrawals": 0, "proposals": 3, "submissions": 3, "verifications": 7},
    },
    {
        "label": "after_predecessor_rejection",
        "commit": "52ddf457ae4c8241a8a6145df70f23fabe2f2435",
        "tree": "9b72a7964c248277baa15db7549a5df11c166997",
        "repository_root": "sha256:4aed9ba56f5608ee782970dbdb96682da03902a96b97dfc69dc9b297bd6d514c",
        "counts": {"accepted_claims": 0, "artifacts": 3, "pending_claims": 2, "proposal_withdrawals": 0, "proposals": 3, "submissions": 3, "verifications": 7},
    },
    {
        "label": "before_corrected_successor_acceptance",
        "commit": "7e9a18e4d437ad8a24e788305b2e03ffe3813878",
        "tree": "18675b8794536093066ec453fb9594a0b8e93341",
        "repository_root": "sha256:bc36be46a09ca4aafd99b20c384bcf6a807e0094e6e7a55879d943cefbf041d5",
        "counts": {"accepted_claims": 0, "artifacts": 3, "pending_claims": 1, "proposal_withdrawals": 0, "proposals": 3, "submissions": 3, "verifications": 7},
    },
    {
        "label": "after_corrected_successor_acceptance",
        "commit": "9bdabbcc1f77d0dd60458e3e9d91d2ffa01fd476",
        "tree": "3c99d1b9c969a8559605a664bdd7280e9729169f",
        "repository_root": "sha256:db4d435c2989d43c7ab88fe135865e89a6ba095429315baedb78bcbd9e90ebdc",
        "counts": {"accepted_claims": 1, "artifacts": 3, "pending_claims": 0, "proposal_withdrawals": 0, "proposals": 3, "submissions": 3, "verifications": 7},
    },
)

PREDECESSOR = {
    "claim_id": "vcl_24878e1c6851b4e5bf7162efb5dff159ae5eff6174d2c521a0c009799d11c247",
    "claim_path": "records/claims/sha256/40dec807844df7badd60cab570b811a1c6137bd0d0a9b6d1408f3b2da33d1f67.json",
    "proposal_id": "vpr_da51a4120b1f1090",
    "proposal_path": "records/proposals/sha256/da51a4120b1f109076490202914ef8aa0c2fb6127b4bc381fd556c0429bb41c5.json",
    "submission_id": "vsb_eb2bca0dbefa9ede",
    "submission_path": "records/submissions/sha256/eb2bca0dbefa9ede12f40c12a30fee8a3b285ff9e2bd756c6a641e7e1b4e7710.json",
    "verification_paths": [
        "records/verifications/sha256/4a3e2c9da58ddb4f3f62ee3720e911dde670f56282f7a2e96586a0b9f56b537f.json",
        "records/verifications/sha256/6e48991ad43b6b58f04545ca8bbad845c6672c99cda422be862d021f98405891.json",
        "records/verifications/sha256/ad088977f327c166da5131b5e67a0dc629c73ced74340333e7b7a8128022ff28.json",
    ],
    "decision_event_id": "vev_e045ff0592e193fa",
    "decision_event_path": ".vela/authority/events/vev_e045ff0592e193fa.json",
}

SUCCESSOR = {
    "claim_id": "vcl_3d4fd59554ccaa2b792b08abae16a8d0fe329d4901ad798fe05c6c7769c9966b",
    "claim_path": "records/claims/sha256/d5d77e7d96e390e0bf692d0abd44367eb06a0c6a61534e1c6654962d6c644776.json",
    "proposal_id": "vpr_9fa23f806717cd53",
    "proposal_path": "records/proposals/sha256/9fa23f806717cd537fa5e6ca811d1f0e951067cc1b42700c143dc45d5bf71e6d.json",
    "submission_id": "vsb_8280451ba4f13d4e",
    "submission_path": "records/submissions/sha256/8280451ba4f13d4ed06807e9613c3a370fba833209f07eda1c87074bcbfc2d60.json",
    "verification_paths": [
        "records/verifications/sha256/12d540b4879ed8afd6c16f41abb8c591b8be736f8a9aa73650f3ab09d1313da2.json",
        "records/verifications/sha256/1cad2a3d5590bbc24fbdaa6b5d36259a2e52302866a3ccecaace7dd764a7f1d0.json",
    ],
    "decision_event_id": "vev_fb652e14f2a9323f",
    "decision_event_path": ".vela/authority/events/vev_fb652e14f2a9323f.json",
    "applied_event_id": "vev_fa0607b365786fe7",
    "applied_event_path": ".vela/authority/events/vev_fa0607b365786fe7.json",
}

SOURCE_PATHS = (
    "evidence/erdos-321/definition-correspondence.v1.json",
    "evidence/erdos-321/definition-correspondence.v2.json",
    "evidence/erdos-321/translation/semantic-diff.v1.json",
    "evidence/erdos-321/translation/semantic-loss.v1.json",
    "evidence/erdos-321/translation/reference-annotations.v1.json",
    "evidence/erdos-321/terminal-variants/comparison.v0.1.json",
)

RELATION_CATEGORIES = {
    "affected": {"admissible_relation", "correspondence_structure", "fixed_statement_availability"},
    "unaffected": {"denotational_conclusion", "pinned_source_identity"},
    "unresolved": {"optimality_and_open_problem", "terminal_to_fixed_lower", "terminal_to_fixed_upper"},
    "incomplete_basis": {"dependency_cone", "fresh_kernel_rebuild"},
    "out_of_scope": {"erdos_887_pending_proposal", "other_repository_claims"},
}


class BuildError(ValueError):
    pass


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise BuildError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json_bytes(raw: bytes) -> dict[str, Any]:
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object)
    if not isinstance(value, dict):
        raise BuildError("JSON object required")
    return value


def load_json(path: Path) -> dict[str, Any]:
    return load_json_bytes(path.read_bytes())


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def jcs(value: Any) -> bytes:
    if value is None:
        return b"null"
    if value is True:
        return b"true"
    if value is False:
        return b"false"
    if isinstance(value, int) and not isinstance(value, bool):
        if abs(value) > 9_007_199_254_740_991:
            raise BuildError("integer exceeds interoperable JSON range")
        return str(value).encode("ascii")
    if isinstance(value, float):
        if not math.isfinite(value):
            raise BuildError("non-finite JSON number")
        raise BuildError("correction records do not admit floats")
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if isinstance(value, list):
        return b"[" + b",".join(jcs(item) for item in value) + b"]"
    if isinstance(value, dict):
        parts = []
        for key in sorted(value, key=lambda item: item.encode("utf-16-be", errors="surrogatepass")):
            if not isinstance(key, str):
                raise BuildError("JSON object keys must be strings")
            parts.append(jcs(key) + b":" + jcs(value[key]))
        return b"{" + b",".join(parts) + b"}"
    raise BuildError(f"unsupported JSON value: {type(value)!r}")


def root(value: dict[str, Any]) -> str:
    return "sha256:" + sha256(jcs(value))


def with_root(value: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(value)
    result["content_root_definition"] = "sha256 of RFC-8785 JSON after removing only content_root"
    result["content_root"] = root(result)
    return result


def reroot(value: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(value)
    result.pop("content_root", None)
    result["content_root"] = root(result)
    return result


def descriptor(path: str) -> dict[str, Any]:
    raw = (REPO / path).read_bytes()
    return {"path": path, "raw_sha256": "sha256:" + sha256(raw), "size": len(raw)}


def git(*arguments: str) -> bytes:
    completed = subprocess.run(["git", *arguments], cwd=REPO, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return completed.stdout


def historical_snapshot(stage: dict[str, Any]) -> dict[str, Any]:
    commit = stage["commit"]
    if git("rev-parse", f"{commit}^{{commit}}").decode().strip() != commit:
        raise BuildError(f"missing replay commit: {commit}")
    if git("show", "-s", "--format=%T", commit).decode().strip() != stage["tree"]:
        raise BuildError(f"replay tree drift: {stage['label']}")
    raw = git("show", f"{commit}:.vela/repository.json")
    repository = load_json_bytes(raw)
    if "sha256:" + sha256(raw) != stage["repository_root"]:
        raise BuildError(f"repository root drift: {stage['label']}")
    counts = {
        "accepted_claims": len(repository["accepted_claims"]),
        "artifacts": len(repository["artifacts"]),
        "pending_claims": len(repository["pending_claims"]),
        "proposal_withdrawals": len(repository.get("proposal_withdrawals", [])),
        "proposals": len(repository["proposals"]),
        "submissions": len(repository["submissions"]),
        "verifications": len(repository["verifications"]),
    }
    if counts != stage["counts"]:
        raise BuildError(f"replay counts drift: {stage['label']}")
    return {
        **stage,
        "command": "vela replay repository --json",
        "ok": True,
        "repository_id": repository["repository_id"],
        "repository_path_normalization": "absolute detached-worktree path replaced with repository",
        "schema": "vela.repository-verification.v3",
    }


def decode_verification(path: str) -> dict[str, Any]:
    wrapper = load_json(REPO / path)
    payload = load_json_bytes(base64.b64decode(wrapper["payload"], validate=True))
    return {
        **descriptor(path),
        "actor_id": payload["identity"]["actor_id"],
        "claim_id": payload["subject"]["claim_id"],
        "does_not_establish": payload["scope"]["does_not_establish"],
        "outcome": payload["outcome"],
        "property": payload["scope"]["property"],
        "proposal_id": payload["subject"]["proposal_id"],
    }


def validate_transition(spec: dict[str, Any], verdict: str) -> dict[str, Any]:
    claim = load_json(REPO / spec["claim_path"])
    proposal = load_json(REPO / spec["proposal_path"])
    event = load_json(REPO / spec["decision_event_path"])["content"]
    if claim["claim_id"] != spec["claim_id"] or proposal["subject"]["id"] != spec["claim_id"]:
        raise BuildError("claim/proposal identity drift")
    if event["kind"] != f"review.{verdict}" or event["payload"]["proposal_id"] != spec["proposal_id"]:
        raise BuildError("decision event drift")
    verifications = [decode_verification(path) for path in spec["verification_paths"]]
    if any(item["proposal_id"] != spec["proposal_id"] or item["claim_id"] != spec["claim_id"] for item in verifications):
        raise BuildError("verification subject drift")
    result = {
        "claim": {"id": spec["claim_id"], **descriptor(spec["claim_path"])},
        "decision": {
            "actor_type": event["actor"]["type"],
            "event_id": spec["decision_event_id"],
            "reason": event["reason"],
            "repository_after": event["payload"]["repository_after"],
            "repository_before": event["payload"]["repository_before"],
            "verdict": verdict,
            **descriptor(spec["decision_event_path"]),
        },
        "proposal": {"id": spec["proposal_id"], **descriptor(spec["proposal_path"])},
        "submission": {"id": spec["submission_id"], **descriptor(spec["submission_path"])},
        "verifications": verifications,
    }
    if "applied_event_path" in spec:
        applied = load_json(REPO / spec["applied_event_path"])["content"]
        if applied["kind"] != "claim.asserted" or applied["payload"]["claim_id"] != spec["claim_id"]:
            raise BuildError("applied event drift")
        result["applied_event"] = {"event_id": spec["applied_event_id"], **descriptor(spec["applied_event_path"])}
    return result


def build_document() -> dict[str, Any]:
    sources = [descriptor(path) for path in SOURCE_PATHS]
    semantic_diff = load_json(REPO / "evidence/erdos-321/translation/semantic-diff.v1.json")
    predecessor = validate_transition(PREDECESSOR, "rejected")
    successor = validate_transition(SUCCESSOR, "accepted")
    relations = [
        {"id": "admissible_relation", "category": "affected", "before": "Admissible was paired with the subset condition alone.", "after": "Admissible is the conjunction of subset and Valid conditions.", "basis": [SOURCE_PATHS[1], SOURCE_PATHS[2]]},
        {"id": "correspondence_structure", "category": "affected", "before": "Four independent pairwise identities.", "after": "Three distinct correspondences plus a conjunction that reuses one.", "basis": [SOURCE_PATHS[0], SOURCE_PATHS[1], SOURCE_PATHS[2]]},
        {"id": "fixed_statement_availability", "category": "affected", "before": "No fixed formal statement was reported in the file.", "after": "The open declarations remain placeholders, while fixed solved lower and upper variants are present.", "basis": [SOURCE_PATHS[1], SOURCE_PATHS[2]]},
        {"id": "denotational_conclusion", "category": "unaffected", "before": "extremalSize N = R N", "after": "extremalSize N = R N", "basis": [SOURCE_PATHS[1], SOURCE_PATHS[2]]},
        {"id": "pinned_source_identity", "category": "unaffected", "before": "Pinned Formal Conjectures and Star Fleet source commits.", "after": "The same pinned commits and retained source snapshots.", "basis": [SOURCE_PATHS[3], SOURCE_PATHS[4]]},
        {"id": "optimality_and_open_problem", "category": "unresolved", "before": "Not established.", "after": "Still not established; Erdős 321 remains open.", "basis": [SOURCE_PATHS[1], SOURCE_PATHS[5]]},
        {"id": "terminal_to_fixed_lower", "category": "unresolved", "before": "Not identified.", "after": "Identified and compared structurally; implication remains unproved.", "basis": [SOURCE_PATHS[2], SOURCE_PATHS[5]]},
        {"id": "terminal_to_fixed_upper", "category": "unresolved", "before": "Not identified.", "after": "Identified and compared structurally; implication remains unproved.", "basis": [SOURCE_PATHS[2], SOURCE_PATHS[5]]},
        {"id": "dependency_cone", "category": "incomplete_basis", "before": "No rooted transitive proof-dependency slice.", "after": "The source comparison still does not establish a complete transitive dependency cone.", "basis": [SOURCE_PATHS[3], SOURCE_PATHS[5]]},
        {"id": "fresh_kernel_rebuild", "category": "incomplete_basis", "before": "Recorded CI attestation only.", "after": "No fresh rebuild was part of the historical correction Decision.", "basis": [SOURCE_PATHS[1]]},
        {"id": "erdos_887_pending_proposal", "category": "out_of_scope", "before": "Absent from the historical correction.", "after": "A later unrelated pending proposal; it does not alter this slice.", "basis": []},
        {"id": "other_repository_claims", "category": "out_of_scope", "before": "Not inspected.", "after": "Not inspected.", "basis": []},
    ]
    document = {
        "schema": "vela.math.correction-impact.v1",
        "authority_effect": "none",
        "case": "erdos:321",
        "scope": {
            "definition": "The two Erdős 321 correspondence records, their exact retained sources, the current-authority-generation rejection and acceptance transitions, and the terminal-to-fixed-variant comparison.",
            "coverage": "Every relation named in relation_slice is classified exactly once. No transitive Repository dependency graph is claimed.",
            "losses": ["The pre-0.972 Claim IDs in semantic-diff.v1 remain source-history identifiers and are not treated as current Standing.", "No fresh Lean rebuild or complete dependency cone was part of the historical correction Decision."],
        },
        "source_lineage": {
            "archived_predecessor_claim_id": semantic_diff["correction_impact"]["predecessor_claim_id"],
            "archived_successor_claim_id": semantic_diff["correction_impact"]["successor_claim_id"],
            "current_authority_generation": {"rejected_predecessor": predecessor, "accepted_successor": successor},
            "sources": sources,
        },
        "replay": {
            "reader": {"core_commit": CORE_READER_COMMIT, "version": CORE_READER_VERSION},
            "normalization": "The replay command's absolute worktree path is replaced by repository; all other reported fields are retained.",
            "stages": [historical_snapshot(stage) for stage in REPLAY_STAGES],
        },
        "relation_slice": relations,
        "repair_obligation": {
            "status": "open",
            "statement": "Construct and kernel-check explicit bridges between the real-log terminal coordinates and each Nat.log fixed-variant hypothesis before asserting either implication.",
            "basis": SOURCE_PATHS[5],
            "standing_effect": "none",
        },
        "nonclaims": [
            "This source-local package is not a Vela Claim, Verification, Decision, Event, or Standing transition.",
            "The historical human Decisions are reported, not recreated.",
            "The corrected Claim does not resolve Erdős 321 or establish optimality.",
            "An unresolved or incomplete-basis relation is not an unaffected relation.",
            "The open repair obligation has not been verified or decided.",
        ],
    }
    return with_root(document)


def validate_document(document: dict[str, Any]) -> None:
    if document.get("schema") != "vela.math.correction-impact.v1" or document.get("authority_effect") != "none":
        raise BuildError("schema or authority effect drift")
    candidate = copy.deepcopy(document)
    observed_root = candidate.pop("content_root", None)
    if observed_root != root(candidate):
        raise BuildError("content root drift")
    observed = {category: set() for category in RELATION_CATEGORIES}
    for relation in document.get("relation_slice", []):
        category, identifier = relation.get("category"), relation.get("id")
        if category not in observed or identifier in observed[category]:
            raise BuildError("relation category or identity drift")
        observed[category].add(identifier)
    if observed != RELATION_CATEGORIES:
        raise BuildError("bounded relation inventory drift")
    expected = build_document()
    if document != expected:
        raise BuildError("correction-impact document does not match retained sources")


def rendered(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    document = build_document()
    validate_document(document)
    raw = rendered(document)
    if arguments.check:
        if OUTPUT.read_bytes() != raw:
            raise BuildError("generated correction-impact record drift")
    else:
        OUTPUT.write_bytes(raw)
    print(document["content_root"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
