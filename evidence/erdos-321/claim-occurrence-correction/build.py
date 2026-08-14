#!/usr/bin/env python3
"""Build and validate the non-authoritative MATH-CLAIM-01 preparation packet."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
from typing import Any


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OCCURRENCE = HERE / "occurrence-resolution.v1.json"
PLAN = HERE / "correction-plan.v1.json"
WEB_PATH = "packages/observatory-data/config/problem-resolution.v1.json"
WEB_COMMIT = "1559f26fae98d5a0bfbfd905d33b0771c73c4333"
WEB_TREE = "0495f8945903380e53891d14268c8d07fd24d697"
WEB_BLOB = "9d5162f1b77e83cb22c2aaf1256ef8734bb47750"
WEB_RAW_SHA256 = "7b349ae3dbca4a33efa7e9810c6f0e454589b6239f83ad16a22eabfd449a80c7"
WEB_CONFIG_ROOT = (
    "sha256:a9d6787719c5c8069a9e14ade0f5a62975410272e6cd1583865b282d1d8669dd"
)
REPOSITORY_ROOT = (
    "sha256:ae41be4a91265d91967344459fa12583314ec05c5a0ebc74d8b0136195879511"
)
ACCEPTED_REPOSITORY_ROOT = (
    "sha256:0e24fa1b13d7eda7b4e809564ec414eb1fda09f5dcf9aa8a6bcd6ae69ac96197"
)
TARGET_ID = "vcl_3d4fd59554ccaa2b792b08abae16a8d0fe329d4901ad798fe05c6c7769c9966b"
TARGET_ROOT = "sha256:d5d77e7d96e390e0bf692d0abd44367eb06a0c6a61534e1c6654962d6c644776"
TARGET_PATH = "records/claims/sha256/d5d77e7d96e390e0bf692d0abd44367eb06a0c6a61534e1c6654962d6c644776.json"
SUCCESSOR_ID = "vcl_a618b77ab0f6a4b5b186133e37af555a22c6acb71a4746bab0b144b8973668a6"
SUCCESSOR_ROOT = (
    "sha256:8ea9f7150743ba0919a9d40aa0e632e1171b0a2ecdce20e76d6068e1427a647e"
)
PROPOSAL_ID = "vpr_58c2f9ae80498879"
SUBMISSION_ID = "vsb_e1025b3c5f4b2375"
FC_COMMIT = "59f30aa314ba225fcd9268723ce8291616df1ab0"
LEAN_COMMIT = "a8c2872a27cf8d11cf6744ca4a2c5b49ace5fea0"
CONTENT_ROOT_DEFINITION = "sha256 of RFC-8785 JSON after removing only content_root"
SHA256 = re.compile(r"sha256:[0-9a-f]{64}\Z")


class PacketError(ValueError):
    pass


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PacketError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json_bytes(raw: bytes) -> dict[str, Any]:
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object)
    if not isinstance(value, dict):
        raise PacketError("JSON object required")
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
            raise PacketError("integer exceeds interoperable JSON range")
        return str(value).encode("ascii")
    if isinstance(value, float):
        if not math.isfinite(value):
            raise PacketError("non-finite JSON number")
        raise PacketError("packet does not admit floats")
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
    if isinstance(value, list):
        return b"[" + b",".join(jcs(item) for item in value) + b"]"
    if isinstance(value, dict):
        parts: list[bytes] = []
        for key in sorted(
            value, key=lambda item: item.encode("utf-16-be", errors="surrogatepass")
        ):
            if not isinstance(key, str):
                raise PacketError("JSON object keys must be strings")
            parts.append(jcs(key) + b":" + jcs(value[key]))
        return b"{" + b",".join(parts) + b"}"
    raise PacketError(f"unsupported JSON value: {type(value)!r}")


def rooted(value: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(value)
    result["content_root_definition"] = CONTENT_ROOT_DEFINITION
    result["content_root"] = "sha256:" + sha256(jcs(result))
    return result


def reroot(value: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(value)
    result.pop("content_root", None)
    result["content_root"] = "sha256:" + sha256(jcs(result))
    return result


def rendered(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def descriptor(path: str) -> dict[str, Any]:
    raw = (REPO / path).read_bytes()
    return {"path": path, "raw_sha256": "sha256:" + sha256(raw), "size": len(raw)}


def exact_reference(
    *,
    system: str,
    object_kind: str,
    identifier: str,
    revision: str,
    digest: str,
    size: int,
    media_type: str,
    selector_kind: str,
    selector_value: str,
    locator: str,
    mutable: bool,
) -> dict[str, Any]:
    return {
        "schema": "vela.exact-reference.v0.1",
        "native_identity": {
            "system": system,
            "object_kind": object_kind,
            "identifier": identifier,
        },
        "revision": {"kind": "git_commit", "value": revision},
        "content_fixity": {
            "media_type": media_type,
            "digest": "sha256:" + digest,
            "size": size,
        },
        "selector": {"kind": selector_kind, "value": selector_value},
        "locator": {
            "uri": locator,
            "mutable": mutable,
            "authentication": "public",
        },
    }


def expected_occurrence() -> dict[str, Any]:
    return rooted(
        {
            "packet_format": "vela.math.claim-occurrence-resolution.v1",
            "authority_effect": "none",
            "subject": {
                "entity_id": "problem:erdos:321",
                "resolution_namespace": "erdos-problems",
                "problem_number": 321,
            },
            "resolver": {
                "repository": "https://github.com/vela-science/vela-web.git",
                "commit": WEB_COMMIT,
                "tree": WEB_TREE,
                "blob": WEB_BLOB,
                "path": WEB_PATH,
                "raw_sha256": "sha256:" + WEB_RAW_SHA256,
                "canonical_json_root": WEB_CONFIG_ROOT,
                "reference": exact_reference(
                    system="git",
                    object_kind="problem_resolution_configuration",
                    identifier=f"vela-web:{WEB_PATH}#problem:erdos:321",
                    revision=WEB_COMMIT,
                    digest=WEB_RAW_SHA256,
                    size=14843,
                    media_type="application/json",
                    selector_kind="entity_id",
                    selector_value="problem:erdos:321",
                    locator=f"https://github.com/vela-science/vela-web/blob/{WEB_COMMIT}/{WEB_PATH}",
                    mutable=False,
                ),
            },
            "occurrences": {
                "canonical": {
                    "source_id": "source:erdos-problems",
                    "native_id": "erdos:321",
                    "native_kind": "problem",
                    "content_root": "sha256:0be01696ca905c6e48036b6cc3f152ccb500ae8b7f32299ada4a58900234eb91",
                },
                "formal_statement": {
                    "source_id": "source:formal-conjectures",
                    "native_id": "Erdos321.erdos_321",
                    "native_kind": "formal_conjecture",
                    "relation_kind": "formal_statement_reference",
                    "content_root": "sha256:1e284abe734d064e27cc0c68fac2cc656ba259aab340521ebf29438006326939",
                },
                "is_theta": {
                    "source_id": "source:formal-conjectures",
                    "native_id": "Erdos321.erdos_321.variants.isTheta",
                    "native_kind": "formal_conjecture",
                    "relation_kind": "formal_statement_reference",
                    "content_root": "sha256:5226f4a3b8646b6f528961676a4eae8f317edb0d85715a570066960fa27d5a49",
                },
            },
            "retained_sources": [
                {
                    "reference": exact_reference(
                        system="git",
                        object_kind="lean_source_file",
                        identifier="formal-conjectures:FormalConjectures/ErdosProblems/321.lean#Erdos321.erdos_321.variants.isTheta",
                        revision=FC_COMMIT,
                        digest="601d8486743aede6803feaaefc7bbb73f0aa8873d0296a6a1c5400fd86c32357",
                        size=4534,
                        media_type="text/plain",
                        selector_kind="declaration",
                        selector_value="Erdos321.erdos_321.variants.isTheta",
                        locator=f"https://raw.githubusercontent.com/google-deepmind/formal-conjectures/{FC_COMMIT}/FormalConjectures/ErdosProblems/321.lean",
                        mutable=False,
                    ),
                    "retained_path": "evidence/erdos-321/translation/sources/formal-conjectures-321.lean",
                },
                {
                    "reference": exact_reference(
                        system="git",
                        object_kind="lean_source_file",
                        identifier="lean-proofs:starfleet/erdos-321/Research/Basic.lean#Erdos321.extremalSize",
                        revision=LEAN_COMMIT,
                        digest="6f8edd294e9a5dfb2475468c23518722a736798ea3e6e51822f826c1e4672a74",
                        size=2192,
                        media_type="text/plain",
                        selector_kind="declaration",
                        selector_value="Erdos321.extremalSize",
                        locator=f"https://raw.githubusercontent.com/williamjblair/lean-proofs/{LEAN_COMMIT}/starfleet/erdos-321/Research/Basic.lean",
                        mutable=False,
                    ),
                    "retained_path": "evidence/erdos-321/translation/sources/starfleet-basic.lean",
                },
            ],
            "mappings": [
                {
                    "source": "source:formal-conjectures#Erdos321.erdos_321",
                    "target": "problem:erdos:321",
                    "relation": "related",
                },
                {
                    "source": "source:formal-conjectures#Erdos321.erdos_321.variants.isTheta",
                    "target": "problem:erdos:321",
                    "relation": "related",
                },
            ],
            "translations": [
                {
                    "source": "resolver entity and reviewed occurrence fields",
                    "target": "this selectively retained occurrence packet",
                    "disposition": "preserved",
                },
                {
                    "source": "all other reviewed occurrences and candidate Sources",
                    "target": "this bounded correction packet",
                    "disposition": "omitted",
                },
                {
                    "source": "statement identity and semantic equivalence",
                    "target": "problem navigation grouping",
                    "disposition": "unresolved",
                },
            ],
            "rights": {
                "resolver_configuration": "Apache-2.0 OR MIT",
                "formal_conjectures_source": "Apache-2.0",
                "lean_proofs_source": "MIT",
                "aggregate_packet": "NOASSERTION",
            },
            "availability": {
                "status": "available",
                "access": "public anonymous Git and retained local source snapshots",
                "observed_at": "2026-08-14",
                "retention": "Git history and retained snapshots; no perpetual-hosting claim",
            },
            "limitations": [
                "The resolver establishes navigation grouping only, not statement identity or equivalence.",
                "Only the canonical problem, main Formal Conjectures declaration, and isTheta occurrence are selected here.",
                "The source statements contain answer(sorry); this packet does not turn the unavailable answer value into an outcome.",
            ],
            "nonclaims": [
                "This packet is not a Claim, Submission, Proposal, Verification Record, Decision, Event, or Standing.",
                "A source mapping, build, review, commit, or publication is not scientific acceptance.",
                "The Web resolver and this packet have authority effect none.",
            ],
        }
    )


def expected_plan(occurrence: dict[str, Any]) -> dict[str, Any]:
    occurrence_raw = rendered(occurrence)
    methods = [
        descriptor("methods/erdos-321/claim-revision-fidelity.v1.json"),
        descriptor("methods/erdos-321/subject-occurrence-mapping.v1.json"),
    ]
    assertion = (
        "At Formal Conjectures commit 59f30aa314ba225fcd9268723ce8291616df1ab0, "
        "the Lean development starfleet/erdos-321 establishes a two-sided asymptotic bound on "
        "extremalSize, which denotes the same quantity as Formal Conjectures' Erdos321.R and "
        "therefore supplies a candidate answer for the exact occurrence "
        "Erdos321.erdos_321.variants.isTheta, not a proof of it. For occurrence resolution only, "
        "the exact occurrences Erdos321.erdos_321 and Erdos321.erdos_321.variants.isTheta are "
        "associated with problem:erdos:321 under resolver root "
        "sha256:a9d6787719c5c8069a9e14ade0f5a62975410272e6cd1583865b282d1d8669dd."
    )
    return rooted(
        {
            "packet_format": "vela.math.claim-correction-preparation.v1",
            "authority_effect": "none",
            "repository": {
                "id": "8115c538-7688-40b7-ab75-3c4765bf3c19",
                "repository_root": REPOSITORY_ROOT,
                "authority_policy_root": "sha256:b9cdcd8061ea0693769b20288590dbb672984f5ff81ea7a7631a4d20eafe3cfe",
                "authority_keyset_root": "sha256:cb06d8d9c2bcb88e0bcdfa908659f06cd6419d07f335ff1c956c1da64942f111",
                "threshold": 1,
            },
            "target": {
                "claim_id": TARGET_ID,
                "claim_root": TARGET_ROOT,
                "claim_path": TARGET_PATH,
                "revision": 1,
                "standing": "accepted",
                "raw_sha256": TARGET_ROOT,
            },
            "requested_change": {
                "action": "claim.revise",
                "relation": "corrects",
                "expected_revision": 2,
                "target_claim_id": TARGET_ID,
                "target_claim_root": TARGET_ROOT,
                "rationale": "Preserve the scientific scope while replacing a shortened source revision and unrooted subject references with full source and occurrence identities.",
            },
            "successor_draft": {
                "claim_id": None,
                "claim_root": None,
                "proposal_id": None,
                "proposal_root": None,
                "availability": "unavailable_until_authenticated_submission",
                "assertion": assertion,
                "claim_type": "theoretical",
                "replayability": "exact",
                "conditions": [
                    "The scientific statement is scoped to Formal Conjectures commit 59f30aa314ba225fcd9268723ce8291616df1ab0 and lean-proofs commit a8c2872a27cf8d11cf6744ca4a2c5b49ace5fea0.",
                    "The resolver relation is navigation grouping only; it does not establish statement identity, semantic equivalence, proof, truth, acceptance, or Standing.",
                    "Erdős problem 321 remains open; this Claim does not assert resolution or optimality.",
                    "The kernel evidence remains a recorded CI attestation at an exact commit, not a fresh rebuild in this correction packet.",
                ],
                "caveats": [
                    "The Formal Conjectures answer-slot values are unavailable and remain so; they are not converted to pass, fail, or zero.",
                    "The occurrence packet selectively retains three identities and omits other reviewed occurrences without denying their existence.",
                    "A successful occurrence or revision check does not accept this correction or change Standing.",
                ],
                "verification_requirements": [
                    "subject_occurrence_mapping",
                    "claim_revision_fidelity",
                ],
            },
            "artifacts": [
                {
                    "kind": "subject-occurrence-mapping",
                    "path": "evidence/erdos-321/claim-occurrence-correction/occurrence-resolution.v1.json",
                    "digest": "sha256:" + sha256(occurrence_raw),
                    "content_root": occurrence["content_root"],
                    "size": len(occurrence_raw),
                },
            ],
            "methods": methods,
            "command_sequence": [
                {
                    "step": "submit",
                    "write_class": "producer_non_authority",
                    "requires": [
                        "explicit producer actor",
                        "producer signing identity",
                        "clean committed packet",
                    ],
                    "argv_template": [
                        "vela",
                        "submit",
                        "--repo",
                        ".",
                        "--claim",
                        "<successor_draft.assertion>",
                        "--type",
                        "theoretical",
                        "--replayability",
                        "exact",
                        "--artifact",
                        "evidence/erdos-321/claim-occurrence-correction/occurrence-resolution.v1.json:subject-occurrence-mapping",
                        "--condition",
                        "The scientific statement is scoped to Formal Conjectures commit 59f30aa314ba225fcd9268723ce8291616df1ab0 and lean-proofs commit a8c2872a27cf8d11cf6744ca4a2c5b49ace5fea0.",
                        "--condition",
                        "The resolver relation is navigation grouping only; it does not establish statement identity, semantic equivalence, proof, truth, acceptance, or Standing.",
                        "--condition",
                        "Erdős problem 321 remains open; this Claim does not assert resolution or optimality.",
                        "--condition",
                        "The kernel evidence remains a recorded CI attestation at an exact commit, not a fresh rebuild in this correction packet.",
                        "--caveat",
                        "The Formal Conjectures answer-slot values are unavailable and remain so; they are not converted to pass, fail, or zero.",
                        "--caveat",
                        "The occurrence packet selectively retains three identities and omits other reviewed occurrences without denying their existence.",
                        "--caveat",
                        "A successful occurrence or revision check does not accept this correction or change Standing.",
                        "--corrects",
                        TARGET_ID,
                        "--target-root",
                        TARGET_ROOT,
                        "--requires-verification",
                        "subject_occurrence_mapping",
                        "--requires-verification",
                        "claim_revision_fidelity",
                        "--as",
                        "agent:<producer>",
                        "--json",
                    ],
                    "runtime_outputs": [
                        "submission_id",
                        "submission_root",
                        "claim_id",
                        "claim_root",
                        "proposal_id",
                        "proposal_root",
                    ],
                },
                {
                    "step": "verify_subject_occurrence",
                    "write_class": "verifier_non_authority",
                    "argv_template": [
                        "vela",
                        "verification",
                        "record",
                        ".",
                        "<proposal_id>",
                        "--profile",
                        "math-claim-occurrence-correction-v1",
                        "--method",
                        "methods/erdos-321/subject-occurrence-mapping.v1.json",
                        "--property",
                        "subject_occurrence_mapping",
                        "--outcome",
                        "<pass|fail|error|inconclusive>",
                        "--does-not-establish",
                        "Scientific acceptance, statement equivalence, truth, or Standing.",
                        "--as",
                        "verifier:<performer>",
                        "--json",
                    ],
                },
                {
                    "step": "verify_claim_revision",
                    "write_class": "verifier_non_authority",
                    "argv_template": [
                        "vela",
                        "verification",
                        "record",
                        ".",
                        "<proposal_id>",
                        "--profile",
                        "math-claim-occurrence-correction-v1",
                        "--method",
                        "methods/erdos-321/claim-revision-fidelity.v1.json",
                        "--property",
                        "claim_revision_fidelity",
                        "--outcome",
                        "<pass|fail|error|inconclusive>",
                        "--does-not-establish",
                        "Scientific acceptance, truth, or Standing.",
                        "--as",
                        "verifier:<performer>",
                        "--json",
                    ],
                },
                {
                    "step": "inspect_decision_inbox",
                    "write_class": "read_only",
                    "argv_template": ["vela", "review", "inbox", ".", "--json"],
                    "runtime_outputs": [
                        "proposal_id",
                        "entry_root",
                        "protocol_readiness",
                    ],
                },
                {
                    "step": "decide",
                    "write_class": "authority",
                    "status": "blocked_until_exact_authorized_signer_and_entry_root_are_available",
                    "argv_template": [
                        "vela",
                        "review",
                        "accept",
                        ".",
                        "<proposal_id>",
                        "--if-entry-root",
                        "<entry_root>",
                        "--reason",
                        "<authorized reason>",
                        "--as",
                        "<attributed performer>",
                        "--session-ref",
                        "<source-owned session or checkpoint>",
                        "--json",
                    ],
                    "runtime_outputs": [
                        "decision",
                        "event",
                        "repository_root_before",
                        "repository_root_after",
                    ],
                },
                {
                    "step": "replay",
                    "write_class": "read_only",
                    "argv_template": ["vela", "replay", ".", "--json"],
                },
            ],
            "authority_residual": {
                "decision_required": True,
                "signer_availability": "not_asserted",
                "ssh_agent_probe": "not part of this generated packet",
                "required_fingerprint": "ssh-ed25519:SHA256:QD4RXcjvjm+ImqEJjOPgr5boQO4b5ESjpt3yKQ6lUXM",
                "authorized_principal": "local:device-sha256:67fbb8e56377e6868e9f941524e0bf39cfb4fd2a4bfdd25c2edb93fc82f86213|uid:501",
                "expected_transition_if_authorized": {
                    "predecessor_standing": "superseded",
                    "successor_standing": "accepted",
                    "event_kinds": ["claim.superseded", "review.accepted"],
                },
            },
            "nonclaims": [
                "This preparation packet performs no Vela write and creates no protocol object.",
                "Null future identities are unavailable, not zero, failure, or synthetic identifiers.",
                "A Verification pass would not imply acceptance; only an authorized Decision and replayed Event can change Standing.",
                "The packet changes neither Protocol 1 nor the Repository authority policy or keyset.",
            ],
        }
    )


def expected_documents() -> dict[str, dict[str, Any]]:
    occurrence = expected_occurrence()
    return {
        OCCURRENCE.name: occurrence,
        PLAN.name: expected_plan(occurrence),
    }


def validate_root(value: dict[str, Any], label: str) -> None:
    if value.get("content_root_definition") != CONTENT_ROOT_DEFINITION:
        raise PacketError(f"{label}: content root definition drift")
    observed = value.get("content_root")
    if not isinstance(observed, str) or not SHA256.fullmatch(observed):
        raise PacketError(f"{label}: content root domain drift")
    preimage = copy.deepcopy(value)
    preimage.pop("content_root", None)
    expected = "sha256:" + sha256(jcs(preimage))
    if observed != expected:
        raise PacketError(f"{label}: content root mismatch")


def validate_documents(documents: dict[str, dict[str, Any]]) -> None:
    expected = expected_documents()
    if set(documents) != set(expected):
        raise PacketError("packet inventory drift")
    for name, value in documents.items():
        validate_root(value, name)
    occurrence = documents[OCCURRENCE.name]
    references = [occurrence["resolver"]["reference"]] + [
        item["reference"] for item in occurrence["retained_sources"]
    ]
    for index, reference in enumerate(references):
        identifier = reference["native_identity"]["identifier"]
        selector = reference["selector"]["value"]
        if identifier != selector and not identifier.endswith(f"#{selector}"):
            raise PacketError(
                f"Exact Reference {index} native identifier and selector drift"
            )
    for name, value in documents.items():
        if value != expected[name]:
            raise PacketError(f"{name}: closed packet content drift")


def git(repo: Path, *arguments: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(repo), *arguments],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        raise PacketError(f"git {' '.join(arguments)} failed")
    return completed.stdout


def validate_completed_transition(repository: dict[str, Any]) -> None:
    accepted = {
        item["claim_id"]: item["claim_root"] for item in repository["accepted_claims"]
    }
    if accepted.get(SUCCESSOR_ID) != SUCCESSOR_ROOT or TARGET_ID in accepted:
        raise PacketError("accepted correction state drift")
    if repository["pending_claims"]:
        raise PacketError("completed correction unexpectedly pending")

    exact_files = {
        f"records/claims/sha256/{SUCCESSOR_ROOT.removeprefix('sha256:')}.json": SUCCESSOR_ROOT.removeprefix(
            "sha256:"
        ),
        "records/proposals/sha256/58c2f9ae804988795c587e3b788382f49c2c6a2f01ed8cf35242a7dec57b6172.json": "58c2f9ae804988795c587e3b788382f49c2c6a2f01ed8cf35242a7dec57b6172",
        "records/submissions/sha256/e1025b3c5f4b2375fe1e3c0d6497bd7a53d24f64b94988a6ad2e9abd55e1597f.json": "e1025b3c5f4b2375fe1e3c0d6497bd7a53d24f64b94988a6ad2e9abd55e1597f",
        "records/verifications/sha256/255c0d4aee18bf826163ed007367d466f778e41cde90952be07c81231f09644e.json": "255c0d4aee18bf826163ed007367d466f778e41cde90952be07c81231f09644e",
        "records/verifications/sha256/89d5b6aca9bf745cdd5e4b52811ca388438f72cd68cb54bd4312f4b47aec1dcc.json": "89d5b6aca9bf745cdd5e4b52811ca388438f72cd68cb54bd4312f4b47aec1dcc",
        "evidence/erdos-321/claim-occurrence-correction/independent-occurrence-review.v1.json": "fe510a6a6d9585d94980738a430e4a0482d089030f0b925082d277ebd6d83e06",
        "evidence/erdos-321/claim-occurrence-correction/independent-revision-review.v1.json": "11fa169ec6ae7d68dde3d7760f294ce0569913fc154ff58a3df699f7a26478ea",
        ".vela/authority/events/vev_35ebae95822f777b.json": "9463f292a5e22a9817b9c264c3db8d07801b3c657d912e74d1e766e637efbc70",
        ".vela/authority/events/vev_75b5ce899f9123da.json": "92e16e76ef1b67d1526e591c9c62086886e7b890e49d44a39532e519f3becc29",
        ".vela/authority/records/var_d307d651b41d5a6f.dsse.json": "468393795e85d2d9485c7e2a34b05e912468d1ca14d52a2a1ace5a81e1fe41b5",
    }
    for path, digest in exact_files.items():
        if sha256((REPO / path).read_bytes()) != digest:
            raise PacketError(f"completed transition byte drift: {path}")

    successor = load_json(
        REPO / f"records/claims/sha256/{SUCCESSOR_ROOT.removeprefix('sha256:')}.json"
    )
    if successor["claim_id"] != SUCCESSOR_ID or successor["revision"] != 2:
        raise PacketError("successor Claim identity drift")
    if successor["relations"] != [{"kind": "corrects", "target_claim_id": TARGET_ID}]:
        raise PacketError("successor correction relation drift")

    supersession = load_json(REPO / ".vela/authority/events/vev_35ebae95822f777b.json")
    accepted = load_json(REPO / ".vela/authority/events/vev_75b5ce899f9123da.json")
    if supersession["content"]["kind"] != "claim.superseded":
        raise PacketError("supersession Event kind drift")
    if supersession["content"]["before_hash"] != TARGET_ROOT:
        raise PacketError("supersession predecessor root drift")
    if supersession["content"]["after_hash"] != SUCCESSOR_ROOT:
        raise PacketError("supersession successor root drift")
    if accepted["content"]["kind"] != "review.accepted":
        raise PacketError("acceptance Event kind drift")
    for event in (supersession, accepted):
        payload = event["content"]["payload"]
        if payload["proposal_id"] != PROPOSAL_ID:
            raise PacketError("Decision Proposal drift")
        if payload["repository_after"] != ACCEPTED_REPOSITORY_ROOT:
            raise PacketError("Decision repository-after drift")

    authority_record = load_json(
        REPO / ".vela/authority/records/var_d307d651b41d5a6f.dsse.json"
    )
    if authority_record["signatures"] != [
        {
            "keyid": "ssh-ed25519:SHA256:QD4RXcjvjm+ImqEJjOPgr5boQO4b5ESjpt3yKQ6lUXM",
            "sig": authority_record["signatures"][0]["sig"],
        }
    ]:
        raise PacketError("authority signature key drift")


def validate_local_custody() -> tuple[str, str]:
    repository_raw = (REPO / ".vela/repository.json").read_bytes()
    observed_repository_root = "sha256:" + sha256(repository_raw)
    if observed_repository_root not in {REPOSITORY_ROOT, ACCEPTED_REPOSITORY_ROOT}:
        raise PacketError("Repository authority root changed")
    repository = load_json_bytes(repository_raw)
    if (
        repository["authority_model_root"]
        != "sha256:b9cdcd8061ea0693769b20288590dbb672984f5ff81ea7a7631a4d20eafe3cfe"
    ):
        raise PacketError("authority policy root drift")
    if (
        repository["authority_keyset_root"]
        != "sha256:cb06d8d9c2bcb88e0bcdfa908659f06cd6419d07f335ff1c956c1da64942f111"
    ):
        raise PacketError("authority keyset root drift")
    target_raw = (REPO / TARGET_PATH).read_bytes()
    if "sha256:" + sha256(target_raw) != TARGET_ROOT:
        raise PacketError("target Claim root drift")
    target = load_json_bytes(target_raw)
    if target["claim_id"] != TARGET_ID or target["revision"] != 1:
        raise PacketError("target Claim identity drift")
    retained = {
        "evidence/erdos-321/translation/sources/formal-conjectures-321.lean": "601d8486743aede6803feaaefc7bbb73f0aa8873d0296a6a1c5400fd86c32357",
        "evidence/erdos-321/translation/sources/starfleet-basic.lean": "6f8edd294e9a5dfb2475468c23518722a736798ea3e6e51822f826c1e4672a74",
    }
    for path, digest in retained.items():
        if sha256((REPO / path).read_bytes()) != digest:
            raise PacketError(f"retained source drift: {path}")
    if observed_repository_root == ACCEPTED_REPOSITORY_ROOT:
        validate_completed_transition(repository)
        return observed_repository_root, "accepted"
    return observed_repository_root, "prepared"


def validate_web_source(web_repo: Path) -> None:
    commit = git(web_repo, "rev-parse", f"{WEB_COMMIT}^{{commit}}").decode().strip()
    if commit != WEB_COMMIT:
        raise PacketError("Web resolver commit drift")
    tree = git(web_repo, "show", "-s", "--format=%T", WEB_COMMIT).decode().strip()
    if tree != WEB_TREE:
        raise PacketError("Web resolver tree drift")
    blob = git(web_repo, "rev-parse", f"{WEB_COMMIT}:{WEB_PATH}").decode().strip()
    if blob != WEB_BLOB:
        raise PacketError("Web resolver blob drift")
    raw = git(web_repo, "show", f"{WEB_COMMIT}:{WEB_PATH}")
    if len(raw) != 14843 or sha256(raw) != WEB_RAW_SHA256:
        raise PacketError("Web resolver bytes drift")
    config = load_json_bytes(raw)
    if "sha256:" + sha256(jcs(config)) != WEB_CONFIG_ROOT:
        raise PacketError("Web resolver canonical root drift")
    entities = [
        item
        for item in config.get("entities", [])
        if item.get("entity_id") == "problem:erdos:321"
    ]
    if len(entities) != 1:
        raise PacketError("Web resolver subject selector drift")
    selected = expected_occurrence()["occurrences"]
    entity = entities[0]
    if entity.get("canonical_occurrence") != selected["canonical"]:
        raise PacketError("canonical occurrence drift")
    by_id = {item["native_id"]: item for item in entity.get("reviewed_occurrences", [])}
    if by_id.get("Erdos321.erdos_321") != selected["formal_statement"]:
        raise PacketError("formal statement occurrence drift")
    if by_id.get("Erdos321.erdos_321.variants.isTheta") != selected["is_theta"]:
        raise PacketError("isTheta occurrence drift")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--print", choices=[OCCURRENCE.name, PLAN.name])
    parser.add_argument("--vela-web-repo", type=Path)
    args = parser.parse_args(argv)
    expected = expected_documents()
    if args.print:
        print(rendered(expected[args.print]).decode(), end="")
        return 0
    if not args.check:
        parser.error("use --check or --print")
    documents = {path.name: load_json(path) for path in (OCCURRENCE, PLAN)}
    validate_documents(documents)
    for path in (OCCURRENCE, PLAN):
        if path.read_bytes() != rendered(expected[path.name]):
            raise PacketError(f"{path.name}: deterministic bytes drift")
    current_repository_root, transition_status = validate_local_custody()
    if args.vela_web_repo is not None:
        validate_web_source(args.vela_web_repo.resolve())
    print(
        json.dumps(
            {
                "ok": True,
                "authority_effect": "none",
                "preparation_repository_root": REPOSITORY_ROOT,
                "current_repository_root": current_repository_root,
                "transition_status": transition_status,
                "occurrence_root": documents[OCCURRENCE.name]["content_root"],
                "plan_root": documents[PLAN.name]["content_root"],
                "web_source_checked": args.vela_web_repo is not None,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
