#!/usr/bin/env python3
"""Literal scorer and observed-evidence vectors for the cold-reader protocol."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import subprocess

import reader_protocol as protocol
import reader_scorer as scorer


HERE = Path(__file__).resolve().parent


def expect(error_type: type[Exception], callable_value, fragment: str) -> None:
    try:
        callable_value()
    except error_type as error:
        assert fragment in str(error), (fragment, str(error))
    else:
        raise AssertionError(f"expected {error_type.__name__}: {fragment}")


def append_event(entries: list[dict], body: dict) -> dict:
    entry = {**body, "previous_entry_root": entries[-1]["entry_root"] if entries else None, "sequence_number": len(entries) + 1}
    entry["entry_root"] = protocol.entry_root(entry)
    entries.append(entry)
    return entry


def main() -> int:
    instrument = json.loads((HERE / "reader-instrument.v0.1.json").read_text())
    packet = json.loads((HERE / "participant-packet.v0.1.json").read_text())

    positive = {
        "authority_classification": "none",
        "confidence_percent": 80,
        "material_difference_rows": [
            {"classification_token": "constants", "evidence_locators": ["span_03", "span_06", "span_07"], "explanation": "The terminal constants are existential while the fixed coefficients are explicit."},
            {"classification_token": "depth_selection", "evidence_locators": ["span_01", "span_04", "span_06", "span_07"], "explanation": "The terminal depth is selected existentially; fixed indices are supplied."},
            {"classification_token": "logarithm_domain", "evidence_locators": ["span_02", "span_06", "span_07"], "explanation": "The statements use real and natural iterated logarithms."},
            {"classification_token": "quantifier_conditions", "evidence_locators": ["span_04", "span_06", "span_07"], "explanation": "The threshold hypotheses and quantifier order differ."}
        ],
        "next_proof_obligation_classification": "kernel_checked_real_nat_log_bridge_before_implication",
        "next_proof_obligation_evidence_locators": ["span_01", "span_02", "span_06", "span_07"],
        "quantity_classification": "same_extremal_quantity_under_inherited_correspondence",
        "quantity_evidence_locators": ["span_08"],
        "relation_lower": "neither_established",
        "relation_lower_evidence_locators": ["span_04", "span_06"],
        "relation_upper": "neither_established",
        "relation_upper_evidence_locators": ["span_04", "span_07"],
        "source_identity_tokens": ["terminal_source", "fixed_source"]
    }
    expected_components = {
        "authority": 1, "material_constants": 1, "material_depth_selection": 1,
        "material_logarithm_domain": 1, "material_quantifier_conditions": 1,
        "next_obligation": 1, "quantity": 1, "relation_lower": 1,
        "relation_upper": 1, "source_fixed": 1, "source_terminal": 1,
    }
    result = scorer.score_response(positive, instrument, packet)
    assert result == {"components": expected_components, "deterministic_total": 11, "maximum": 11}

    mutations = []
    for field, value in (("authority_classification", "standing"), ("quantity_classification", "different_quantity"), ("relation_lower", "equivalent"), ("relation_upper", "equivalent"), ("next_proof_obligation_classification", "other")):
        mutations.append((field, lambda response, field=field, value=value: response.__setitem__(field, value)))
    for index, token in enumerate(("constants", "depth_selection", "logarithm_domain", "quantifier_conditions")):
        mutations.append((token, lambda response, index=index: response["material_difference_rows"][index].__setitem__("evidence_locators", ["span_08"])))
    mutations.extend((
        ("source_terminal", lambda response: response.__setitem__("source_identity_tokens", ["fixed_source"])),
        ("source_fixed", lambda response: response.__setitem__("source_identity_tokens", ["terminal_source"])),
    ))
    assert len(mutations) == 11
    for label, mutate in mutations:
        candidate = copy.deepcopy(positive)
        mutate(candidate)
        degraded = scorer.score_response(candidate, instrument, packet)
        assert degraded["deterministic_total"] == 10, (label, degraded)

    all_locators = list(packet["evidence_locator_catalog"])
    schema = packet["response_schema"]
    gaming = {
        "authority_classification": schema["authority_classification"][0],
        "confidence_percent": 100,
        "material_difference_rows": [
            {"classification_token": token, "evidence_locators": all_locators, "explanation": "."}
            for token in schema["material_difference_rows"]["classification_token"]
        ],
        "next_proof_obligation_classification": schema["next_proof_obligation_classification"][0],
        "next_proof_obligation_evidence_locators": all_locators,
        "quantity_classification": schema["quantity_classification"][0],
        "quantity_evidence_locators": all_locators,
        "relation_lower": schema["relation_lower"][-1],
        "relation_lower_evidence_locators": all_locators,
        "relation_upper": schema["relation_upper"][-1],
        "relation_upper_evidence_locators": all_locators,
        "source_identity_tokens": schema["source_identity_tokens"],
    }
    assert scorer.score_response(gaming, instrument, packet)["deterministic_total"] == 1
    malformed = copy.deepcopy(positive)
    malformed["unexpected"] = True
    expect(scorer.ScoreError, lambda: scorer.score_response(malformed, instrument, packet), "field set drift")
    invalid_enum = copy.deepcopy(positive)
    invalid_enum["relation_lower"] = "arbitrary"
    expect(scorer.ScoreError, lambda: scorer.score_response(invalid_enum, instrument, packet), "enum drift")
    duplicate = copy.deepcopy(positive)
    duplicate["quantity_evidence_locators"] = ["span_08", "span_08"]
    expect(scorer.ScoreError, lambda: scorer.score_response(duplicate, instrument, packet), "duplicate")
    rekeyed = copy.deepcopy(instrument)
    rekeyed["scoring_key"]["authority_classification"] = "standing"
    expect(scorer.ScoreError, lambda: scorer.score_response(positive, rekeyed, packet), "scoring key drift")

    source_repo = Path(os.environ.get("VELA_LEAN_PROOFS_REPO", str(HERE.parents[3] / "lean-proofs")))
    terminal_bytes = subprocess.run(
        ["git", "--no-replace-objects", "-C", str(source_repo), "show", "a8c2872a27cf8d11cf6744ca4a2c5b49ace5fea0:starfleet/erdos-321/Research/FinalAsymptotic.lean"],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15,
    ).stdout
    materials = {
        "participant_packet": (HERE / "participant-packet.v0.1.json").read_bytes(),
        "quantity_bridge": (HERE.parent / "definition-correspondence.v2.json").read_bytes(),
        "terminal_source": terminal_bytes,
        "fixed_source": (HERE.parent / "translation/sources/formal-conjectures-321.lean").read_bytes(),
    }
    response_raw = b'{"answer":"participant text"}\n'
    attestation_raw = b'eligible human reader attestation\n'
    record = {
        "arm": "baseline", "assignment": "baseline_first",
        "delivery_manifest_root": instrument["arms"]["baseline"]["delivery_manifest_root"],
        "eligibility_attestation_raw_root": protocol.sha256_root(attestation_raw),
        "elapsed_monotonic_ns": 1_500_000_001,
        "materials_opened": [
            {"material_id": material_id, "opened_at": "2026-08-15T12:00:00Z", "raw_sha256": instrument["material_catalog"][material_id]["raw_sha256"]}
            for material_id in instrument["arms"]["baseline"]["material_ids"]
        ],
        "monotonic_started_ns": 2_000_000_000, "monotonic_stopped_ns": 3_500_000_001,
        "participant_class": "human", "participant_id": "human-001", "period": 1,
        "period_record_root": "pending", "response": {"answer": "participant text"},
        "response_content_root": protocol.canonical_root({"answer": "participant text"}),
        "response_raw_root": protocol.sha256_root(response_raw),
        "timer_started_at": "2026-08-15T12:00:00Z", "timer_stopped_at": "2026-08-15T12:30:00Z",
    }
    record["period_record_root"] = protocol.canonical_root({key: value for key, value in record.items() if key != "period_record_root"})
    protocol.validate_period_record(record, instrument, materials, response_raw, attestation_raw)
    treatment_materials = {**materials, "comparison": (HERE / "comparison.v0.1.json").read_bytes()}
    treatment_record = copy.deepcopy(record)
    treatment_record["arm"] = "treatment"
    treatment_record["period"] = 2
    treatment_record["delivery_manifest_root"] = instrument["arms"]["treatment"]["delivery_manifest_root"]
    treatment_record["materials_opened"] = [
        {"material_id": material_id, "opened_at": "2026-08-15T12:00:00Z", "raw_sha256": instrument["material_catalog"][material_id]["raw_sha256"]}
        for material_id in instrument["arms"]["treatment"]["material_ids"]
    ]
    treatment_record["period_record_root"] = protocol.canonical_root({key: value for key, value in treatment_record.items() if key != "period_record_root"})
    protocol.validate_period_record(treatment_record, instrument, treatment_materials, response_raw, attestation_raw)
    for arm in ("baseline", "treatment"):
        rows = [instrument["material_catalog"][material_id] for material_id in instrument["arms"][arm]["material_ids"]]
        assert protocol.sha256_root(protocol.jcs(rows)) == instrument["arms"][arm]["delivery_manifest_root"]
    swapped = copy.deepcopy(record)
    swapped["materials_opened"][0], swapped["materials_opened"][1] = swapped["materials_opened"][1], swapped["materials_opened"][0]
    swapped["period_record_root"] = protocol.canonical_root({key: value for key, value in swapped.items() if key != "period_record_root"})
    expect(protocol.ProtocolError, lambda: protocol.validate_period_record(swapped, instrument, materials, response_raw, attestation_raw), "material order")
    expect(protocol.ProtocolError, lambda: protocol.validate_period_record(record, instrument, {key: value for key, value in materials.items() if key != "fixed_source"}, response_raw, attestation_raw), "material set")
    extra_material = treatment_materials
    expect(protocol.ProtocolError, lambda: protocol.validate_period_record(record, instrument, extra_material, response_raw, attestation_raw), "material set")
    drifted_material = {**materials, "terminal_source": materials["terminal_source"] + b"x"}
    expect(protocol.ProtocolError, lambda: protocol.validate_period_record(record, instrument, drifted_material, response_raw, attestation_raw), "material byte")
    expect(protocol.ProtocolError, lambda: protocol.validate_period_record(record, instrument, materials, b'{"answer":"drift"}\n', attestation_raw), "response root")
    drifted_timer = copy.deepcopy(record)
    drifted_timer["elapsed_monotonic_ns"] += 1
    drifted_timer["period_record_root"] = protocol.canonical_root({key: value for key, value in drifted_timer.items() if key != "period_record_root"})
    expect(protocol.ProtocolError, lambda: protocol.validate_period_record(drifted_timer, instrument, materials, response_raw, attestation_raw), "elapsed")

    first = {
        "assignment": "baseline_first", "eligibility_attestation_raw_root": "sha256:" + "1" * 64,
        "enrollment_ordinal": 1, "entry_root": "sha256:c1922ff78d8ef6a7d04c1031f16cc7bd312cafee4ed6f15f328de58d1ce33414",
        "event": "enrolled", "occurred_at": "2026-08-15T12:00:00Z", "participant_class": "human",
        "participant_id": "human-001", "previous_entry_root": None, "sequence_number": 1,
    }
    empty = instrument["observed_enrollment_ledger"]["initial_empty_document"]
    assert protocol.canonical_root(empty) == instrument["observed_enrollment_ledger"]["initial_empty_root"]
    assert protocol.entry_root(first) == first["entry_root"]
    entries = [first]
    append_event(entries, {"event": "period_completed", "occurred_at": "2026-08-15T12:30:00Z", "participant_id": "human-001", "per_period_record_root": "sha256:" + "2" * 64, "period": 1})
    append_event(entries, {"event": "period_completed", "occurred_at": "2026-08-15T13:00:00Z", "participant_id": "human-001", "per_period_record_root": "sha256:" + "3" * 64, "period": 2})
    append_event(entries, {"assignment": "treatment_first", "eligibility_attestation_raw_root": "sha256:" + "4" * 64, "enrollment_ordinal": 2, "event": "enrolled", "occurred_at": "2026-08-16T12:00:00Z", "participant_class": "human", "participant_id": "human-002"})
    append_event(entries, {"event": "withdrawn", "occurred_at": "2026-08-16T12:10:00Z", "participant_id": "human-002", "reason_code": "participant_request"})
    append_event(entries, {"assignment": "baseline_first", "eligibility_attestation_raw_root": "sha256:" + "5" * 64, "enrollment_ordinal": 3, "event": "enrolled", "occurred_at": "2026-08-17T12:00:00Z", "participant_class": "human", "participant_id": "human-003"})
    ledger = {"entries": entries, "format": protocol.LEDGER_FORMAT}
    summary = protocol.validate_ledger(ledger, instrument["assignment_schedule"])
    assert summary["enrolled"] == 3 and summary["completed"] == 1 and summary["head_root"] == entries[-1]["entry_root"]

    wrong_sequence = copy.deepcopy(ledger)
    wrong_sequence["entries"][1]["sequence_number"] = 9
    expect(protocol.ProtocolError, lambda: protocol.validate_ledger(wrong_sequence, instrument["assignment_schedule"]), "sequence")
    boolean_sequence = copy.deepcopy(ledger)
    boolean_sequence["entries"][0]["sequence_number"] = True
    expect(protocol.ProtocolError, lambda: protocol.validate_ledger(boolean_sequence, instrument["assignment_schedule"]), "sequence")
    wrong_prior = copy.deepcopy(ledger)
    wrong_prior["entries"][1]["previous_entry_root"] = "sha256:" + "9" * 64
    wrong_prior["entries"][1]["entry_root"] = protocol.entry_root(wrong_prior["entries"][1])
    expect(protocol.ProtocolError, lambda: protocol.validate_ledger(wrong_prior, instrument["assignment_schedule"]), "prior-root")
    wrong_root = copy.deepcopy(ledger)
    wrong_root["entries"][0]["entry_root"] = "sha256:" + "0" * 64
    expect(protocol.ProtocolError, lambda: protocol.validate_ledger(wrong_root, instrument["assignment_schedule"]), "entry root")
    duplicate_id = {"entries": [first], "format": protocol.LEDGER_FORMAT}
    append_event(duplicate_id["entries"], {"assignment": "treatment_first", "eligibility_attestation_raw_root": "sha256:" + "6" * 64, "enrollment_ordinal": 2, "event": "enrolled", "occurred_at": "2026-08-18T12:00:00Z", "participant_class": "human", "participant_id": "human-001"})
    expect(protocol.ProtocolError, lambda: protocol.validate_ledger(duplicate_id, instrument["assignment_schedule"]), "enrollment event")
    wrong_assignment = copy.deepcopy(first)
    wrong_assignment["assignment"] = "treatment_first"
    wrong_assignment["entry_root"] = protocol.entry_root(wrong_assignment)
    expect(protocol.ProtocolError, lambda: protocol.validate_ledger({"entries": [wrong_assignment], "format": protocol.LEDGER_FORMAT}, instrument["assignment_schedule"]), "assignment")
    boolean_ordinal = copy.deepcopy(first)
    boolean_ordinal["enrollment_ordinal"] = True
    boolean_ordinal["entry_root"] = protocol.entry_root(boolean_ordinal)
    expect(protocol.ProtocolError, lambda: protocol.validate_ledger({"entries": [boolean_ordinal], "format": protocol.LEDGER_FORMAT}, instrument["assignment_schedule"]), "ordinal")
    after_cutoff = copy.deepcopy(first)
    after_cutoff["occurred_at"] = "2026-10-01T00:00:00Z"
    after_cutoff["entry_root"] = protocol.entry_root(after_cutoff)
    expect(protocol.ProtocolError, lambda: protocol.validate_ledger({"entries": [after_cutoff], "format": protocol.LEDGER_FORMAT}, instrument["assignment_schedule"]), "enrollment event")
    wrong_period = [first]
    append_event(wrong_period, {"event": "period_completed", "occurred_at": "2026-08-15T12:30:00Z", "participant_id": "human-001", "per_period_record_root": "sha256:" + "7" * 64, "period": 2})
    expect(protocol.ProtocolError, lambda: protocol.validate_ledger({"entries": wrong_period, "format": protocol.LEDGER_FORMAT}, instrument["assignment_schedule"]), "period order")
    boolean_period = [first]
    append_event(boolean_period, {"event": "period_completed", "occurred_at": "2026-08-15T12:30:00Z", "participant_id": "human-001", "per_period_record_root": "sha256:" + "7" * 64, "period": True})
    expect(protocol.ProtocolError, lambda: protocol.validate_ledger({"entries": boolean_period, "format": protocol.LEDGER_FORMAT}, instrument["assignment_schedule"]), "period order")
    late_completion = [first]
    append_event(late_completion, {"event": "period_completed", "occurred_at": "2026-10-08T00:00:00Z", "participant_id": "human-001", "per_period_record_root": "sha256:" + "7" * 64, "period": 1})
    expect(protocol.ProtocolError, lambda: protocol.validate_ledger({"entries": late_completion, "format": protocol.LEDGER_FORMAT}, instrument["assignment_schedule"]), "period completion")
    before_enrollment = [first]
    append_event(before_enrollment, {"event": "period_completed", "occurred_at": "2026-08-15T11:59:59Z", "participant_id": "human-001", "per_period_record_root": "sha256:" + "7" * 64, "period": 1})
    expect(protocol.ProtocolError, lambda: protocol.validate_ledger({"entries": before_enrollment, "format": protocol.LEDGER_FORMAT}, instrument["assignment_schedule"]), "chronology")
    too_many: list[dict] = []
    for ordinal in range(1, 20):
        append_event(too_many, {"assignment": "baseline_first" if ordinal % 2 else "treatment_first", "eligibility_attestation_raw_root": "sha256:" + f"{ordinal:x}"[-1] * 64, "enrollment_ordinal": ordinal, "event": "enrolled", "occurred_at": "2026-08-19T12:00:00Z", "participant_class": "human", "participant_id": f"maximum-{ordinal:02d}"})
    expect(protocol.ProtocolError, lambda: protocol.validate_ledger({"entries": too_many, "format": protocol.LEDGER_FORMAT}, instrument["assignment_schedule"]), "limit")

    complete_entries: list[dict] = []
    for ordinal in range(1, 14):
        participant_id = f"complete-{ordinal:02d}"
        append_event(complete_entries, {"assignment": "baseline_first" if ordinal % 2 else "treatment_first", "eligibility_attestation_raw_root": "sha256:" + f"{ordinal:x}"[-1] * 64, "enrollment_ordinal": ordinal, "event": "enrolled", "occurred_at": "2026-08-20T12:00:00Z", "participant_class": "human", "participant_id": participant_id})
    for ordinal in range(1, 13):
        participant_id = f"complete-{ordinal:02d}"
        append_event(complete_entries, {"event": "period_completed", "occurred_at": "2026-08-20T13:00:00Z", "participant_id": participant_id, "per_period_record_root": "sha256:" + "a" * 64, "period": 1})
        append_event(complete_entries, {"event": "period_completed", "occurred_at": "2026-08-20T13:00:00Z", "participant_id": participant_id, "per_period_record_root": "sha256:" + "b" * 64, "period": 2})
    complete_summary = protocol.validate_ledger({"entries": complete_entries, "format": protocol.LEDGER_FORMAT}, instrument["assignment_schedule"])
    assert complete_summary["completed"] == 12 and complete_summary["status"] == "complete"
    blocked_enrollment = copy.deepcopy(complete_entries)
    append_event(blocked_enrollment, {"assignment": "treatment_first", "eligibility_attestation_raw_root": "sha256:" + "d" * 64, "enrollment_ordinal": 14, "event": "enrolled", "occurred_at": "2026-08-20T13:01:00Z", "participant_class": "human", "participant_id": "complete-14"})
    expect(protocol.ProtocolError, lambda: protocol.validate_ledger({"entries": blocked_enrollment, "format": protocol.LEDGER_FORMAT}, instrument["assignment_schedule"]), "enrollment event")
    append_event(complete_entries, {"event": "period_completed", "occurred_at": "2026-08-20T13:01:00Z", "participant_id": "complete-13", "per_period_record_root": "sha256:" + "c" * 64, "period": 1})
    append_event(complete_entries, {"event": "period_completed", "occurred_at": "2026-08-20T13:02:00Z", "participant_id": "complete-13", "per_period_record_root": "sha256:" + "d" * 64, "period": 2})
    assert protocol.validate_ledger({"entries": complete_entries, "format": protocol.LEDGER_FORMAT}, instrument["assignment_schedule"])["completed"] == 13

    assert protocol.elapsed_monotonic_ns(2_000_000_000, 3_500_000_001) == 1_500_000_001
    expect(protocol.ProtocolError, lambda: protocol.elapsed_monotonic_ns(2, 1), "precedes")
    assert protocol.sha256_root(b'{"answer":1}\n') == "sha256:cc206ebfccfc22324dae65b112277c8d8fd2c5280a04025e6c5f2f78cdf774cf"
    assert instrument["custody"]["future_manifest_contract"]["logical_location"].startswith("custody://vela-math/")
    print("erdos-321-reader-protocol-tests: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
