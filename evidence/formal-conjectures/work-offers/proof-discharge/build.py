#!/usr/bin/env python3
"""Build the bounded Erdős 887 proof-discharge Work Offer."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]
EXECUTION_DIR = HERE / "execution"
PACKET_PATH = HERE.parent / "packets/erdos-887-proof-discharge.v1.json"

TARGET_ID = "erdos:887:proof-discharge"
MATH_COMMIT = "c654010cfc7eb09d0f93f68c6792982d38f28b99"
MATH_TREE = "b1353e9abe6435880238ccaad574f4b9a3c3ea74"
REPOSITORY_ROOT = "sha256:ae41be4a91265d91967344459fa12583314ec05c5a0ebc74d8b0136195879511"
BASIS_CLAIM_ID = "vcl_8407166fa41b4c27891a6c71630e4160d0347257aa1126fb892247b29076f85c"
BASIS_CLAIM_ROOT = "sha256:c445d8df3e41982ccb1d0628fc89060097f5a2a10040d73a8eb78cde226beea1"
SOURCE_COMMIT = "158727e43d3be335f902ac7ef6b9beb819e38c9d"
SOURCE_TREE = "80d17febad5b2f724165561f5af74e19156e34d5"
SOURCE_BLOB = "21c7d60d90d013de645b46f318980ba4b4a5d9f7"
SOURCE_RAW_SHA256 = "sha256:c2225a17de2f5210dbdb010bf7e915940d6776daf4ba4220d59b3002856a429a"
SOURCE_PATH = "FormalConjectures/ErdosProblems/887.lean"
REPOSITORY_ID = "8115c538-7688-40b7-ab75-3c4765bf3c19"
ORIGIN_ID = "vro_229ce0a08217da5e"
PROJECTION_PATH = "evidence/formal-conjectures/source-adapter/projection.v1.json"
PROJECTION_ROOT = "sha256:1a90cbe1732e21e730753a12e6b3b1ecbd3e0019a287a5ba001c9a9fdccf881b"
SOURCE_RECORD_ROOT = "sha256:2c3cddfa45773c96ec937c1710f0dbee550775f7d33dd324bee73a4152c45dde"


class ProofOfferError(ValueError):
    """Raised when the generated proof Work Offer is inconsistent."""


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


def _write(path: Path, value: dict[str, Any]) -> bytes:
    raw = _canonical_bytes(value) + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return raw


def _descriptor(path: Path, value: dict[str, Any], root_field: str) -> dict[str, Any]:
    raw = _canonical_bytes(value) + b"\n"
    return {
        "schema": value["schema"],
        "path": str(path.relative_to(REPO_ROOT)),
        "size": len(raw),
        "raw_sha256": _raw_root(raw),
        "root": value[root_field],
    }


def build_profile() -> dict[str, Any]:
    profile: dict[str, Any] = {
        "schema": "vela.math.proof-attempt-producer-profile.v1",
        "authority_effect": "none",
        "target_id": TARGET_ID,
        "performer_policy": {
            "eligible_classes": ["agent", "human", "organization", "tool"],
            "class_is_quality_rank": False,
            "required_provenance": [
                "attributed actor or tool identity",
                "model, provider, runtime, and tool versions when applicable",
                "source-owned session or checkpoint reference when available",
                "exact inputs and produced artifacts",
                "elapsed time and bounded resource use",
                "shared dependencies and prior exposure",
            ],
        },
        "execution": {
            "source_access": "public",
            "network": "allowed only for exact public source and dependency acquisition before the retained offline check",
            "credentials": "none required or retained",
            "large_artifacts": "external by rooted locator; do not commit caches or build directories",
            "default_bound": {
                "wall_clock_minutes": 90,
                "paid_external_compute": False,
                "upstream_writes": False,
            },
        },
        "permitted_outputs": [
            "kernel_checked_proof_candidate",
            "bounded_partial_result",
            "bounded_obstruction_or_counterexample_candidate",
            "not_proved_within_declared_bounds",
            "execution_error",
        ],
        "nonclaims": [
            "A performer class does not determine evidentiary quality or authority.",
            "A bounded unsuccessful attempt does not establish that Erdős problem 887 is false or impossible.",
            "A Lean build using sorryAx does not discharge the proof obligation.",
            "This activity profile grants no Repository authority and authorizes no upstream action.",
        ],
        "profile_root_definition": "sha256 of canonical JSON after removing only profile_root",
    }
    profile["profile_root"] = _root(profile)
    return profile


def build_contract() -> dict[str, Any]:
    contract: dict[str, Any] = {
        "schema": "vela.math.proof-attempt-result-contract.v1",
        "authority_effect": "none",
        "target_id": TARGET_ID,
        "terminal_states": {
            "proved_candidate": {
                "requirements": [
                    "A patch replaces only the in-scope proof placeholder or adds directly required supporting declarations.",
                    "The exact patched source builds under the retained toolchain and dependency inventory.",
                    "#print axioms for Erdos887.erdos_887.parts.ii contains no sorryAx.",
                    "The result retains stdout, stderr, command transcript, dependency inventory, source patch, and exact source/result roots.",
                ],
                "does_not_establish": [
                    "Upstream acceptance, Vela Verification, a Repository Decision, or Math Standing.",
                    "Novelty, optimality, or proof of any out-of-scope Erdős 887 variant.",
                ],
            },
            "bounded_partial_result": {
                "requirements": [
                    "Retain each exact proved lemma, failed goal, and remaining obligation.",
                    "State whether the partial result reduces the target under explicit assumptions or merely explores a tactic path.",
                ],
            },
            "bounded_obstruction_or_counterexample_candidate": {
                "requirements": [
                    "Bind the exact construction, execution method, checked range or proof, and scope.",
                    "Do not promote finite search or a candidate obstruction to a universal mathematical claim.",
                ],
            },
            "not_proved_within_declared_bounds": {
                "requirements": [
                    "Retain the attempted methods, terminal goals, resource bound, and reusable findings.",
                    "Do not claim impossibility, falsehood, or exhaustion beyond the declared search space.",
                ],
            },
            "execution_error": {
                "requirements": [
                    "Retain the exact failed command, environment identity, exit status, stdout, and stderr.",
                    "Keep unavailable, unsupported, and failed distinct.",
                ],
            },
        },
        "required_result_fields": [
            "schema",
            "authority_effect",
            "target_id",
            "packet_root",
            "execution_binding",
            "producer",
            "terminal_state",
            "declared_bounds",
            "source_roots",
            "artifacts",
            "findings",
            "remaining_obligations",
            "nonclaims",
            "result_root",
        ],
        "canonical_framing": "canonical JSON plus exactly one trailing LF",
        "maximum_result_bytes": 131072,
        "result_contract_root_definition": "sha256 of canonical JSON after removing only result_contract_root",
    }
    contract["result_contract_root"] = _root(contract)
    return contract


def build_capsule(contract: dict[str, Any]) -> dict[str, Any]:
    capsule: dict[str, Any] = {
        "schema": "vela.math.proof-attempt-verifier-capsule.v1",
        "authority_effect": "none",
        "target_id": TARGET_ID,
        "subject": {
            "repository": "https://github.com/google-deepmind/formal-conjectures",
            "commit": SOURCE_COMMIT,
            "tree": SOURCE_TREE,
            "path": SOURCE_PATH,
            "git_blob_oid": SOURCE_BLOB,
            "raw_sha256": SOURCE_RAW_SHA256,
            "declaration": "Erdos887.erdos_887.parts.ii",
        },
        "checks": [
            "Refuse source commit, tree, path, blob, raw SHA-256, packet, profile, capsule, or result-contract drift.",
            "Apply the retained patch to a clean exact source checkout and refuse path escape or undeclared source mutation.",
            "Run the retained build and target check with exact toolchain and dependency identities.",
            "For proved_candidate, inspect #print axioms and refuse any result containing sorryAx.",
            "Require the declared terminal state to match retained command results and artifacts.",
            "Require every retained artifact path and raw digest to resolve inside the result package.",
        ],
        "review_requirements": {
            "proof_scope": "separate attributed review of the exact proof term, assumptions, axiom report, and target match",
            "independence": "declare actor separation, prior exposure, shared model/provider/runtime/toolchain, and evidence reuse",
            "authority": "review and build results have no authority effect until separately recorded under Repository policy",
        },
        "result_schema": "vela.math.proof-attempt-result.v1",
        "result_contract_root": contract["result_contract_root"],
        "verifier_capsule_root_definition": "sha256 of canonical JSON after removing only verifier_capsule_root",
    }
    capsule["verifier_capsule_root"] = _root(capsule)
    return capsule


def build_packet(
    profile: dict[str, Any],
    contract: dict[str, Any],
    capsule: dict[str, Any],
) -> dict[str, Any]:
    packet: dict[str, Any] = {
        "schema": "vela.math.proof-discharge-target-packet.v1",
        "authority_effect": "none",
        "target": {
            "id": TARGET_ID,
            "problem": {"namespace": "erdos-problems", "number": 887},
            "source_fixture_id": "fidelity-erdos-887-1237",
            "title": "Attempt the corrected Erdős 887 proof obligation",
        },
        "objective": "Within the declared resource bound, attempt to discharge the exact proof placeholder for Erdos887.erdos_887.parts.ii, or return a rooted partial, obstruction, negative attempt, or execution-error record that makes the remaining obligation more precise.",
        "repository": {
            "repository_id": REPOSITORY_ID,
            "origin_id": ORIGIN_ID,
            "repository_root": REPOSITORY_ROOT,
            "source_commit": MATH_COMMIT,
            "source_tree": MATH_TREE,
        },
        "source": {
            "repository": "https://github.com/google-deepmind/formal-conjectures",
            "projection_path": PROJECTION_PATH,
            "projection_root": PROJECTION_ROOT,
            "record_root": SOURCE_RECORD_ROOT,
            "head_commit": SOURCE_COMMIT,
            "head_tree": SOURCE_TREE,
            "path": SOURCE_PATH,
            "git_blob_oid": SOURCE_BLOB,
            "raw_sha256": SOURCE_RAW_SHA256,
            "declaration": "Erdos887.erdos_887.parts.ii",
            "source_status": "research_open",
        },
        "basis": {
            "math": {
                "repository": "https://github.com/vela-science/math",
                "commit": MATH_COMMIT,
                "tree": MATH_TREE,
                "repository_root": REPOSITORY_ROOT,
                "claim_id": BASIS_CLAIM_ID,
                "claim_root": BASIS_CLAIM_ROOT,
                "obligation_source": "evidence/formal-conjectures/work-offers/lifecycle/erdos-887-pr-1237-fidelity-repair.v1.json#remap",
            },
            "formal_conjectures": {
                "repository": "https://github.com/google-deepmind/formal-conjectures",
                "commit": SOURCE_COMMIT,
                "tree": SOURCE_TREE,
                "path": SOURCE_PATH,
                "git_blob_oid": SOURCE_BLOB,
                "raw_sha256": SOURCE_RAW_SHA256,
                "declaration": "Erdos887.erdos_887.parts.ii",
                "source_status": "research_open",
            },
        },
        "scope": {
            "included": [
                "The exact parts.ii declaration and directly required supporting lemmas.",
                "A kernel-checkable proof attempt under the exact retained Formal Conjectures toolchain.",
                "Bounded mathematical and formal-search observations that remain useful if the proof is not discharged.",
            ],
            "excluded": [
                "Erdos887.erdos_887.parts.i and the Rosenfeld variants except as explicitly cited context.",
                "Any claim that the open problem is solved without a no-sorry kernel-checked proof of parts.ii.",
                "Upstream comments, issues, reviews, branches, or pull requests.",
                "Vela Verification, Decision, Event, or Standing changes.",
            ],
        },
        "completion_contract": {
            "success": "A proved_candidate satisfying every result-contract requirement and ready for separate attributed review.",
            "useful_non_success": "A bounded partial, obstruction, negative attempt, or execution-error result satisfying its terminal-state requirements.",
            "no_result": "No result may be inferred from elapsed time, missing output, or an interrupted process.",
        },
        "custody": {
            "access": "public",
            "participant_private_data_allowed": False,
            "proof_artifacts_may_be_public": True,
        },
        "execution_components": {
            "authority_effect": "none",
            "producer_profile": _descriptor(EXECUTION_DIR / "producer-profile.v1.json", profile, "profile_root"),
            "verifier_capsule": _descriptor(EXECUTION_DIR / "verifier-capsule.v1.json", capsule, "verifier_capsule_root"),
            "result_contract": _descriptor(EXECUTION_DIR / "result-contract.v1.json", contract, "result_contract_root"),
        },
        "nonclaims": [
            "This Work Offer is a source-owned coordination record, not a Vela protocol object.",
            "The problem is open; issuance does not predict that this bounded attempt will solve it.",
            "An attributed agent and an attributed human are eligible under the same evidence and provenance requirements.",
            "A result, review, Git commit, or upstream merge is not a Repository Decision or Math Standing.",
        ],
        "packet_root_definition": "sha256 of canonical JSON after removing only packet_root",
    }
    packet["packet_root"] = _root(packet)
    return packet


def build() -> tuple[tuple[Path, dict[str, Any], str], ...]:
    profile = build_profile()
    contract = build_contract()
    capsule = build_capsule(contract)
    packet = build_packet(profile, contract, capsule)
    return (
        (EXECUTION_DIR / "producer-profile.v1.json", profile, "profile_root"),
        (EXECUTION_DIR / "result-contract.v1.json", contract, "result_contract_root"),
        (EXECUTION_DIR / "verifier-capsule.v1.json", capsule, "verifier_capsule_root"),
        (PACKET_PATH, packet, "packet_root"),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--print-roots", action="store_true")
    args = parser.parse_args()
    generated = build()
    for path, value, _ in generated:
        raw = _canonical_bytes(value) + b"\n"
        if args.check:
            if not path.exists() or path.read_bytes() != raw:
                raise SystemExit(f"{path.relative_to(REPO_ROOT)} does not match generated bytes")
        else:
            _write(path, value)
    if args.print_roots:
        print(json.dumps({root_field: value[root_field] for _, value, root_field in generated}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
