#!/usr/bin/env python3
"""Deterministic, non-Protocol evaluator for the Erdős 321 frozen replay pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

PILOT = Path(__file__).resolve().parent
TASK = PILOT / "candidate" / "task.json"
RESPONSE_SCHEMA = PILOT / "candidate" / "response.schema.json"
ADJUDICATION = PILOT / "protected" / "adjudication.json"
HASH = re.compile(r"^sha256:[0-9a-f]{64}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
CLAIM_ID = re.compile(r"^vcl_[0-9a-f]{64}$")


class PilotError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode()


def pretty_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode()


def digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def load_json(path: Path, code: str = "malformed_json") -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PilotError(code, f"cannot read exact JSON {path}: {error}") from error
    if not isinstance(value, dict):
        raise PilotError(code, f"expected a JSON object at {path}")
    return value


def require_keys(value: dict[str, Any], keys: set[str], context: str) -> None:
    missing = sorted(keys - value.keys())
    if missing:
        raise PilotError(
            "missing_root",
            f"{context} is missing required fields: {', '.join(missing)}",
        )


def repository_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=PILOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(result.stdout.strip())


def git(*arguments: str) -> bytes:
    try:
        result = subprocess.run(
            ["git", *arguments],
            cwd=repository_root(),
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as error:
        detail = error.stderr.decode(errors="replace").strip()
        raise PilotError(
            "missing_git_object", f"git {' '.join(arguments)} failed: {detail}"
        ) from error
    return result.stdout


def git_text(*arguments: str) -> str:
    return git(*arguments).decode().strip()


def validate_root(value: Any, context: str) -> str:
    if not isinstance(value, str) or not HASH.fullmatch(value):
        raise PilotError("missing_root", f"{context} must be an exact sha256 root")
    return value


def validate_commit(value: Any, context: str) -> str:
    if not isinstance(value, str) or not COMMIT.fullmatch(value):
        raise PilotError(
            "wrong_period", f"{context} must be an exact 40-byte Git identity"
        )
    return value


def verify_git_entry(commit: str, entry: dict[str, Any], period: str) -> bytes:
    require_keys(entry, {"bytes", "git_blob", "path", "sha256"}, f"{period} entry")
    path = entry["path"]
    if not isinstance(path, str) or path.startswith("/") or ".." in Path(path).parts:
        raise PilotError("unsafe_path", f"unsafe {period} path: {path!r}")
    payload = git("show", f"{commit}:{path}")
    observed_blob = git_text("rev-parse", f"{commit}:{path}")
    observed = {
        "bytes": len(payload),
        "git_blob": observed_blob,
        "sha256": digest(payload),
    }
    for field, actual in observed.items():
        if entry[field] != actual:
            raise PilotError(
                "mutable_source" if period == "t0" else "protected_outcome_changed",
                f"{period} {path} {field} changed: expected {entry[field]!r}, observed {actual!r}",
            )
    return payload


def verify_replay_receipts(
    adjudication: dict[str, Any], periods: dict[str, dict[str, Any]]
) -> dict[str, str]:
    receipts = adjudication["replay_receipts"]
    if not isinstance(receipts, list) or len(receipts) != len(periods):
        raise PilotError(
            "missing_root", "protected replay receipts must cover t0 and t1 exactly"
        )
    observed_periods: set[str] = set()
    receipt_roots: dict[str, str] = {}
    for entry in receipts:
        if not isinstance(entry, dict) or set(entry) != {
            "bytes",
            "path",
            "period",
            "sha256",
        }:
            raise PilotError(
                "malformed_adjudication", "replay receipt entry has the wrong shape"
            )
        period = entry["period"]
        if period not in periods or period in observed_periods:
            raise PilotError(
                "wrong_period", f"invalid or duplicate replay period: {period!r}"
            )
        observed_periods.add(period)
        relative = entry["path"]
        if (
            not isinstance(relative, str)
            or Path(relative).parts[:2] != ("protected", "replay")
            or Path(relative).is_absolute()
            or ".." in Path(relative).parts
        ):
            raise PilotError("unsafe_path", f"unsafe replay receipt path: {relative!r}")
        path = PILOT / relative
        try:
            payload = path.read_bytes()
        except OSError as error:
            raise PilotError(
                "missing_root", f"cannot read protected replay receipt: {relative}"
            ) from error
        if len(payload) != entry["bytes"] or digest(payload) != entry["sha256"]:
            raise PilotError(
                "protected_outcome_changed",
                f"protected replay receipt changed: {relative}",
            )
        receipt = load_json(path, "malformed_replay_receipt")
        if set(receipt) != {
            "authority_effect",
            "command",
            "format",
            "output",
            "reader",
        }:
            raise PilotError(
                "malformed_replay_receipt",
                f"replay receipt has the wrong shape: {relative}",
            )
        if (
            receipt["authority_effect"] != "none"
            or receipt["format"] != "math.signed-replay-receipt.v1"
            or receipt["reader"] != adjudication["historical_reader"]
            or receipt["command"]
            != ["vela", "replay", f"<detached-{period}-checkout>", "--json"]
        ):
            raise PilotError(
                "malformed_replay_receipt",
                f"replay receipt metadata is invalid: {relative}",
            )
        output = receipt["output"]
        if not isinstance(output, dict):
            raise PilotError(
                "malformed_replay_receipt",
                f"replay output is not an object: {relative}",
            )
        require_keys(
            output,
            {
                "authority_keyset_root",
                "authority_model_root",
                "counts",
                "git_commit",
                "git_tree",
                "ok",
                "origin_id",
                "origin_root",
                "repository_id",
                "repository_root",
                "schema",
            },
            f"{period} replay output",
        )
        declared = periods[period]
        if (
            output["git_commit"] != declared["commit"]
            or output["git_tree"] != declared["tree"]
        ):
            raise PilotError(
                "wrong_period", f"{period} replay receipt does not bind its Git period"
            )
        if output["repository_root"] != declared["repository_root"]:
            raise PilotError(
                "wrong_root",
                f"{period} Repository root does not match its signed replay receipt",
            )
        if (
            output["schema"] != "vela.repository-verification.v3"
            or output["ok"] is not True
        ):
            raise PilotError(
                "malformed_replay_receipt", f"{period} replay did not report success"
            )
        for field in (
            "authority_keyset_root",
            "authority_model_root",
            "origin_root",
            "repository_root",
        ):
            validate_root(output[field], f"{period} replay {field}")
        receipt_roots[period] = entry["sha256"]
    if observed_periods != set(periods):
        raise PilotError("missing_root", "protected replay receipt period is missing")
    return receipt_roots


def verify_fixture(
    task_path: Path = TASK, adjudication_path: Path = ADJUDICATION
) -> dict[str, Any]:
    task = load_json(task_path, "malformed_task")
    adjudication = load_json(adjudication_path, "malformed_adjudication")
    require_keys(
        task,
        {
            "authority_effect",
            "candidate_view",
            "format",
            "t0",
            "task",
        },
        "task",
    )
    require_keys(
        adjudication,
        {
            "authority_effect",
            "expected",
            "format",
            "current_source_anchor",
            "protected_entries",
            "protected_tokens",
            "replay_receipts",
            "t1",
        },
        "adjudication",
    )
    if task["authority_effect"] != "none" or adjudication["authority_effect"] != "none":
        raise PilotError(
            "authority_boundary", "evaluation material must have authority_effect none"
        )

    t0 = task["t0"]
    t1 = adjudication["t1"]
    current = adjudication["current_source_anchor"]
    for name, value in (("t0", t0), ("t1", t1), ("current source anchor", current)):
        if not isinstance(value, dict):
            raise PilotError("missing_root", f"{name} must be an object")
        require_keys(value, {"commit", "tree", "repository_root"}, name)
        validate_commit(value["commit"], f"{name} commit")
        validate_commit(value["tree"], f"{name} tree")
        validate_root(value["repository_root"], f"{name} Repository root")

    t0_commit = t0["commit"]
    t1_commit = t1["commit"]
    if t0_commit == t1_commit:
        raise PilotError("wrong_period", "t0 and t1 must be different commits")
    if git_text("rev-parse", f"{t0_commit}^{{tree}}") != t0["tree"]:
        raise PilotError(
            "wrong_period", "t0 commit does not resolve to the declared tree"
        )
    if git_text("rev-parse", f"{t1_commit}^{{tree}}") != t1["tree"]:
        raise PilotError(
            "wrong_period", "t1 commit does not resolve to the declared tree"
        )
    if git_text("rev-parse", f"{current['commit']}^{{tree}}") != current["tree"]:
        raise PilotError(
            "wrong_period",
            "current source anchor does not resolve to its declared tree",
        )
    ancestry = subprocess.run(
        ["git", "merge-base", "--is-ancestor", t0_commit, t1_commit],
        cwd=repository_root(),
    )
    if ancestry.returncode != 0:
        raise PilotError("wrong_period", "t0 is not an ancestor of protected t1")
    t0_time = int(git_text("show", "-s", "--format=%ct", t0_commit))
    t1_time = int(git_text("show", "-s", "--format=%ct", t1_commit))
    if t0_time >= t1_time:
        raise PilotError(
            "wrong_period", "t0 does not chronologically precede protected t1"
        )

    replay_receipts = verify_replay_receipts(adjudication, {"t0": t0, "t1": t1})

    view = task["candidate_view"]
    if not isinstance(view, dict) or not isinstance(view.get("inclusions"), list):
        raise PilotError("missing_root", "candidate_view.inclusions must be a list")
    inclusions = view["inclusions"]
    protected_entries = adjudication["protected_entries"]
    paths: set[str] = set()
    for entry in inclusions:
        if not isinstance(entry, dict):
            raise PilotError("malformed_task", "each t0 inclusion must be an object")
        if entry.get("path") in paths:
            raise PilotError(
                "duplicate_path", f"duplicate t0 path: {entry.get('path')}"
            )
        paths.add(entry.get("path"))
        verify_git_entry(t0_commit, entry, "t0")
    protected_paths: set[str] = set()
    for entry in protected_entries:
        if not isinstance(entry, dict):
            raise PilotError(
                "malformed_adjudication", "each t1 entry must be an object"
            )
        protected_paths.add(entry.get("path"))
        verify_git_entry(t1_commit, entry, "t1")
    overlap = sorted(paths & protected_paths)
    if overlap:
        raise PilotError(
            "leakage", f"candidate and protected paths overlap: {', '.join(overlap)}"
        )

    task_bytes = task_path.read_bytes()
    schema_bytes = RESPONSE_SCHEMA.read_bytes()
    for token in adjudication["protected_tokens"]:
        if not isinstance(token, str) or not token:
            raise PilotError(
                "malformed_adjudication", "protected tokens must be nonempty strings"
            )
        encoded = token.encode()
        if encoded in task_bytes or encoded in schema_bytes:
            raise PilotError(
                "leakage", f"protected token entered candidate metadata: {token}"
            )

    claim = t0.get("claim")
    if not isinstance(claim, dict):
        raise PilotError("missing_root", "t0 Claim identity is missing")
    require_keys(claim, {"claim_id", "claim_root", "revision", "standing"}, "t0 Claim")
    if not CLAIM_ID.fullmatch(str(claim["claim_id"])):
        raise PilotError("missing_root", "t0 Claim id is malformed")
    validate_root(claim["claim_root"], "t0 Claim root")

    return {
        "adjudication_sha256": digest(adjudication_path.read_bytes()),
        "candidate_paths": sorted(paths),
        "current_source_anchor": current,
        "protected_paths": sorted(protected_paths),
        "replay_receipts": replay_receipts,
        "t0": t0,
        "t1": t1,
        "task_sha256": digest(task_bytes),
    }


def manifest_without_root(entries: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "authority_effect": "none",
        "entries": sorted(entries, key=lambda item: item["path"]),
        "format": "math.time-frozen-replay-candidate-bundle.v1",
    }


def export_bundle(output: Path) -> dict[str, Any]:
    fixture = verify_fixture()
    if output.exists():
        raise PilotError(
            "output_exists", f"refusing to overwrite candidate bundle: {output}"
        )
    output.mkdir(parents=True)
    entries: list[dict[str, Any]] = []

    def write(relative: str, payload: bytes, role: str) -> None:
        destination = output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)
        entries.append(
            {
                "bytes": len(payload),
                "path": relative,
                "role": role,
                "sha256": digest(payload),
            }
        )

    write("task.json", TASK.read_bytes(), "task")
    write("response.schema.json", RESPONSE_SCHEMA.read_bytes(), "response_schema")
    task = load_json(TASK)
    for entry in task["candidate_view"]["inclusions"]:
        payload = git("show", f"{task['t0']['commit']}:{entry['path']}")
        write(f"inputs/{entry['path']}", payload, entry["role"])

    base = manifest_without_root(entries)
    manifest = {**base, "bundle_root": digest(canonical_bytes(base))}
    (output / "bundle-manifest.json").write_bytes(pretty_bytes(manifest))
    verified = verify_bundle(output)
    if verified["task_sha256"] != fixture["task_sha256"]:
        raise PilotError("mutable_source", "exported task differs from the frozen task")
    return verified


def verify_bundle(bundle: Path) -> dict[str, Any]:
    fixture = verify_fixture()
    manifest_path = bundle / "bundle-manifest.json"
    manifest = load_json(manifest_path, "malformed_bundle")
    require_keys(
        manifest,
        {"authority_effect", "bundle_root", "entries", "format"},
        "bundle manifest",
    )
    if manifest["authority_effect"] != "none":
        raise PilotError(
            "authority_boundary", "candidate bundle must have authority_effect none"
        )
    entries = manifest["entries"]
    if not isinstance(entries, list):
        raise PilotError("malformed_bundle", "bundle entries must be a list")
    expected_root = digest(canonical_bytes(manifest_without_root(entries)))
    if manifest["bundle_root"] != expected_root:
        raise PilotError("mutable_source", "candidate bundle root changed")

    expected_paths = {entry["path"] for entry in entries} | {"bundle-manifest.json"}
    actual_paths = {
        str(path.relative_to(bundle)) for path in bundle.rglob("*") if path.is_file()
    }
    if actual_paths != expected_paths:
        missing = sorted(expected_paths - actual_paths)
        extra = sorted(actual_paths - expected_paths)
        raise PilotError(
            "leakage", f"bundle path mismatch; missing={missing}, extra={extra}"
        )

    protected = load_json(ADJUDICATION)
    protected_hashes = {entry["sha256"] for entry in protected["protected_entries"]}
    for entry in entries:
        path = bundle / entry["path"]
        payload = path.read_bytes()
        if len(payload) != entry["bytes"] or digest(payload) != entry["sha256"]:
            raise PilotError(
                "mutable_source", f"candidate byte changed: {entry['path']}"
            )
        if digest(payload) in protected_hashes:
            raise PilotError(
                "leakage",
                f"protected t1 byte entered candidate bundle: {entry['path']}",
            )
        for token in protected["protected_tokens"]:
            if token.encode() in payload:
                raise PilotError(
                    "leakage",
                    f"protected token entered candidate bundle: {entry['path']}",
                )
    if digest((bundle / "task.json").read_bytes()) != fixture["task_sha256"]:
        raise PilotError("mutable_source", "candidate task bytes changed")
    if digest((bundle / "response.schema.json").read_bytes()) != digest(
        RESPONSE_SCHEMA.read_bytes()
    ):
        raise PilotError("mutable_source", "candidate response schema changed")
    return {
        "bundle_root": manifest["bundle_root"],
        "entries": len(entries),
        "task_sha256": fixture["task_sha256"],
    }


def response_contract(response: dict[str, Any], task: dict[str, Any]) -> None:
    keys = {
        "action",
        "format",
        "nonclaims",
        "rationale",
        "refusal_reason",
        "relation",
        "required_evidence",
        "scope",
        "subject_occurrences",
        "target_claim_id",
        "target_claim_root",
        "task_id",
    }
    if set(response) != keys:
        raise PilotError(
            "malformed_output", f"response keys must be exactly {sorted(keys)}"
        )
    if response["format"] != "math.time-frozen-replay-response.v1":
        raise PilotError("malformed_output", "wrong response format")
    if response["task_id"] != task["task"]["task_id"]:
        raise PilotError("malformed_output", "wrong task id")
    if response["action"] not in {"propose_transition", "refuse"}:
        raise PilotError("malformed_output", "unsupported action")
    if response["target_claim_id"] != task["t0"]["claim"]["claim_id"]:
        raise PilotError("malformed_output", "response targets a non-t0 Claim id")
    if response["target_claim_root"] != task["t0"]["claim"]["claim_root"]:
        raise PilotError("malformed_output", "response targets a non-t0 Claim root")
    for field in ("subject_occurrences", "required_evidence", "nonclaims"):
        value = response[field]
        if not isinstance(value, list) or not all(
            isinstance(item, str) for item in value
        ):
            raise PilotError("malformed_output", f"{field} must be a string array")
        if len(set(value)) != len(value):
            raise PilotError("malformed_output", f"{field} contains duplicates")
    if (
        not isinstance(response["rationale"], str)
        or not 1 <= len(response["rationale"]) <= 2000
    ):
        raise PilotError(
            "malformed_output", "rationale must contain 1 to 2000 characters"
        )
    slug = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
    if not isinstance(response["scope"], str) or not slug.fullmatch(response["scope"]):
        raise PilotError("malformed_output", "scope must be a bounded slug")
    for field in ("required_evidence", "nonclaims"):
        if not all(slug.fullmatch(item) for item in response[field]):
            raise PilotError(
                "malformed_output", f"{field} values must be bounded slugs"
            )
    if not all(
        re.fullmatch(r"Erdos321\.[A-Za-z0-9_.]+", item)
        for item in response["subject_occurrences"]
    ):
        raise PilotError(
            "malformed_output",
            "subject occurrence is not a bounded Erdős 321 native id",
        )
    if response["action"] == "propose_transition":
        if (
            not isinstance(response["relation"], str)
            or not slug.fullmatch(response["relation"])
            or response["refusal_reason"] is not None
        ):
            raise PilotError(
                "malformed_output",
                "proposal needs a bounded relation slug and null refusal_reason",
            )
        if response["scope"] == "no_transition":
            raise PilotError(
                "malformed_output", "proposal cannot use no_transition scope"
            )
    else:
        reasons = {
            "ambiguous_occurrence",
            "insufficient_t0_evidence",
            "missing_exact_root",
            "source_unavailable",
        }
        if (
            response["relation"] is not None
            or response["scope"] != "no_transition"
            or response["subject_occurrences"]
        ):
            raise PilotError(
                "malformed_output",
                "refusal must not invent a relation, scope, or occurrence",
            )
        if response["refusal_reason"] not in reasons:
            raise PilotError(
                "malformed_output", "refusal needs an allowed exact reason"
            )


def provenance_contract(
    provenance: dict[str, Any], bundle_root: str, output_sha256: str
) -> None:
    keys = {
        "command",
        "dependencies",
        "environment",
        "format",
        "input_bundle_root",
        "limitations",
        "model",
        "output_sha256",
        "performer",
        "tools",
    }
    if set(provenance) != keys:
        raise PilotError(
            "malformed_provenance", f"provenance keys must be exactly {sorted(keys)}"
        )
    if provenance["format"] != "math.time-frozen-replay-provenance.v1":
        raise PilotError("malformed_provenance", "wrong provenance format")
    if (
        provenance["input_bundle_root"] != bundle_root
        or provenance["output_sha256"] != output_sha256
    ):
        raise PilotError(
            "malformed_provenance",
            "provenance does not bind the exact input and output",
        )
    performer = provenance["performer"]
    if not isinstance(performer, dict) or set(performer) != {"id", "kind"}:
        raise PilotError(
            "malformed_provenance", "performer must have exact id and kind"
        )
    if performer["kind"] not in {
        "human",
        "ai_agent",
        "organization",
        "deterministic_tool",
    }:
        raise PilotError("malformed_provenance", "unsupported peer performer kind")
    if not isinstance(performer["id"], str) or not performer["id"]:
        raise PilotError(
            "malformed_provenance", "performer id must be observable and nonempty"
        )
    model = provenance["model"]
    if model is not None and (
        not isinstance(model, dict) or set(model) != {"name", "provider", "version"}
    ):
        raise PilotError(
            "malformed_provenance", "model must be null or exact provider/name/version"
        )
    if model is not None and any(
        not isinstance(value, str) or not value for value in model.values()
    ):
        raise PilotError(
            "malformed_provenance",
            "model provider/name/version must be nonempty strings",
        )
    command = provenance["command"]
    if not isinstance(command, dict) or set(command) != {
        "argv",
        "exit_code",
        "working_directory",
    }:
        raise PilotError(
            "malformed_provenance",
            "command must capture argv, working directory, and exit code",
        )
    if (
        not isinstance(command["argv"], list)
        or not command["argv"]
        or not all(isinstance(item, str) and item for item in command["argv"])
    ):
        raise PilotError(
            "malformed_provenance", "command argv must be a nonempty string array"
        )
    if not isinstance(command["exit_code"], int) or not isinstance(
        command["working_directory"], str
    ):
        raise PilotError(
            "malformed_provenance",
            "command exit_code or working_directory is malformed",
        )
    if not command["working_directory"]:
        raise PilotError(
            "malformed_provenance", "command working_directory must be observable"
        )
    environment = provenance["environment"]
    if not isinstance(environment, dict) or set(environment) != {
        "architecture",
        "os",
        "runtime",
    }:
        raise PilotError(
            "malformed_provenance",
            "environment must identify OS, architecture, and runtime",
        )
    if any(not isinstance(value, str) or not value for value in environment.values()):
        raise PilotError(
            "malformed_provenance", "environment values must be nonempty strings"
        )
    tools = provenance["tools"]
    if (
        not isinstance(tools, list)
        or not tools
        or any(
            not isinstance(item, dict) or set(item) != {"name", "version"}
            for item in tools
        )
    ):
        raise PilotError(
            "malformed_provenance", "tools must be nonempty name/version objects"
        )
    if any(
        not isinstance(value, str) or not value
        for item in tools
        for value in item.values()
    ):
        raise PilotError(
            "malformed_provenance", "tool names and versions must be nonempty strings"
        )
    for field in ("dependencies", "limitations"):
        if not isinstance(provenance[field], list) or not all(
            isinstance(item, str) and item for item in provenance[field]
        ):
            raise PilotError("malformed_provenance", f"{field} must be a string array")


def metric(status: str, detail: str) -> dict[str, str]:
    return {"detail": detail, "status": status}


def evaluate(
    bundle: Path, response_path: Path, provenance_path: Path
) -> dict[str, Any]:
    fixture = verify_fixture()
    bundle_result = verify_bundle(bundle)
    response = load_json(response_path, "malformed_output")
    provenance = load_json(provenance_path, "malformed_provenance")
    task = load_json(TASK)
    adjudication = load_json(ADJUDICATION)
    response_contract(response, task)
    output_sha256 = digest(response_path.read_bytes())
    provenance_contract(provenance, bundle_result["bundle_root"], output_sha256)

    serialized = json.dumps(response, ensure_ascii=False, sort_keys=True)
    leaked = [
        token for token in adjudication["protected_tokens"] if token in serialized
    ]
    self_references = [
        marker
        for marker in (
            "protected/adjudication",
            "protected/t1",
            "adjudication.json",
            "pilot.py",
        )
        if marker.casefold() in serialized.casefold()
    ]
    expected = adjudication["expected"]
    action = response["action"]
    if action == "refuse":
        dimensions = {
            "proposed_relation": metric(
                "not_applicable", "Candidate made an explicit bounded refusal."
            ),
            "subject_source_occurrence": metric(
                "not_applicable", "Candidate made an explicit bounded refusal."
            ),
            "scope": metric(
                "not_applicable", "Candidate made an explicit bounded refusal."
            ),
            "required_evidence": metric(
                "not_applicable", "Candidate made an explicit bounded refusal."
            ),
            "abstention_refusal": metric(
                "pass", f"Bounded refusal: {response['refusal_reason']}"
            ),
        }
    else:
        target_ok = (
            response["target_claim_id"] == expected["target_claim_id"]
            and response["target_claim_root"] == expected["target_claim_root"]
        )
        dimensions = {
            "proposed_relation": metric(
                "pass"
                if response["relation"] == expected["relation"] and target_ok
                else "fail",
                "Compared exact relation and t0 target identity.",
            ),
            "subject_source_occurrence": metric(
                "pass"
                if set(response["subject_occurrences"])
                == set(expected["subject_occurrences"])
                else "fail",
                "Compared the exact set of source-native occurrences retained at protected t1.",
            ),
            "scope": metric(
                "pass" if response["scope"] == expected["scope"] else "fail",
                "Compared only the bounded correction scope, not mathematical truth.",
            ),
            "required_evidence": metric(
                "pass"
                if set(response["required_evidence"])
                == set(expected["required_evidence"])
                else "fail",
                "Compared the exact scoped checks later required before Decision.",
            ),
            "abstention_refusal": metric(
                "pass"
                if set(expected["minimum_nonclaims"]) <= set(response["nonclaims"])
                else "fail",
                "Proposal must explicitly abstain from the larger protected nonclaims.",
            ),
        }
    dimensions["hindsight_leakage"] = metric(
        "pass" if not leaked else "fail",
        "No protected t1 token detected."
        if not leaked
        else f"Detected {len(leaked)} protected token(s).",
    )
    dimensions["evaluator_self_reference"] = metric(
        "pass" if not self_references else "fail",
        "No scorer-only path or implementation reference detected."
        if not self_references
        else f"Detected scorer references: {', '.join(self_references)}",
    )
    eligible = not leaked and not self_references
    pass_count = sum(item["status"] == "pass" for item in dimensions.values())
    fail_count = sum(item["status"] == "fail" for item in dimensions.values())
    score: dict[str, Any] = {
        "authority_effect": "none",
        "dimensions": dimensions,
        "eligible": eligible,
        "format": "math.time-frozen-replay-score.v1",
        "input_bundle_root": bundle_result["bundle_root"],
        "limitations": [
            "This is an exact fixture comparison, not a truth, acceptance, model-quality, or generalization score.",
            "Identity kind has no weight; method, inputs, output, scope, and disclosed dependencies are the observable basis.",
        ],
        "provenance_sha256": digest(provenance_path.read_bytes()),
        "response_sha256": output_sha256,
        "summary": {
            "fail": fail_count,
            "not_applicable": sum(
                item["status"] == "not_applicable" for item in dimensions.values()
            ),
            "pass": pass_count,
        },
        "task_sha256": fixture["task_sha256"],
    }
    score["score_root"] = digest(canonical_bytes(score))
    return score


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("verify")
    export_parser = subparsers.add_parser("export")
    export_parser.add_argument("--output", type=Path, required=True)
    bundle_parser = subparsers.add_parser("verify-bundle")
    bundle_parser.add_argument("--bundle", type=Path, required=True)
    evaluate_parser = subparsers.add_parser("evaluate")
    evaluate_parser.add_argument("--bundle", type=Path, required=True)
    evaluate_parser.add_argument("--response", type=Path, required=True)
    evaluate_parser.add_argument("--provenance", type=Path, required=True)
    evaluate_parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    try:
        if arguments.command == "verify":
            result = verify_fixture()
        elif arguments.command == "export":
            result = export_bundle(arguments.output)
        elif arguments.command == "verify-bundle":
            result = verify_bundle(arguments.bundle)
        else:
            result = evaluate(
                arguments.bundle, arguments.response, arguments.provenance
            )
            if arguments.output:
                arguments.output.parent.mkdir(parents=True, exist_ok=True)
                arguments.output.write_bytes(pretty_bytes(result))
        print(pretty_bytes({"ok": True, **result}).decode(), end="")
        return 0
    except (PilotError, subprocess.CalledProcessError) as error:
        code = error.code if isinstance(error, PilotError) else "internal_error"
        print(
            pretty_bytes(
                {"error": {"code": code, "message": str(error)}, "ok": False}
            ).decode(),
            end="",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
