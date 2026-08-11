#!/usr/bin/env python3
"""Deterministic custody, timing, and append-only enrollment validation."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any

from evidence_rooting import jcs, sha256_hex


class ProtocolError(ValueError):
    """Observed reader evidence is outside the frozen protocol."""


SHA256_PREFIX = "sha256:"
LEDGER_FORMAT = "vela.math.cold-reader-enrollment-ledger.v0.1"


def sha256_root(value: bytes) -> str:
    return SHA256_PREFIX + sha256_hex(value)


def canonical_root(value: dict[str, Any]) -> str:
    return sha256_root(jcs(value))


def entry_root(entry: dict[str, Any]) -> str:
    if "entry_root" in entry:
        entry = {key: value for key, value in entry.items() if key != "entry_root"}
    return canonical_root(entry)


def parse_time(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ProtocolError("RFC 3339 UTC timestamp required")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as error:
        raise ProtocolError("RFC 3339 UTC timestamp required") from error
    return parsed


def elapsed_monotonic_ns(start_ns: Any, stop_ns: Any) -> int:
    if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in (start_ns, stop_ns)):
        raise ProtocolError("nonnegative integer monotonic nanoseconds required")
    if stop_ns < start_ns:
        raise ProtocolError("monotonic stop precedes start")
    return stop_ns - start_ns


def validate_period_record(
    record: dict[str, Any], instrument: dict[str, Any], material_bytes: dict[str, bytes],
    response_raw: bytes, eligibility_attestation_raw: bytes,
) -> None:
    expected_fields = set(instrument["custody"]["per_period_record"]) | {"period_record_root"}
    if not isinstance(record, dict) or set(record) != expected_fields:
        raise ProtocolError("period record field drift")
    if record["participant_class"] != "human" or not isinstance(record["participant_id"], str) or not record["participant_id"]:
        raise ProtocolError("period participant drift")
    assignment, period = record["assignment"], record["period"]
    if assignment not in ("baseline_first", "treatment_first") or type(period) is not int or period not in (1, 2):
        raise ProtocolError("period assignment drift")
    expected_arm = "baseline" if (assignment == "baseline_first") == (period == 1) else "treatment"
    arm = instrument["arms"][expected_arm]
    if record["arm"] != expected_arm or record["delivery_manifest_root"] != arm["delivery_manifest_root"]:
        raise ProtocolError("assigned arm drift")
    catalog = instrument["material_catalog"]
    expected_materials = arm["material_ids"]
    if set(material_bytes) != set(expected_materials):
        raise ProtocolError("material set drift")
    opened = record["materials_opened"]
    if not isinstance(opened, list) or len(opened) != len(expected_materials):
        raise ProtocolError("materials opened drift")
    wall_start, wall_stop = parse_time(record["timer_started_at"]), parse_time(record["timer_stopped_at"])
    if wall_stop < wall_start:
        raise ProtocolError("wall timer order drift")
    for material_id, observed in zip(expected_materials, opened, strict=True):
        expected = catalog[material_id]
        if set(observed) != {"material_id", "opened_at", "raw_sha256"} or observed["material_id"] != material_id:
            raise ProtocolError("material order or field drift")
        opened_at = parse_time(observed["opened_at"])
        data = material_bytes[material_id]
        if not wall_start <= opened_at <= wall_stop or len(data) != expected["byte_length"] or sha256_root(data) != expected["raw_sha256"] or observed["raw_sha256"] != expected["raw_sha256"]:
            raise ProtocolError("material byte or chronology drift")
    start_ns, stop_ns = record["monotonic_started_ns"], record["monotonic_stopped_ns"]
    if record["elapsed_monotonic_ns"] != elapsed_monotonic_ns(start_ns, stop_ns):
        raise ProtocolError("elapsed monotonic drift")
    try:
        decoded_response = json.loads(response_raw.decode("utf-8", errors="strict"), object_pairs_hook=unique_object)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ProtocolError("response bytes drift") from error
    if decoded_response != record["response"] or record["response_raw_root"] != sha256_root(response_raw) or record["response_content_root"] != canonical_root(record["response"]):
        raise ProtocolError("response root drift")
    if record["eligibility_attestation_raw_root"] != sha256_root(eligibility_attestation_raw):
        raise ProtocolError("attestation root drift")
    if record["period_record_root"] != canonical_root({key: value for key, value in record.items() if key != "period_record_root"}):
        raise ProtocolError("period record root drift")


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ProtocolError("duplicate response key")
        result[key] = value
    return result


def validate_ledger(ledger: dict[str, Any], schedule: dict[str, Any]) -> dict[str, int | str]:
    if set(ledger) != {"entries", "format"} or ledger["format"] != LEDGER_FORMAT or not isinstance(ledger["entries"], list):
        raise ProtocolError("ledger envelope drift")
    human = schedule["participant_classes"]["human"]
    if human != {"allocation": "sequential alternation between baseline_first and treatment_first", "initial_sequence": "baseline_first", "target": 12}:
        raise ProtocolError("human assignment schedule drift")
    recruitment_cutoff = parse_time(schedule["recruitment_cutoff"])
    completion_cutoff = parse_time(schedule["completion_cutoff"])
    maximum_enrollment = schedule["maximum_enrollment"]
    if not isinstance(maximum_enrollment, int) or isinstance(maximum_enrollment, bool) or maximum_enrollment < human["target"]:
        raise ProtocolError("maximum enrollment drift")
    states: dict[str, dict[str, Any]] = {}
    prior_root: str | None = None
    prior_time: datetime | None = None
    enrollment_count = completed_count = 0
    for sequence, entry in enumerate(ledger["entries"], 1):
        if not isinstance(entry, dict) or type(entry.get("sequence_number")) is not int or entry["sequence_number"] != sequence or entry.get("previous_entry_root") != prior_root:
            raise ProtocolError("ledger sequence or prior-root drift")
        if entry.get("entry_root") != entry_root(entry):
            raise ProtocolError("ledger entry root drift")
        event = entry.get("event")
        participant_id = entry.get("participant_id")
        occurred = parse_time(entry.get("occurred_at"))
        if not isinstance(participant_id, str) or not participant_id:
            raise ProtocolError("participant id required")
        if prior_time is not None and occurred < prior_time:
            raise ProtocolError("ledger chronology drift")
        if event == "enrolled":
            expected_fields = {"assignment", "eligibility_attestation_raw_root", "enrollment_ordinal", "entry_root", "event", "occurred_at", "participant_class", "participant_id", "previous_entry_root", "sequence_number"}
            if set(entry) != expected_fields or participant_id in states or occurred > recruitment_cutoff or completed_count >= human["target"]:
                raise ProtocolError("enrollment event drift")
            enrollment_count += 1
            if enrollment_count > maximum_enrollment or type(entry["enrollment_ordinal"]) is not int or entry["enrollment_ordinal"] != enrollment_count or entry["participant_class"] != "human":
                raise ProtocolError("enrollment limit or ordinal drift")
            expected_assignment = "baseline_first" if enrollment_count % 2 == 1 else "treatment_first"
            if entry["assignment"] != expected_assignment or not valid_root(entry["eligibility_attestation_raw_root"]):
                raise ProtocolError("assignment or attestation drift")
            states[participant_id] = {"enrolled_at": occurred, "periods": [], "withdrawn": False}
        elif event == "period_completed":
            expected_fields = {"entry_root", "event", "occurred_at", "participant_id", "per_period_record_root", "period", "previous_entry_root", "sequence_number"}
            state = states.get(participant_id)
            if set(entry) != expected_fields or state is None or state["withdrawn"] or occurred < state["enrolled_at"] or occurred > completion_cutoff:
                raise ProtocolError("period completion event drift")
            expected_period = len(state["periods"]) + 1
            if type(entry["period"]) is not int or entry["period"] != expected_period or expected_period not in (1, 2) or not valid_root(entry["per_period_record_root"]):
                raise ProtocolError("period order or record root drift")
            state["periods"].append(expected_period)
            if expected_period == 2:
                completed_count += 1
        elif event == "withdrawn":
            expected_fields = {"entry_root", "event", "occurred_at", "participant_id", "previous_entry_root", "reason_code", "sequence_number"}
            state = states.get(participant_id)
            if set(entry) != expected_fields or state is None or state["withdrawn"] or len(state["periods"]) == 2 or occurred < state["enrolled_at"] or occurred > completion_cutoff:
                raise ProtocolError("withdrawal event drift")
            if not isinstance(entry["reason_code"], str) or not entry["reason_code"]:
                raise ProtocolError("withdrawal reason required")
            state["withdrawn"] = True
        else:
            raise ProtocolError("unknown ledger event")
        prior_root = entry["entry_root"]
        prior_time = occurred
    status = "complete" if completed_count >= human["target"] else "under_recruited_or_in_progress"
    return {"completed": completed_count, "enrolled": enrollment_count, "head_root": prior_root or canonical_root(ledger), "status": status}


def valid_root(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 71 and value.startswith(SHA256_PREFIX) and all(character in "0123456789abcdef" for character in value[7:])
