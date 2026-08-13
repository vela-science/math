#!/usr/bin/env python3
"""Build the current Erdős 321 repair remap without rewriting historical evidence."""

from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
OUTPUT = HERE / "correction-remap.v1.json"
PRODUCER = "agent:codex-terminal-bridge-disposition"
CLAIM_ID = "vcl_c2934683423e1961929339fdef54a49a92b268d329992b79a31b336608427cfc"
PROPOSAL_ID = "vpr_4cce463df6f23e2b"
EXPECTED_CLAIM = "At the exact retained Erdős 321 source revisions, the terminal theorem and structural comparison do not establish implication to either fixed Nat.log variant."
EXPECTED_DISPOSITION_CLAIM = "At the exact retained source revisions, the terminal theorem and structural comparison do not establish implication to either fixed Nat.log variant."
PATHS = {
    "prior_impact": "evidence/erdos-321/correction-impact/correction-impact.v1.json",
    "disposition": "evidence/erdos-321/terminal-variants/repair-disposition/repair-disposition.v1.json",
    "claim": "records/claims/sha256/d344ca99e2d23e01fbe730e5333fc834fe15e710215ad595c1abe4cd83a04a13.json",
    "proposal": "records/proposals/sha256/4cce463df6f23e2b31f7ac329bc82af8ca096bf96b564cf2f3a461950b0f3aea.json",
    "submission": "records/submissions/sha256/c050f50fe0f91bd278e7470525fdcd0e6ed71b8c713cedb0246c13adcc566ca8.json",
    "producer_verification": "records/verifications/sha256/223429dabd56a629bfe7737cffdf97cb099e3fd060691b3d0e35a278fb5ef225.json",
    "independent_verification": "records/verifications/sha256/203ca47346ff9282392265188f6f6e7c6fc84d1d7fca11b89f295913c35b9a1c.json",
    "decision": ".vela/authority/events/vev_b9917b1940133d68.json",
    "applied": ".vela/authority/events/vev_072db31131b6c541.json",
}


class RemapError(ValueError):
    pass


def load(path: str) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in items:
            if key in value:
                raise RemapError(f"duplicate JSON key in {path}: {key}")
            value[key] = item
        return value

    value = json.loads((REPO / path).read_text(), object_pairs_hook=pairs)
    if not isinstance(value, dict):
        raise RemapError(f"object required: {path}")
    return value


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def rooted(value: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(value)
    result["content_root_definition"] = "sha256 of canonical JSON after removing only content_root"
    result["content_root"] = "sha256:" + hashlib.sha256(canonical(result)).hexdigest()
    return result


def descriptor(path: str) -> dict[str, Any]:
    raw = (REPO / path).read_bytes()
    return {"path": path, "raw_sha256": "sha256:" + hashlib.sha256(raw).hexdigest(), "size": len(raw)}


def verification(path: str) -> dict[str, Any]:
    wrapper = load(path)
    payload = json.loads(base64.b64decode(wrapper["payload"], validate=True))
    if payload["subject"]["proposal_id"] != PROPOSAL_ID or payload["subject"]["claim_id"] != CLAIM_ID:
        raise RemapError("Verification subject drift")
    if payload["scope"]["property"] != "terminal_bridge_scope" or payload["outcome"] != "pass":
        raise RemapError("Verification result drift")
    independent = PRODUCER in payload["independence"]["declared_independent_of"]
    return {
        **descriptor(path),
        "actor_class": payload["identity"]["actor_class"],
        "actor_id": payload["identity"]["actor_id"],
        "independent_of_producer": independent,
        "method": payload["method"],
        "outcome": payload["outcome"],
        "property": payload["scope"]["property"],
        "shared_dependencies": payload["independence"]["shared_dependencies"],
    }


def build() -> dict[str, Any]:
    prior = load(PATHS["prior_impact"])
    disposition = load(PATHS["disposition"])
    claim = load(PATHS["claim"])
    proposal = load(PATHS["proposal"])
    submission_wrapper = load(PATHS["submission"])
    submission = json.loads(base64.b64decode(submission_wrapper["payload"], validate=True))
    decision = load(PATHS["decision"])["content"]
    applied = load(PATHS["applied"])["content"]
    producer_verification = verification(PATHS["producer_verification"])
    independent_verification = verification(PATHS["independent_verification"])
    if prior["repair_obligation"]["status"] != "open":
        raise RemapError("historical repair obligation drift")
    if disposition["disposition"]["status"] != "unsupported_by_retained_basis":
        raise RemapError("repair disposition drift")
    if claim["claim_id"] != CLAIM_ID or proposal["subject"]["id"] != CLAIM_ID:
        raise RemapError("Claim or Proposal drift")
    if submission["claim"]["assertion"] != EXPECTED_CLAIM or disposition["disposition"]["claim"] != EXPECTED_DISPOSITION_CLAIM:
        raise RemapError("Submission assertion drift")
    if producer_verification["independent_of_producer"]:
        raise RemapError("producer-context review independence drift")
    if not independent_verification["independent_of_producer"]:
        raise RemapError("independent review requirement drift")
    if decision["kind"] != "review.accepted" or decision["payload"]["proposal_id"] != PROPOSAL_ID:
        raise RemapError("Decision drift")
    performer = decision["payload"]["decision_performer"]
    if performer["actor_class"] != "agent" or performer["actor_id"] != "agent:codex-terminal-repair-decision":
        raise RemapError("Decision performer drift")
    if applied["kind"] != "claim.asserted" or applied["payload"]["claim_id"] != CLAIM_ID:
        raise RemapError("applied Claim event drift")
    return rooted({
        "schema": "vela.math.erdos321-terminal-bridge-remap.v1",
        "authority_effect": "none",
        "case": "erdos:321",
        "historical_impact": {**descriptor(PATHS["prior_impact"]), "content_root": prior["content_root"]},
        "repair_disposition": {**descriptor(PATHS["disposition"]), "content_root": disposition["content_root"]},
        "accepted_scope_claim": {
            "claim": {**descriptor(PATHS["claim"]), "id": CLAIM_ID},
            "proposal": {**descriptor(PATHS["proposal"]), "id": PROPOSAL_ID},
            "submission": descriptor(PATHS["submission"]),
            "verifications": [producer_verification, independent_verification],
            "decision": {
                **descriptor(PATHS["decision"]),
                "actor_class": performer["actor_class"],
                "actor_id": performer["actor_id"],
                "authority_principal_id": performer["authority_principal_id"],
                "reason": decision["reason"],
                "repository_before": decision["payload"]["repository_before"],
                "repository_after": decision["payload"]["repository_after"],
                "session_ref": performer["session_ref"],
            },
            "applied_event": descriptor(PATHS["applied"]),
        },
        "relation_remap": [
            {"id": "terminal_to_fixed_lower", "prior": "unresolved", "current": "unresolved", "reason": "The accepted negative scope Claim establishes that the retained basis does not prove the implication; it does not supply a bridge theorem."},
            {"id": "terminal_to_fixed_upper", "prior": "unresolved", "current": "unresolved", "reason": "The accepted negative scope Claim establishes that the retained basis does not prove the implication; it does not supply a bridge theorem."},
        ],
        "repair_obligation": {
            "prior_status": "open",
            "current_status": "closed_unsupported_by_retained_basis",
            "closure_claim_id": CLAIM_ID,
            "reopen_only_if": "A rooted common-source port or new retained evidence supplies an explicit bridge candidate for kernel checking.",
            "standing_effect": "none",
        },
        "nonclaims": [
            "Closing the bounded investigation does not prove that no bridge exists.",
            "Both terminal-to-fixed relations remain unresolved rather than unaffected.",
            "The source-local remap reports the accepted Claim and has no authority effect of its own.",
            "Actor class is provenance; the independent Verification and Decision are evaluated by method, scope, independence, and Repository authority.",
        ],
    })


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    document = build()
    raw = json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True).encode() + b"\n"
    if args.check:
        if OUTPUT.read_bytes() != raw:
            raise RemapError("correction remap drift")
    else:
        OUTPUT.write_bytes(raw)
    print(document["content_root"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
