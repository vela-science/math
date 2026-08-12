#!/usr/bin/env python3
"""Offline checks for the FC-to-Vela do-not-collapse matrix."""

from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
import re
import unittest
from collections.abc import Callable


HERE = Path(__file__).resolve().parent
MATRIX_PATH = HERE / "do-not-collapse.v0.1.json"
ROOT_DEFINITION = "sha256 of RFC 8785 canonical JSON after removing only matrix_root"
PROGRAM_SHA256 = "4dfef11f56497fe029204919e810dcfb9d8a9597a767681bd17155c57f1f6fda"
EXPECTED_MATRIX_ROOT = "sha256:81c088354d7aa247aa50c655566a5971aa21ccbaded1823867357b6a3c7735b6"
CORE_OUTCOMES = {"pass", "fail", "inconclusive", "error"}
FC_OUTCOMES = CORE_OUTCOMES | {"unavailable"}
REQUIRED_RULES = {
    "fc_pass_is_not_standing",
    "publication_is_not_decision",
    "proposal_status_is_derived",
    "frontier_has_no_identifier",
    "projection_root_is_not_typed_source_identity",
    "producer_signature_is_not_reviewer_authority",
    "unsigned_draft_is_not_submission",
    "unavailable_is_not_verification_failure",
}
REQUIRED_ADAPTER_REQUIREMENTS = {
    "unsupported_schema_and_version_refusal",
    "field_and_schema_typed_roots",
    "exact_source_revision_and_drift",
    "complete_bounded_reads",
    "copied_or_referenced_custody",
    "interpreting_implementation_identity",
    "license_access_and_public_redaction",
    "reconstructibility_and_loss",
    "deletion_tombstone_and_mutability",
}
EXPECTED_ROOT_DOMAINS = [
    "fc_audit_core",
    "fc_audit_observation",
    "source_content",
    "artifact",
    "claim",
    "submission",
    "verification",
    "proposal",
    "repository",
    "authority",
    "projection",
]
EXPECTED_PLANES = {
    "source_observation": {
        "authority_effect": "none",
        "examples": [
            "Formal Conjectures audit core",
            "Formal Conjectures observation envelope",
            "GitHub review or merge status",
        ],
    },
    "activity_preparation": {
        "authority_effect": "none",
        "examples": [
            "Target",
            "Approach",
            "Attempt",
            "Research Block",
            "unsigned Submission draft",
        ],
    },
    "portable_signed_object": {
        "authority_effect": "none",
        "examples": ["signed Submission", "signed Verification Record"],
    },
    "repository_authority": {
        "authority_effect": "human_decision_only",
        "examples": ["authorized human Decision", "admitted Event"],
    },
    "derived_read": {
        "authority_effect": "none",
        "examples": ["Standing", "Proposal status", "Frontier", "projection"],
    },
}
EXPECTED_REVIEWED_SOURCES = {
    "core": {
        "repository": "https://github.com/vela-science/vela.git",
        "commit": "f61abcee4edd2d8a33fa181f4aac6eade82c6edf",
        "protocol_manifest_root": "sha256:b93f359a435e9c7f5d48e6a123ee823644bbe6117e162815c6f967a11eef2e84",
        "custody": {
            "visibility": "public",
            "acquisition": "anonymous Git HTTPS at the exact commit",
            "license": "Apache-2.0 OR MIT",
            "reconstructibility": "The reviewed source commit is publicly fetchable and the protocol manifest root is independently pinned here.",
        },
        "verification_outcomes": ["pass", "fail", "inconclusive", "error"],
    },
    "math": {
        "repository": "https://github.com/vela-science/math.git",
        "commit": "79998d341606892e435caf3ec53cedd384b5b52f",
        "phase_0_packet_manifest_sha256": "3f4879db9ae16aa1f106a499d70635a8180f0fbd6db82074f44307d894b0f1c9",
        "custody": {
            "visibility": "public",
            "acquisition": "anonymous Git HTTPS at the exact commit",
            "license": "No repository-wide license was declared in the reviewed tree.",
            "reconstructibility": "The reviewed source commit and complete Phase 0 packet are publicly fetchable; reuse rights must not be inferred from public visibility.",
        },
    },
    "web": {
        "repository": "https://github.com/vela-science/vela-web.git",
        "commit": "9feb69750834a076a13e066905107da61a976407",
        "custody": {
            "visibility": "private",
            "acquisition": "authorized private Git checkout at the exact commit",
            "license": "Software is Apache-2.0 OR MIT; original editorial content is CC BY 4.0 unless otherwise marked.",
            "reconstructibility": "This public Math packet does not copy or disclose private Web source. A public reader cannot reconstruct the reviewed Web implementation; WEB-03 must prove its parser, mapper, renderer, and refusal paths inside the authorized private repository.",
        },
    },
}


def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def parse_json(raw: bytes) -> dict[str, object]:
    if not raw.endswith(b"\n") or raw.endswith(b"\n\n"):
        raise ValueError("matrix file must use exactly one trailing LF")
    value = json.loads(raw, object_pairs_hook=reject_duplicate_keys)
    if not isinstance(value, dict):
        raise ValueError("matrix must be one JSON object")
    return value


def jcs(value: object) -> bytes:
    if value is None:
        return b"null"
    if value is True:
        return b"true"
    if value is False:
        return b"false"
    if isinstance(value, int) and not isinstance(value, bool):
        if abs(value) > 9_007_199_254_740_991:
            raise ValueError("integer exceeds interoperable JSON range")
        return str(value).encode("ascii")
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite JSON number")
        raise ValueError("matrix admits no floating-point values")
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if isinstance(value, list):
        return b"[" + b",".join(jcs(item) for item in value) + b"]"
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise ValueError("object keys must be strings")
        keys = sorted(value, key=lambda key: key.encode("utf-16-be", errors="surrogatepass"))
        return b"{" + b",".join(jcs(key) + b":" + jcs(value[key]) for key in keys) + b"}"
    raise ValueError(f"unsupported JSON value: {type(value)!r}")


def expected_root(matrix: dict[str, object]) -> str:
    payload = copy.deepcopy(matrix)
    payload.pop("matrix_root", None)
    return "sha256:" + hashlib.sha256(jcs(payload)).hexdigest()


def validate(matrix: dict[str, object]) -> None:
    if matrix.get("schema") != "vela.math.fc-audit.do-not-collapse.v0.1":
        raise ValueError("unsupported matrix schema")
    if matrix.get("matrix_root_definition") != ROOT_DEFINITION:
        raise ValueError("matrix root definition drift")
    if matrix.get("matrix_root") != expected_root(matrix):
        raise ValueError("matrix root drift")
    if matrix.get("authority_effect") != "none":
        raise ValueError("matrix cannot carry authority")
    if matrix["program_contract"]["sha256"] != PROGRAM_SHA256:
        raise ValueError("program contract drift")

    rules = matrix["rules"]
    rule_ids = [rule["id"] for rule in rules]
    if len(rule_ids) != len(set(rule_ids)) or set(rule_ids) != REQUIRED_RULES:
        raise ValueError("do-not-collapse rule inventory drift")
    accepted_rule_ids = matrix["acceptance"]["required_rule_ids"]
    if len(accepted_rule_ids) != len(REQUIRED_RULES) or set(accepted_rule_ids) != REQUIRED_RULES:
        raise ValueError("acceptance rule inventory drift")
    for rule in rules:
        for field in (
            "producer_state",
            "consumer_state",
            "required_behavior",
            "forbidden_collapse",
            "falsifier",
        ):
            if not isinstance(rule[field], str) or not rule[field].strip():
                raise ValueError(f"rule {rule['id']} has no {field}")

    conversions = matrix["fc_outcome_conversion"]
    by_outcome = {item["fc_outcome"]: item for item in conversions}
    if len(conversions) != len(by_outcome) or set(by_outcome) != FC_OUTCOMES:
        raise ValueError("FC outcome conversion inventory drift")
    if set(matrix["reviewed_sources"]["core"]["verification_outcomes"]) != CORE_OUTCOMES:
        raise ValueError("Core Verification vocabulary drift")
    for outcome, conversion in by_outcome.items():
        if conversion["source_axis"] != outcome:
            raise ValueError(f"source outcome collapsed: {outcome}")
        if conversion["automatic_verification"] is not False:
            raise ValueError(f"automatic Verification forbidden: {outcome}")
        mapped = conversion["possible_protocol_outcome_after_local_policy_and_signing"]
        if outcome == "unavailable":
            if mapped is not None:
                raise ValueError("unavailable must refuse Verification conversion")
        elif mapped != outcome or mapped not in CORE_OUTCOMES:
            raise ValueError(f"protocol outcome drift: {outcome}")

    root_domains = matrix["root_domains"]
    if root_domains != EXPECTED_ROOT_DOMAINS:
        raise ValueError("typed root-domain inventory drift")
    plane_records = matrix["planes"]
    planes = {plane["id"]: plane for plane in plane_records}
    if len(planes) != len(plane_records) or set(planes) != set(EXPECTED_PLANES):
        raise ValueError("plane inventory drift")
    for plane_id, expected in EXPECTED_PLANES.items():
        actual = planes[plane_id]
        if actual.get("authority_effect") != expected["authority_effect"]:
            raise ValueError("plane authority drift")
        if actual.get("examples") != expected["examples"]:
            raise ValueError("plane example inventory drift")
    if any(
        plane["authority_effect"] != "none"
        for key, plane in planes.items()
        if key != "repository_authority"
    ):
        raise ValueError("non-authority plane claims authority")
    if planes["repository_authority"]["authority_effect"] != "human_decision_only":
        raise ValueError("human Decision boundary drift")

    if matrix["reviewed_sources"] != EXPECTED_REVIEWED_SOURCES:
        raise ValueError("reviewed source inventory or identity drift")
    adapter_requirements = matrix["adapter_requirements"]
    adapter_requirement_ids = [item["id"] for item in adapter_requirements]
    if (
        len(adapter_requirement_ids) != len(REQUIRED_ADAPTER_REQUIREMENTS)
        or set(adapter_requirement_ids) != REQUIRED_ADAPTER_REQUIREMENTS
    ):
        raise ValueError("adapter requirement inventory drift")
    for requirement in adapter_requirements:
        for field in ("requirement", "falsifier"):
            if not isinstance(requirement[field], str) or not requirement[field].strip():
                raise ValueError(f"adapter requirement {requirement['id']} has no {field}")
    accepted_adapter_ids = matrix["acceptance"]["required_adapter_requirement_ids"]
    if (
        len(accepted_adapter_ids) != len(REQUIRED_ADAPTER_REQUIREMENTS)
        or set(accepted_adapter_ids) != REQUIRED_ADAPTER_REQUIREMENTS
    ):
        raise ValueError("acceptance adapter requirement inventory drift")

    roots = [
        matrix["reviewed_sources"]["core"]["protocol_manifest_root"],
        matrix["matrix_root"],
    ]
    if not all(re.fullmatch(r"sha256:[0-9a-f]{64}", root) for root in roots):
        raise ValueError("full typed root required")
    if re.fullmatch(
        r"[0-9a-f]{64}",
        matrix["reviewed_sources"]["math"]["phase_0_packet_manifest_sha256"],
    ) is None:
        raise ValueError("Phase 0 packet file SHA-256 must be full")
    commits = [source["commit"] for source in matrix["reviewed_sources"].values()]
    if not all(re.fullmatch(r"[0-9a-f]{40}", commit) for commit in commits):
        raise ValueError("reviewed source commit must be full")
    if matrix["matrix_root"] != EXPECTED_MATRIX_ROOT:
        raise ValueError("matrix root is not externally pinned")


class DoNotCollapseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = MATRIX_PATH.read_bytes()
        cls.matrix = parse_json(cls.raw)

    def test_matrix_is_rooted_and_complete(self) -> None:
        validate(self.matrix)

    def test_parser_rejects_duplicate_keys_and_bad_framing(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            parse_json(b'{"schema":"a","schema":"b"}\n')
        with self.assertRaisesRegex(ValueError, "exactly one trailing LF"):
            parse_json(self.raw.rstrip(b"\n"))
        with self.assertRaisesRegex(ValueError, "exactly one trailing LF"):
            parse_json(self.raw + b"\n")

    def test_every_declared_collapse_fails_closed(self) -> None:
        mutations: list[tuple[str, Callable[[dict[str, object]], None]]] = [
            ("matrix cannot carry authority", lambda value: value.__setitem__("authority_effect", "standing")),
            ("do-not-collapse rule inventory drift", lambda value: value["rules"].pop()),
            ("acceptance rule inventory drift", lambda value: value["acceptance"]["required_rule_ids"].pop()),
            ("acceptance rule inventory drift", lambda value: value["acceptance"]["required_rule_ids"].append(value["acceptance"]["required_rule_ids"][0])),
            ("source outcome collapsed", lambda value: value["fc_outcome_conversion"][0].__setitem__("source_axis", "accepted")),
            ("automatic Verification forbidden", lambda value: value["fc_outcome_conversion"][0].__setitem__("automatic_verification", True)),
            ("unavailable must refuse Verification conversion", lambda value: value["fc_outcome_conversion"][4].__setitem__("possible_protocol_outcome_after_local_policy_and_signing", "error")),
            ("Core Verification vocabulary drift", lambda value: value["reviewed_sources"]["core"]["verification_outcomes"].append("unavailable")),
            ("typed root-domain inventory drift", lambda value: value["root_domains"].append("projection")),
            ("typed root-domain inventory drift", lambda value: value["root_domains"].remove("artifact")),
            ("plane inventory drift", lambda value: value["planes"].append(copy.deepcopy(value["planes"][0]))),
            ("plane example inventory drift", lambda value: value["planes"][0]["examples"].pop()),
            ("reviewed source inventory or identity drift", lambda value: value["reviewed_sources"]["core"].__setitem__("commit", "0" * 40)),
            ("reviewed source inventory or identity drift", lambda value: value["reviewed_sources"].pop("web")),
            ("reviewed source inventory or identity drift", lambda value: value["reviewed_sources"]["web"].__setitem__("repository", "https://example.invalid/private.git")),
            ("adapter requirement inventory drift", lambda value: value["adapter_requirements"].pop()),
            ("acceptance adapter requirement inventory drift", lambda value: value["acceptance"]["required_adapter_requirement_ids"].pop()),
            ("plane authority drift", lambda value: value["planes"][3].__setitem__("authority_effect", "none")),
        ]
        for message, mutate in mutations:
            with self.subTest(message=message):
                value = copy.deepcopy(self.matrix)
                mutate(value)
                value["matrix_root"] = expected_root(value)
                with self.assertRaisesRegex(ValueError, message):
                    validate(value)

    def test_root_refuses_semantic_drift(self) -> None:
        value = copy.deepcopy(self.matrix)
        value["rules"][0]["required_behavior"] = "Treat pass as accepted Standing."
        with self.assertRaisesRegex(ValueError, "matrix root drift"):
            validate(value)

    def test_nonclaims_keep_external_validation_separate(self) -> None:
        limits = " ".join(self.matrix["acceptance"]["does_not_establish"])
        self.assertIn("Vela Verification", limits)
        self.assertIn("Vela Decision", limits)
        self.assertIn("Math Standing", limits)
        self.assertIn("External adoption or independent validation", limits)


if __name__ == "__main__":
    unittest.main()
