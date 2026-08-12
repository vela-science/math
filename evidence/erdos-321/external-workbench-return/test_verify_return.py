#!/usr/bin/env python3
"""Hostile and positive tests for the external-workbench return boundary."""

from __future__ import annotations

import copy
from pathlib import Path
import tempfile

from verify_return import ReturnError, capture, jcs


REQUIRED_NONCLAIMS = [
    "This external workbench return is not a Vela Verification, Decision, Event, or Standing.",
    "Activity signatures authenticate activity, not scientific truth.",
    "Automated conformance does not establish human acceptance.",
    "An operator attestation does not by itself establish independent adoption.",
    "Artifact roots establish byte identity, not scientific correctness.",
]


def expect(action, contains: str) -> None:
    try:
        action()
    except ReturnError as error:
        assert contains in str(error), error
    else:
        raise AssertionError(f"expected refusal containing: {contains}")


def write(path: Path, value: dict) -> None:
    path.write_bytes(jcs(value))


def attestation() -> dict:
    return {
        "format": "vela.external-workbench-operator-attestation.v1",
        "operator_id": "operator:external-lab",
        "controller_id": "controller:external-lab",
        "relationship_to_experiment_operator": "not_same_operator",
        "operation_control": "separately_controlled",
        "repository_authority_credentials_used": False,
        "scientific_decision_authority_used": False,
        "attested_at": "2026-08-20T12:00:00Z",
        "identity_evidence_method": "signed_statement",
        "identity_evidence_locator": "https://example.org/evidence/operator-statement.json",
        "identity_evidence_root": "sha256:" + "1" * 64,
    }


def workbench_result() -> dict:
    return {
        "format": "vela.workbench-result.v1",
        "authority_effect": "none",
        "workbench": {
            "name": "external-lab-workbench",
            "repository": "https://example.org/external-lab/workbench.git",
            "commit": "2" * 40,
            "operator_id": "operator:external-lab",
            "operation_id": "operation:erdos-321-001",
        },
        "packet_root": "sha256:62004075572072cb96ccdf3f869ad3cf261d1abd39e826624d49b026dd57d92d",
        "activity_event_ids": ["event:external-001"],
        "result_status": "candidate_returned",
        "artifact_roots": ["sha256:" + "3" * 64],
        "nonclaims": REQUIRED_NONCLAIMS,
    }


def main() -> int:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        result_path, attestation_path = root / "result.json", root / "attestation.json"
        result, statement = workbench_result(), attestation()
        write(result_path, result)
        write(attestation_path, statement)
        receipt = capture(result_path, attestation_path, "2026-08-20T12:01:00Z", "custodian:vela")
        assert receipt["authority_effect"] == "none"
        assert receipt["externality_status"] == "operator_attested_not_independently_verified"
        assert receipt["scientific_status"] == "unverified_candidate"
        assert receipt["result_status"] == "candidate_returned"
        assert len(receipt["content_root"]) == 71
        assert "human acceptance" in receipt["limitations"][-1]

        refused = copy.deepcopy(result)
        refused["result_status"] = "refused"
        refused["activity_event_ids"] = []
        refused["artifact_roots"] = []
        write(result_path, refused)
        refused_receipt = capture(result_path, attestation_path, "2026-08-20T12:01:00Z", "custodian:vela")
        assert refused_receipt["scientific_status"] == "workbench_refused"

        drift = copy.deepcopy(result)
        drift["packet_root"] = "sha256:" + "0" * 64
        write(result_path, drift)
        expect(lambda: capture(result_path, attestation_path, "2026-08-20T12:01:00Z", "custodian:vela"), "packet root")

        drift = copy.deepcopy(result)
        drift["nonclaims"] = drift["nonclaims"][:-1]
        write(result_path, drift)
        expect(lambda: capture(result_path, attestation_path, "2026-08-20T12:01:00Z", "custodian:vela"), "nonclaims")

        drift = copy.deepcopy(result)
        drift["artifact_roots"] = []
        write(result_path, drift)
        expect(lambda: capture(result_path, attestation_path, "2026-08-20T12:01:00Z", "custodian:vela"), "artifact root")

        drift = copy.deepcopy(result)
        drift["authority_effect"] = "standing"
        write(result_path, drift)
        expect(lambda: capture(result_path, attestation_path, "2026-08-20T12:01:00Z", "custodian:vela"), "authority effect")

        drift_statement = copy.deepcopy(statement)
        drift_statement["relationship_to_experiment_operator"] = "same_operator"
        write(result_path, result)
        write(attestation_path, drift_statement)
        expect(lambda: capture(result_path, attestation_path, "2026-08-20T12:01:00Z", "custodian:vela"), "separation")

        drift_statement = copy.deepcopy(statement)
        drift_statement["repository_authority_credentials_used"] = True
        write(attestation_path, drift_statement)
        expect(lambda: capture(result_path, attestation_path, "2026-08-20T12:01:00Z", "custodian:vela"), "authority")

        write(attestation_path, statement)
        result_path.write_text('{"format":"vela.workbench-result.v1","format":"duplicate"}', encoding="utf-8")
        expect(lambda: capture(result_path, attestation_path, "2026-08-20T12:01:00Z", "custodian:vela"), "strict JSON")

        result_path.unlink()
        result_path.symlink_to(attestation_path)
        expect(lambda: capture(result_path, attestation_path, "2026-08-20T12:01:00Z", "custodian:vela"), "type or size")

    print("external-workbench-return-tests: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
