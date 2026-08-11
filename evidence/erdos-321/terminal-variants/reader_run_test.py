#!/usr/bin/env python3
"""Focused operator and custody tests for the cold-reader run."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import tempfile

from evidence_rooting import jcs
import reader_run as run


HERE = Path(__file__).resolve().parent


def expect(error: type[BaseException], action, contains: str) -> None:
    try:
        action()
    except error as observed:
        assert contains in str(observed), observed
    else:
        raise AssertionError(f"expected {error.__name__}: {contains}")


def positive_response() -> dict:
    return {
        "authority_classification": "none",
        "confidence_percent": 80,
        "material_difference_rows": [
            {"classification_token": "constants", "evidence_locators": ["span_03", "span_06", "span_07"], "explanation": "Existential terminal constants differ from fixed coefficients."},
            {"classification_token": "depth_selection", "evidence_locators": ["span_01", "span_04", "span_06", "span_07"], "explanation": "Terminal depth is selected while fixed indices are supplied."},
            {"classification_token": "logarithm_domain", "evidence_locators": ["span_02", "span_06", "span_07"], "explanation": "Real and natural iterated logarithms differ."},
            {"classification_token": "quantifier_conditions", "evidence_locators": ["span_04", "span_06", "span_07"], "explanation": "Threshold hypotheses and quantifier order differ."},
        ],
        "next_proof_obligation_classification": "kernel_checked_real_nat_log_bridge_before_implication",
        "next_proof_obligation_evidence_locators": ["span_01", "span_02", "span_06", "span_07"],
        "quantity_classification": "same_extremal_quantity_under_inherited_correspondence",
        "quantity_evidence_locators": ["span_08"],
        "relation_lower": "neither_established",
        "relation_lower_evidence_locators": ["span_04", "span_06"],
        "relation_upper": "neither_established",
        "relation_upper_evidence_locators": ["span_04", "span_07"],
        "source_identity_tokens": ["terminal_source", "fixed_source"],
    }


def write(path: Path, value) -> None:
    path.write_bytes(jcs(value) if not isinstance(value, bytes) else value)


def opened(instrument: dict, arm: str, timestamp: str) -> list[dict]:
    return [
        {"material_id": material_id, "opened_at": timestamp, "raw_sha256": instrument["material_catalog"][material_id]["raw_sha256"]}
        for material_id in instrument["arms"][arm]["material_ids"]
    ]


def record(
    custody: Path, participant: str, period: int, arm: str, source_repo: Path,
    response: dict, started: str, stopped: str, occurred: str,
) -> dict:
    scratch = custody.parent / f"scratch-{participant}-{period}"
    scratch.mkdir()
    response_path, opened_path = scratch / "response.json", scratch / "opened.json"
    write(response_path, response)
    instrument = json.loads((HERE / "reader-instrument.v0.1.json").read_text())
    write(opened_path, opened(instrument, arm, started))
    return run.record_period(
        custody, participant, response_path, opened_path, source_repo,
        started, stopped, period * 1_000_000_000, period * 1_000_000_000 + 500_000_000, occurred,
    )


def main() -> int:
    source_repo = Path(os.environ.get("VELA_LEAN_PROOFS_REPO", str(HERE.parents[3] / "lean-proofs")))
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary).resolve()
        custody = root / "run"
        manifest = run.init_run(custody, "custodian:test", now="2026-08-15T12:00:00Z", token="0123456789abcdef")
        assert manifest["run_id"] == "20260815T120000Z-0123456789abcdef"
        assert custody.stat().st_mode & 0o777 == 0o700
        assert all((custody / name).stat().st_mode & 0o777 == 0o700 for name in ("attestations", "period-records", "responses"))
        expect(run.RunError, lambda: run.init_run(custody, "custodian:test"), "already exists")

        attestation_1 = root / "attestation-1.txt"
        attestation_1.write_bytes(b"I attest that none of the frozen exclusions applied before period one.\n")
        first = run.enroll(custody, "human-001", attestation_1, "2026-08-15T12:01:00Z")
        assert first["assignment"] == "baseline_first" and first["enrollment_ordinal"] == 1
        expect(run.RunError, lambda: run.enroll(custody, "human-001", attestation_1, "2026-08-15T12:02:00Z"), "already")

        answer = positive_response()
        p1 = record(custody, "human-001", 1, "baseline", source_repo, answer, "2026-08-15T12:02:00Z", "2026-08-15T12:05:00Z", "2026-08-15T12:05:00Z")
        p2 = record(custody, "human-001", 2, "treatment", source_repo, answer, "2026-08-15T12:06:00Z", "2026-08-15T12:10:00Z", "2026-08-15T12:10:00Z")
        assert p1["score"]["deterministic_total"] == 11 and p2["score"]["deterministic_total"] == 11

        attestation_2 = root / "attestation-2.txt"
        attestation_2.write_bytes(b"Independent eligible reader; no prior access to excluded materials.\n")
        second = run.enroll(custody, "human-002", attestation_2, "2026-08-15T12:11:00Z")
        assert second["assignment"] == "treatment_first" and second["enrollment_ordinal"] == 2
        record(custody, "human-002", 1, "treatment", source_repo, answer, "2026-08-15T12:12:00Z", "2026-08-15T12:15:00Z", "2026-08-15T12:15:00Z")
        record(custody, "human-002", 2, "baseline", source_repo, answer, "2026-08-15T12:16:00Z", "2026-08-15T12:20:00Z", "2026-08-15T12:20:00Z")

        attestation_3 = root / "attestation-3.txt"
        attestation_3.write_bytes(b"Eligible before opening any period materials.\n")
        run.enroll(custody, "human-003", attestation_3, "2026-08-15T12:21:00Z")
        withdrawn = run.withdraw(custody, "human-003", "participant_request", "2026-08-15T12:22:00Z")
        assert withdrawn["event"] == "withdrawn"
        expect(run.RunError, lambda: record(custody, "human-003", 1, "baseline", source_repo, answer, "2026-08-15T12:23:00Z", "2026-08-15T12:24:00Z", "2026-08-15T12:24:00Z"), "cannot complete")

        audited = run.audit(custody, source_repo)
        assert audited["status"] == "pass" and audited["period_records"] == 4
        report = run.analyze(custody, source_repo, "2026-08-20T00:00:00Z")
        assert report["status"] == "in_progress"
        assert report["analysis"]["first_period_groups"]["baseline"]["count"] == 1
        assert report["analysis"]["first_period_groups"]["treatment"]["count"] == 1
        assert report["analysis"]["primary_difference_treatment_minus_baseline_fraction"] == [0, 1]
        assert len(report["analysis"]["first_period_records"]) == 2
        assert all(len(group["component_sums"]) == 11 for group in report["analysis"]["first_period_groups"].values())
        assert report["withdrawn_participant_ids"] == ["human-003"]
        assert report["authority_effect"] == "none"
        assert report["content_root"] == run.protocol.canonical_root({key: value for key, value in report.items() if key != "content_root"})

        late = run.analyze(custody, source_repo, "2026-10-08T00:00:00Z")
        assert late["status"] == "incomplete_at_frozen_cutoff"
        manifest_path = custody / run.MANIFEST_NAME
        final_manifest = manifest_path.read_bytes()
        retained_attestation = custody / "attestations" / "human-001.txt"
        attestation_bytes = retained_attestation.read_bytes()
        retained_attestation.write_bytes(b"changed after enrollment\n")
        expect(run.RunError, lambda: run.audit(custody, source_repo), "differs from enrollment")
        retained_attestation.write_bytes(attestation_bytes)
        response_path = custody / "responses" / "human-001-period-1.json"
        response_backup = root / "human-001-period-1.backup"
        response_path.rename(response_backup)
        response_path.symlink_to(response_backup)
        expect(run.RunError, lambda: run.audit(custody, source_repo), "file type")
        response_path.unlink()
        response_backup.rename(response_path)
        oversized = response_path.read_bytes()
        response_path.write_bytes(b"x" * 1_048_577)
        expect(run.RunError, lambda: run.audit(custody, source_repo), "size drift")
        response_path.write_bytes(oversized)
        drifted = json.loads(manifest_path.read_text())
        drifted["ledger_head_root"] = "sha256:" + "0" * 64
        manifest_path.write_bytes(jcs(drifted))
        expect(run.RunError, lambda: run.audit(custody, source_repo), "ledger root drift")
        manifest_path.write_bytes(jcs(manifest))
        # The initial manifest is also stale after enrollment and must refuse.
        expect(run.RunError, lambda: run.audit(custody, source_repo), "ledger root drift")
        manifest_path.write_bytes(final_manifest)
        assert run.audit(custody, source_repo)["status"] == "pass"

    print("erdos-321-reader-run-tests: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
