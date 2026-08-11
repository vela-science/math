#!/usr/bin/env python3
"""Operate and audit the preregistered Erdős 321 cold-reader run."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import secrets
import stat
import subprocess
import sys
from typing import Any

from evidence_rooting import jcs
import reader_protocol as protocol
import reader_scorer as scorer


HERE = Path(__file__).resolve().parent
PLAN_PATH = HERE / "plan.v0.1.json"
INSTRUMENT_PATH = HERE / "reader-instrument.v0.1.json"
PACKET_PATH = HERE / "participant-packet.v0.1.json"
COMPARISON_PATH = HERE / "comparison.v0.1.json"
LEDGER_NAME = "enrollment-ledger.v0.1.json"
MANIFEST_NAME = "manifest.v0.1.json"
MANIFEST_FORMAT = "vela.math.cold-reader-custody-manifest.v0.1"
REPORT_FORMAT = "vela.math.erdos321-terminal-variant-reader-result.v0.1"
PARTICIPANT_RE = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}\Z")
RUN_RE = re.compile(r"[0-9]{8}T[0-9]{6}Z-[0-9a-f]{16}\Z")
COMPONENT_NAMES = (
    "authority", "material_constants", "material_depth_selection",
    "material_logarithm_domain", "material_quantifier_conditions",
    "next_obligation", "quantity", "relation_lower", "relation_upper",
    "source_fixed", "source_terminal",
)


class RunError(ValueError):
    """The requested operation is outside the frozen run contract."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=protocol.unique_object)
    except (OSError, UnicodeError, json.JSONDecodeError, protocol.ProtocolError) as error:
        raise RunError(f"invalid JSON input: {path.name}") from error
    if not isinstance(value, dict):
        raise RunError(f"JSON object required: {path.name}")
    return value


def private_bytes(path: Path, maximum: int = 1_048_576) -> bytes:
    try:
        before = path.lstat()
    except OSError as error:
        raise RunError(f"missing custody file: {path.name}") from error
    if not stat.S_ISREG(before.st_mode) or before.st_mode & 0o777 != 0o600 or before.st_size > maximum:
        raise RunError(f"custody file type, mode, or size drift: {path.name}")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags)
    try:
        opened = os.fstat(fd)
        if (opened.st_dev, opened.st_ino, opened.st_size) != (before.st_dev, before.st_ino, before.st_size):
            raise RunError(f"custody file identity drift: {path.name}")
        chunks: list[bytes] = []
        observed = 0
        while True:
            chunk = os.read(fd, min(65_536, maximum + 1 - observed))
            if not chunk:
                break
            chunks.append(chunk)
            observed += len(chunk)
            if observed > maximum:
                raise RunError(f"custody file exceeds size bound: {path.name}")
        after = os.fstat(fd)
        if (after.st_dev, after.st_ino, after.st_size) != (before.st_dev, before.st_ino, before.st_size):
            raise RunError(f"custody file changed during read: {path.name}")
        return b"".join(chunks)
    finally:
        os.close(fd)


def load_private_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(private_bytes(path).decode("utf-8", errors="strict"), object_pairs_hook=protocol.unique_object)
    except (UnicodeError, json.JSONDecodeError, protocol.ProtocolError) as error:
        raise RunError(f"invalid custody JSON: {path.name}") from error
    if not isinstance(value, dict):
        raise RunError(f"custody JSON object required: {path.name}")
    return value


def input_bytes(path: Path, maximum: int) -> bytes:
    observed = path.lstat()
    if not stat.S_ISREG(observed.st_mode) or observed.st_size > maximum:
        raise RunError(f"input file type or size drift: {path.name}")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags)
    try:
        data = os.read(fd, maximum + 1)
        if len(data) > maximum or os.read(fd, 1):
            raise RunError(f"input exceeds size bound: {path.name}")
        return data
    finally:
        os.close(fd)


def fixed_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    plan, instrument, packet = load_json(PLAN_PATH), load_json(INSTRUMENT_PATH), load_json(PACKET_PATH)
    if protocol.canonical_root({key: value for key, value in plan.items() if key != "content_root"}) != plan.get("content_root"):
        raise RunError("plan content root drift")
    if protocol.canonical_root({key: value for key, value in instrument.items() if key != "content_root"}) != instrument.get("content_root"):
        raise RunError("instrument content root drift")
    if protocol.canonical_root({key: value for key, value in packet.items() if key != "content_root"}) != packet.get("content_root"):
        raise RunError("participant packet content root drift")
    if plan.get("reader_instrument_root") != instrument["content_root"] or plan.get("participant_packet_root") != packet["content_root"]:
        raise RunError("plan input root drift")
    return plan, instrument, packet


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def safe_id(value: str, label: str) -> str:
    if not PARTICIPANT_RE.fullmatch(value):
        raise RunError(f"invalid {label}")
    return value


def require_run(directory: Path) -> Path:
    resolved = directory.resolve(strict=True)
    if not resolved.is_dir() or resolved.stat().st_mode & 0o777 != 0o700:
        raise RunError("custody directory must be a real mode-0700 directory")
    for name in ("attestations", "period-records", "responses"):
        child = resolved / name
        observed = child.lstat()
        if not stat.S_ISDIR(observed.st_mode) or observed.st_mode & 0o777 != 0o700:
            raise RunError(f"custody subdirectory drift: {name}")
    return resolved


def write_new(path: Path, data: bytes, mode: int = 0o600) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, mode)
    try:
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise RunError("short custody write")
            view = view[written:]
        os.fsync(fd)
        if os.fstat(fd).st_mode & 0o777 != mode:
            raise RunError("custody file mode drift")
    except BaseException:
        try:
            os.close(fd)
        finally:
            path.unlink(missing_ok=True)
        raise
    os.close(fd)


def replace_json(path: Path, value: dict[str, Any]) -> None:
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise RunError("custody target is not a regular file")
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(8)}")
    try:
        write_new(temporary, jcs(value))
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def init_run(directory: Path, custodian: str, *, now: str | None = None, token: str | None = None) -> dict[str, Any]:
    parent = directory.parent.resolve(strict=True)
    destination = parent / directory.name
    if destination.exists() or destination.is_symlink():
        raise RunError("custody directory already exists")
    created_at = now or utc_now()
    protocol.parse_time(created_at)
    random_token = token or secrets.token_hex(8)
    run_id = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ").strftime("%Y%m%dT%H%M%SZ-") + random_token
    if not RUN_RE.fullmatch(run_id) or not custodian.strip():
        raise RunError("invalid run identity or custodian")
    os.mkdir(destination, 0o700)
    for name in ("attestations", "period-records", "responses"):
        os.mkdir(destination / name, 0o700)
    plan, instrument, _ = fixed_inputs()
    ledger = instrument["observed_enrollment_ledger"]["initial_empty_document"]
    if protocol.canonical_root(ledger) != instrument["observed_enrollment_ledger"]["initial_empty_root"]:
        raise RunError("initial ledger root drift")
    manifest = {
        "baseline_delivery_manifest_root": instrument["arms"]["baseline"]["delivery_manifest_root"],
        "comparison_root": plan["comparison_root"],
        "created_at": created_at,
        "custodian": custodian,
        "format": MANIFEST_FORMAT,
        "instrument_root": instrument["content_root"],
        "ledger_head_root": protocol.canonical_root(ledger),
        "participant_packet_root": plan["participant_packet_root"],
        "period_record_roots": [],
        "plan_root": plan["content_root"],
        "run_id": run_id,
        "source_lock_root": plan["source_lock_root"],
        "treatment_delivery_manifest_root": instrument["arms"]["treatment"]["delivery_manifest_root"],
    }
    write_new(destination / LEDGER_NAME, jcs(ledger))
    write_new(destination / MANIFEST_NAME, jcs(manifest))
    return manifest


def read_state(directory: Path) -> tuple[Path, dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    run = require_run(directory)
    plan, instrument, packet = fixed_inputs()
    ledger, manifest = load_private_json(run / LEDGER_NAME), load_private_json(run / MANIFEST_NAME)
    protocol.validate_ledger(ledger, instrument["assignment_schedule"])
    expected_manifest_fields = set(instrument["custody"]["future_manifest_contract"]["required_members"]) | {"format"}
    if set(manifest) != expected_manifest_fields or manifest.get("format") != MANIFEST_FORMAT or not RUN_RE.fullmatch(str(manifest.get("run_id", ""))):
        raise RunError("custody manifest drift")
    if not isinstance(manifest.get("custodian"), str) or not manifest["custodian"].strip():
        raise RunError("custody manifest custodian drift")
    protocol.parse_time(manifest.get("created_at"))
    if not isinstance(manifest.get("period_record_roots"), list) or not all(protocol.valid_root(value) for value in manifest["period_record_roots"]):
        raise RunError("custody manifest period roots drift")
    expected_fixed = {
        "plan_root": plan["content_root"], "source_lock_root": plan["source_lock_root"],
        "comparison_root": plan["comparison_root"], "instrument_root": instrument["content_root"],
        "participant_packet_root": packet["content_root"],
        "baseline_delivery_manifest_root": instrument["arms"]["baseline"]["delivery_manifest_root"],
        "treatment_delivery_manifest_root": instrument["arms"]["treatment"]["delivery_manifest_root"],
    }
    if any(manifest.get(key) != value for key, value in expected_fixed.items()):
        raise RunError("custody manifest input drift")
    ledger_summary = protocol.validate_ledger(ledger, instrument["assignment_schedule"])
    if manifest.get("ledger_head_root") != ledger_summary["head_root"]:
        raise RunError("custody manifest ledger root drift")
    return run, plan, instrument, packet, ledger, manifest


def append_ledger(run: Path, instrument: dict[str, Any], ledger: dict[str, Any], manifest: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    entries = ledger["entries"]
    entry = {
        **event,
        "previous_entry_root": entries[-1]["entry_root"] if entries else None,
        "sequence_number": len(entries) + 1,
    }
    entry["entry_root"] = protocol.entry_root(entry)
    updated = {"entries": [*entries, entry], "format": protocol.LEDGER_FORMAT}
    summary = protocol.validate_ledger(updated, instrument["assignment_schedule"])
    replace_json(run / LEDGER_NAME, updated)
    manifest["ledger_head_root"] = summary["head_root"]
    replace_json(run / MANIFEST_NAME, manifest)
    return entry


def enroll(directory: Path, participant_id: str, attestation_path: Path, occurred_at: str) -> dict[str, Any]:
    run, _, instrument, _, ledger, manifest = read_state(directory)
    participant_id = safe_id(participant_id, "participant id")
    protocol.parse_time(occurred_at)
    attestation = input_bytes(attestation_path, 65_536)
    if not attestation:
        raise RunError("eligibility attestation must not be empty")
    if any(entry.get("event") == "enrolled" and entry.get("participant_id") == participant_id for entry in ledger["entries"]):
        raise RunError("participant is already enrolled")
    ordinal = sum(1 for entry in ledger["entries"] if entry["event"] == "enrolled") + 1
    assignment = "baseline_first" if ordinal % 2 else "treatment_first"
    write_new(run / "attestations" / f"{participant_id}.txt", attestation)
    return append_ledger(run, instrument, ledger, manifest, {
        "assignment": assignment,
        "eligibility_attestation_raw_root": protocol.sha256_root(attestation),
        "enrollment_ordinal": ordinal,
        "event": "enrolled",
        "occurred_at": occurred_at,
        "participant_class": "human",
        "participant_id": participant_id,
    })


def participant_state(ledger: dict[str, Any], participant_id: str) -> dict[str, Any]:
    state: dict[str, Any] | None = None
    for entry in ledger["entries"]:
        if entry["participant_id"] != participant_id:
            continue
        if entry["event"] == "enrolled":
            state = {
                "assignment": entry["assignment"],
                "attestation_root": entry["eligibility_attestation_raw_root"],
                "periods": [], "withdrawn": False,
            }
        elif state is not None and entry["event"] == "period_completed":
            state["periods"].append(entry["period"])
        elif state is not None and entry["event"] == "withdrawn":
            state["withdrawn"] = True
    if state is None:
        raise RunError("participant is not enrolled")
    return state


def opened_materials_template(directory: Path, participant_id: str, opened_at: str) -> list[dict[str, Any]]:
    _, _, instrument, _, ledger, _ = read_state(directory)
    participant_id = safe_id(participant_id, "participant id")
    protocol.parse_time(opened_at)
    state = participant_state(ledger, participant_id)
    if state["withdrawn"] or len(state["periods"]) >= 2:
        raise RunError("participant cannot open another period")
    period = len(state["periods"]) + 1
    arm = "baseline" if (state["assignment"] == "baseline_first") == (period == 1) else "treatment"
    return [
        {"material_id": material_id, "opened_at": opened_at, "raw_sha256": instrument["material_catalog"][material_id]["raw_sha256"]}
        for material_id in instrument["arms"][arm]["material_ids"]
    ]


def git_blob(repository: Path, commit: str, path: str) -> bytes:
    if not repository.resolve(strict=True).is_dir():
        raise RunError("source repository is not a directory")
    env = {"PATH": os.environ.get("PATH", ""), "LC_ALL": "C", "GIT_CONFIG_NOSYSTEM": "1", "GIT_NO_REPLACE_OBJECTS": "1", "GIT_TERMINAL_PROMPT": "0"}
    result = subprocess.run(
        ["git", "--no-replace-objects", "-C", str(repository), "show", f"{commit}:{path}"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, check=False, timeout=15,
    )
    if result.returncode != 0:
        raise RunError("terminal source object is unavailable")
    return result.stdout


def material_bytes(instrument: dict[str, Any], packet: dict[str, Any], arm: str, source_repository: Path) -> dict[str, bytes]:
    catalog = instrument["material_catalog"]
    span = packet["evidence_locator_catalog"]["span_01"]
    commit = span["source"].split(":", 1)[1]
    available = {
        "participant_packet": PACKET_PATH.read_bytes(),
        "quantity_bridge": HERE.parent / "definition-correspondence.v2.json",
        "fixed_source": HERE.parent / "translation" / "sources" / "formal-conjectures-321.lean",
        "comparison": COMPARISON_PATH,
        "terminal_source": git_blob(source_repository, commit, catalog["terminal_source"]["path"]),
    }
    data = {key: value.read_bytes() if isinstance(value, Path) else value for key, value in available.items()}
    return {material_id: data[material_id] for material_id in instrument["arms"][arm]["material_ids"]}


def record_period(
    directory: Path, participant_id: str, response_path: Path, opened_path: Path,
    source_repository: Path, timer_started_at: str, timer_stopped_at: str,
    monotonic_started_ns: int, monotonic_stopped_ns: int, occurred_at: str,
) -> dict[str, Any]:
    run, _, instrument, packet, ledger, manifest = read_state(directory)
    participant_id = safe_id(participant_id, "participant id")
    state = participant_state(ledger, participant_id)
    if state["withdrawn"] or len(state["periods"]) >= 2:
        raise RunError("participant cannot complete another period")
    period = len(state["periods"]) + 1
    arm = "baseline" if (state["assignment"] == "baseline_first") == (period == 1) else "treatment"
    response_raw = input_bytes(response_path, 1_048_576)
    try:
        response = json.loads(response_raw.decode("utf-8", errors="strict"), object_pairs_hook=protocol.unique_object)
    except (UnicodeError, json.JSONDecodeError, protocol.ProtocolError) as error:
        raise RunError("response is not strict JSON") from error
    if not isinstance(response, dict):
        raise RunError("response object required")
    opened = load_json_array(opened_path)
    attestation = private_bytes(run / "attestations" / f"{participant_id}.txt")
    if protocol.sha256_root(attestation) != state["attestation_root"]:
        raise RunError("eligibility attestation changed after enrollment")
    if protocol.parse_time(occurred_at) < protocol.parse_time(timer_stopped_at):
        raise RunError("period event precedes timer stop")
    materials = material_bytes(instrument, packet, arm, source_repository)
    record = {
        "arm": arm,
        "assignment": state["assignment"],
        "delivery_manifest_root": instrument["arms"][arm]["delivery_manifest_root"],
        "eligibility_attestation_raw_root": protocol.sha256_root(attestation),
        "elapsed_monotonic_ns": protocol.elapsed_monotonic_ns(monotonic_started_ns, monotonic_stopped_ns),
        "materials_opened": opened,
        "monotonic_started_ns": monotonic_started_ns,
        "monotonic_stopped_ns": monotonic_stopped_ns,
        "participant_class": "human",
        "participant_id": participant_id,
        "period": period,
        "period_record_root": "pending",
        "response": response,
        "response_content_root": protocol.canonical_root(response),
        "response_raw_root": protocol.sha256_root(response_raw),
        "timer_started_at": timer_started_at,
        "timer_stopped_at": timer_stopped_at,
    }
    record["period_record_root"] = protocol.canonical_root({key: value for key, value in record.items() if key != "period_record_root"})
    protocol.validate_period_record(record, instrument, materials, response_raw, attestation)
    response_target = run / "responses" / f"{participant_id}-period-{period}.json"
    record_target = run / "period-records" / f"{participant_id}-period-{period}.json"
    write_new(response_target, response_raw)
    score = scorer.score_response(response, instrument, packet)
    write_new(record_target, jcs({**record, "score": score}))
    manifest["period_record_roots"] = [*manifest["period_record_roots"], record["period_record_root"]]
    entry = append_ledger(run, instrument, ledger, manifest, {
        "event": "period_completed", "occurred_at": occurred_at, "participant_id": participant_id,
        "per_period_record_root": record["period_record_root"], "period": period,
    })
    return {"entry": entry, "score": score}


def load_json_array(path: Path) -> list[dict[str, Any]]:
    try:
        value = json.loads(input_bytes(path, 1_048_576).decode("utf-8", errors="strict"), object_pairs_hook=protocol.unique_object)
    except (OSError, UnicodeError, json.JSONDecodeError, protocol.ProtocolError) as error:
        raise RunError("invalid opened-materials JSON") from error
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise RunError("opened-materials array required")
    return value


def withdraw(directory: Path, participant_id: str, reason_code: str, occurred_at: str) -> dict[str, Any]:
    run, _, instrument, _, ledger, manifest = read_state(directory)
    safe_id(participant_id, "participant id")
    if not reason_code.strip():
        raise RunError("withdrawal reason required")
    return append_ledger(run, instrument, ledger, manifest, {
        "event": "withdrawn", "occurred_at": occurred_at,
        "participant_id": participant_id, "reason_code": reason_code,
    })


def audit(directory: Path, source_repository: Path) -> dict[str, Any]:
    run, _, instrument, packet, ledger, manifest = read_state(directory)
    expected_roots: list[str] = []
    attestation_roots = {
        entry["participant_id"]: entry["eligibility_attestation_raw_root"]
        for entry in ledger["entries"] if entry["event"] == "enrolled"
    }
    expected_attestations = {f"{participant_id}.txt" for participant_id in attestation_roots}
    expected_records = {
        f"{entry['participant_id']}-period-{entry['period']}.json"
        for entry in ledger["entries"] if entry["event"] == "period_completed"
    }
    if {path.name for path in (run / "attestations").iterdir()} != expected_attestations:
        raise RunError("custody attestation inventory drift")
    if {path.name for path in (run / "responses").iterdir()} != expected_records or {path.name for path in (run / "period-records").iterdir()} != expected_records:
        raise RunError("custody period inventory drift")
    for entry in ledger["entries"]:
        if entry["event"] != "period_completed":
            continue
        participant_id, period = entry["participant_id"], entry["period"]
        stored = load_private_json(run / "period-records" / f"{participant_id}-period-{period}.json")
        score = stored.pop("score", None)
        response_raw = private_bytes(run / "responses" / f"{participant_id}-period-{period}.json")
        attestation = private_bytes(run / "attestations" / f"{participant_id}.txt")
        if protocol.sha256_root(attestation) != attestation_roots[participant_id]:
            raise RunError("eligibility attestation differs from enrollment")
        materials = material_bytes(instrument, packet, stored["arm"], source_repository)
        protocol.validate_period_record(stored, instrument, materials, response_raw, attestation)
        if score != scorer.score_response(stored["response"], instrument, packet) or entry["per_period_record_root"] != stored["period_record_root"]:
            raise RunError("stored score or ledger period root drift")
        expected_roots.append(stored["period_record_root"])
    if manifest["period_record_roots"] != expected_roots:
        raise RunError("manifest period-root order drift")
    summary = protocol.validate_ledger(ledger, instrument["assignment_schedule"])
    return {"ledger": summary, "period_records": len(expected_roots), "run_id": manifest["run_id"], "status": "pass"}


def analyze(directory: Path, source_repository: Path, as_of: str) -> dict[str, Any]:
    run, plan, instrument, packet, ledger, manifest = read_state(directory)
    audit_result = audit(directory, source_repository)
    as_of_time = protocol.parse_time(as_of)
    completions: dict[str, list[dict[str, Any]]] = {}
    completed_order: list[str] = []
    withdrawn: list[str] = []
    for entry in ledger["entries"]:
        if entry["event"] == "period_completed":
            stored = load_private_json(run / "period-records" / f"{entry['participant_id']}-period-{entry['period']}.json")
            completions.setdefault(entry["participant_id"], []).append(stored)
            if entry["period"] == 2:
                completed_order.append(entry["participant_id"])
        elif entry["event"] == "withdrawn":
            withdrawn.append(entry["participant_id"])
    target = instrument["assignment_schedule"]["participant_classes"]["human"]["target"]
    selected_ids = completed_order[:target]
    groups: dict[str, list[dict[str, Any]]] = {"baseline": [], "treatment": []}
    primary_records: list[dict[str, Any]] = []
    for participant_id in selected_ids:
        first = next(record for record in completions[participant_id] if record["period"] == 1)
        groups[first["arm"]].append(first)
        primary_records.append({
            "arm": first["arm"],
            "assignment": first["assignment"],
            "confidence_percent": first["response"]["confidence_percent"],
            "elapsed_monotonic_ns": first["elapsed_monotonic_ns"],
            "materials_opened_count": len(first["materials_opened"]),
            "participant_id": participant_id,
            "period_record_root": first["period_record_root"],
            "score": first["score"],
        })
    group_results: dict[str, Any] = {}
    for arm, records in groups.items():
        totals = [record["score"]["deterministic_total"] for record in records]
        component_sums = {
            name: sum(record["score"]["components"][name] for record in records)
            for name in COMPONENT_NAMES
        }
        group_results[arm] = {
            "component_sums": component_sums,
            "count": len(records),
            "score_sum": sum(totals),
            "score_mean_fraction": [sum(totals), len(records)] if records else [0, 0],
        }
    baseline, treatment = group_results["baseline"], group_results["treatment"]
    if baseline["count"] and treatment["count"]:
        difference = [treatment["score_sum"] * baseline["count"] - baseline["score_sum"] * treatment["count"], treatment["count"] * baseline["count"]]
    else:
        difference = [0, 0]
    cutoff = protocol.parse_time(instrument["assignment_schedule"]["completion_cutoff"])
    status = "complete" if len(selected_ids) >= target else ("incomplete_at_frozen_cutoff" if as_of_time > cutoff else "in_progress")
    result = {
        "analysis": {
            "first_period_groups": group_results,
            "first_period_records": primary_records,
            "primary_difference_treatment_minus_baseline_fraction": difference,
            "selected_participant_ids": selected_ids,
        },
        "as_of": as_of,
        "authority_effect": "none",
        "audit": audit_result,
        "format": REPORT_FORMAT,
        "instrument_root": instrument["content_root"],
        "limitations": [
            "Second-period responses are excluded from the primary estimator.",
            "Correct answers do not establish acceptance, adoption, scientific lift, or reviewer efficiency.",
            "The public instrument is not blinded or held out.",
        ],
        "plan_root": plan["content_root"],
        "run_id": manifest["run_id"],
        "status": status,
        "withdrawn_participant_ids": withdrawn,
    }
    result["content_root_definition"] = "sha256 of RFC-8785 JSON after removing only content_root"
    result["content_root"] = protocol.canonical_root(result)
    return result


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("directory", type=Path)
    init.add_argument("--custodian", required=True)
    enroll_parser = commands.add_parser("enroll")
    enroll_parser.add_argument("directory", type=Path)
    enroll_parser.add_argument("--participant-id", required=True)
    enroll_parser.add_argument("--attestation", type=Path, required=True)
    enroll_parser.add_argument("--occurred-at", required=True)
    period = commands.add_parser("record-period")
    period.add_argument("directory", type=Path)
    period.add_argument("--participant-id", required=True)
    period.add_argument("--response", type=Path, required=True)
    period.add_argument("--opened-materials", type=Path, required=True)
    period.add_argument("--lean-proofs-repo", type=Path, required=True)
    period.add_argument("--timer-started-at", required=True)
    period.add_argument("--timer-stopped-at", required=True)
    period.add_argument("--monotonic-started-ns", type=int, required=True)
    period.add_argument("--monotonic-stopped-ns", type=int, required=True)
    period.add_argument("--occurred-at", required=True)
    withdrawn = commands.add_parser("withdraw")
    withdrawn.add_argument("directory", type=Path)
    withdrawn.add_argument("--participant-id", required=True)
    withdrawn.add_argument("--reason-code", required=True)
    withdrawn.add_argument("--occurred-at", required=True)
    template = commands.add_parser("opened-materials")
    template.add_argument("directory", type=Path)
    template.add_argument("--participant-id", required=True)
    template.add_argument("--opened-at", required=True)
    for name in ("audit", "analyze"):
        command = commands.add_parser(name)
        command.add_argument("directory", type=Path)
        command.add_argument("--lean-proofs-repo", type=Path, required=True)
        if name == "analyze":
            command.add_argument("--as-of", required=True)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "init":
        result = init_run(args.directory, args.custodian)
    elif args.command == "enroll":
        result = enroll(args.directory, args.participant_id, args.attestation, args.occurred_at)
    elif args.command == "record-period":
        result = record_period(args.directory, args.participant_id, args.response, args.opened_materials, args.lean_proofs_repo, args.timer_started_at, args.timer_stopped_at, args.monotonic_started_ns, args.monotonic_stopped_ns, args.occurred_at)
    elif args.command == "withdraw":
        result = withdraw(args.directory, args.participant_id, args.reason_code, args.occurred_at)
    elif args.command == "opened-materials":
        result = opened_materials_template(args.directory, args.participant_id, args.opened_at)
    elif args.command == "audit":
        result = audit(args.directory, args.lean_proofs_repo)
    else:
        result = analyze(args.directory, args.lean_proofs_repo, args.as_of)
    sys.stdout.buffer.write(jcs(result) + b"\n")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RunError, protocol.ProtocolError, scorer.ScoreError, OSError, subprocess.SubprocessError) as error:
        print(f"reader_run_refused: {error}", file=sys.stderr)
        raise SystemExit(1) from error
