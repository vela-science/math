#!/usr/bin/env python3
"""Build the one source-owned, non-authoritative Math Campaign case record."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / "evidence/formal-conjectures/work-offers"
INDEX_PATH = WORK / "index.v1.json"
LIFECYCLE_PATH = WORK / "lifecycle/erdos-887-pr-1237-fidelity-repair.v1.json"
OUTPUT_PATH = Path(__file__).resolve().parent / "erdos-887-source-fidelity-pilot.v1.json"


class CampaignError(ValueError):
    pass


def _reject_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise CampaignError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load(path: Path):
    raw = path.read_bytes()
    if not raw.endswith(b"\n") or raw.endswith(b"\n\n"):
        raise CampaignError(f"{path} must have exactly one trailing LF")
    value = json.loads(raw, object_pairs_hook=_reject_duplicates)
    if _framed(value) != raw:
        raise CampaignError(f"{path} is not canonical JSON")
    return value, raw


def _canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()


def _framed(value) -> bytes:
    return _canonical(value) + b"\n"


def _root(value, field: str) -> str:
    body = dict(value)
    body.pop(field, None)
    return "sha256:" + hashlib.sha256(_canonical(body)).hexdigest()


def _raw_root(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def build():
    index, index_raw = _load(INDEX_PATH)
    lifecycle, lifecycle_raw = _load(LIFECYCLE_PATH)
    target = index["targets"][0]
    if target["presence"] != "superseded" or target["next_command"] is not None:
        raise CampaignError("Campaign requires the exact terminal Work Offer")
    if lifecycle["lifecycle_root"] != target["lifecycle"]["lifecycle_root"]:
        raise CampaignError("Work Offer lifecycle root drift")
    if lifecycle["completion"]["contract_status"] != "not_satisfied":
        raise CampaignError("Campaign must preserve the Completion Contract gap")
    if lifecycle["completion"]["review"]["reviewer"]["kind"] != "ai_model":
        raise CampaignError("Campaign must retain the attributed AI-model review")

    campaign = {
        "authority_effect": "none",
        "campaign_id": "math:erdos-887-source-fidelity-pilot",
        "campaign_root_definition": "sha256 of canonical JSON after removing only campaign_root",
        "decision_domains": lifecycle["decisions"],
        "mechanism": {
            "adjudication": "Exact Completion Contract evidence and separately attributed domain Decisions",
            "experimental": True,
            "failure_modes": [
                "A historical actor-class restriction can make sound work fail its issued contract.",
                "Scientific admission can be mistaken for program completion.",
                "Repository-root churn can falsely reissue already-addressed work.",
            ],
            "kind": "staged_open_work",
            "review_requirements": {
                "eligible_performer_classes": ["agent", "human"],
                "independence_must_be_declared": True,
                "method_and_exact_inputs_required": True,
                "quality_rank_from_performer_class": False,
            },
            "scope": "one exact source-fidelity repair",
        },
        "nonclaims": [
            "This Campaign is a source-local product record, not a Protocol object or scientific authority.",
            "AI and human performer classes are provenance, not an evidentiary ranking.",
            "The accepted scientific Decision does not establish program completion, reward eligibility, deployment, or Erdős problem 887.",
            "This single case does not establish that staged open work is effective or generalizable.",
            "This closed Campaign creates no payment, allocation, credential, or authority for the separately issued successor Work Offer.",
        ],
        "outcomes": {
            "downstream": {"status": "not_measured"},
            "epistemic": {
                "scientific_decision": "accepted",
                "statement_fidelity_review": "pass",
            },
            "process": {
                "campaign_state": "closed_with_contract_gap",
                "completion_contract": "not_satisfied",
                "work_offer": "superseded",
            },
        },
        "problem": {
            "namespace": "erdos-problems",
            "number": "887",
            "target_id": "erdos:887",
        },
        "remap": lifecycle["remap"],
        "resources": {
            "allocations": [],
            "compute": "bring_your_own",
            "credentials": "none_retained",
            "public_inputs": True,
            "reward_commitment": "none",
        },
        "schema": "vela.math.source-campaign.v1",
        "state": "closed_with_contract_gap",
        "title": "Erdős 887 source-fidelity repair pilot",
        "work_offer": {
            "index": {
                "index_root": index["index_root"],
                "path": str(INDEX_PATH.relative_to(ROOT)),
                "raw_sha256": _raw_root(index_raw),
            },
            "lifecycle": {
                "lifecycle_root": lifecycle["lifecycle_root"],
                "path": str(LIFECYCLE_PATH.relative_to(ROOT)),
                "raw_sha256": _raw_root(lifecycle_raw),
            },
            "packet_root": target["packet"]["packet_root"],
            "presence": target["presence"],
        },
    }
    campaign["campaign_root"] = _root(campaign, "campaign_root")
    return campaign, _framed(campaign)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    campaign, raw = build()
    if args.check:
        if OUTPUT_PATH.read_bytes() != raw:
            raise CampaignError("Campaign record drift; run build.py")
    else:
        OUTPUT_PATH.write_bytes(raw)
    print(json.dumps({"campaign_root": campaign["campaign_root"], "ok": True}, separators=(",", ":")))


if __name__ == "__main__":
    main()
