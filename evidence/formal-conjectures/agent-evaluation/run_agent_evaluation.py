#!/usr/bin/env python3
"""Run the predeclared attributed agent sender/receiver evaluation."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import time
from typing import Any

import jsonschema


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ALLOCATION_PATH = HERE / "agent-allocation.v0.1.json"
SENDER_SCHEMA_PATH = HERE / "sender-output.schema.v0.1.json"
RECEIVER_SCHEMA_PATH = HERE / "receiver-output.schema.v0.1.json"
RUNS_DIR = HERE / "runs"
MODEL = "gpt-5.6-sol"
RUNTIME = "codex-cli 0.145.0"
REASONING_EFFORT = "high"
DISABLED_FEATURES = [
    "plugins",
    "apps",
    "memories",
    "browser_use",
    "in_app_browser",
    "computer_use",
    "image_generation",
    "goals",
    "workspace_dependencies",
    "multi_agent",
    "shell_tool",
    "unified_exec",
]


def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_json(text: str) -> object:
    return json.loads(text, object_pairs_hook=reject_duplicate_keys)


def load_json(path: Path) -> object:
    return parse_json(path.read_text(encoding="utf-8"))


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def semantic_root(value: dict[str, object], field: str) -> str:
    unrooted = dict(value)
    unrooted.pop(field, None)
    return "sha256:" + hashlib.sha256(canonical_bytes(unrooted)).hexdigest()


def raw_sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def file_stem(assignment: dict[str, object]) -> str:
    return f"slot-{assignment['slot']:02d}--task-{assignment['task_order']:02d}--fixture-{assignment['fixture_position']:02d}"


def normalize_public_log(text: str, task_dir: str) -> str:
    normalized = text.replace(str(Path.home()), "$USER_HOME")
    normalized = normalized.replace(task_dir, "$TASK_DIR")
    return normalized


def role_prompt(role: str, assignment: dict[str, object], bundle: dict[str, object], sender_output: dict[str, object] | None, sender_digest: str | None) -> str:
    common = (
        "You are one fresh, attributed AI review task context in a frozen evaluation. "
        "Actor class is provenance, not a quality rank. Use only the JSON material below. "
        "Do not call tools, browse, use memory, inspect a repository, or infer private context. "
        "Separate mechanical status, source fidelity, artifact availability, community status, and authority. "
        "A pass, review, merge, audit disposition, or Git commit is not acceptance or Standing. "
        "Return exactly one JSON object matching the supplied output schema. Do not wrap it in Markdown. "
        f"The exact task-context identity is {assignment[f'{role}_task_context_id']}. "
    )
    if role == "sender":
        instruction = (
            "Review the exact fixture. Give a witness-backed advisory verdict. Use issue code "
            "conditional_proof_dependency only for a retained proof dependency; answer_slot_scope only "
            "for quantifier/binder scope changing the stated answer; vacuous_hypothesis only for an "
            "unsatisfiable or vacuous boundary; exact_artifact_identity_unavailable only when exact "
            "external proof identity cannot be resolved; use other only for a different concrete issue. "
            "An empty issue_codes list is valid. Preserve uncertainty rather than guessing."
        )
        material: dict[str, object] = {"assignment": assignment, "bundle": bundle}
    else:
        instruction = (
            "Continue from the sender output using only the same rooted condition bundle. Preserve or "
            "correct its layer-separated classification, state what can be reproduced or only scoped, "
            "list missing provenance, and identify the next obligation. Do not merely endorse the sender."
        )
        material = {
            "assignment": assignment,
            "bundle": bundle,
            "sender_output_sha256": sender_digest,
            "sender_output": sender_output,
        }
    return common + instruction + "\n\nEVALUATION MATERIAL:\n" + json.dumps(material, ensure_ascii=False, sort_keys=True)


def codex_command(schema_path: Path) -> list[str]:
    command = [
        "codex",
        "exec",
        "--ephemeral",
        "--ignore-user-config",
        "--skip-git-repo-check",
        "--sandbox",
        "read-only",
        "--model",
        MODEL,
        "--config",
        f'model_reasoning_effort="{REASONING_EFFORT}"',
    ]
    for feature in DISABLED_FEATURES:
        command.extend(["--disable", feature])
    command.extend(["--output-schema", str(schema_path), "--json", "-"])
    return command


def execute_role(role: str, assignment: dict[str, object]) -> dict[str, object]:
    stem = file_stem(assignment)
    role_dir = RUNS_DIR / role
    observation_path = role_dir / f"{stem}.observation.json"
    output_path = role_dir / f"{stem}.output.json"
    event_path = role_dir / f"{stem}.events.jsonl"
    stderr_path = role_dir / f"{stem}.stderr.txt"
    if observation_path.exists() or output_path.exists() or event_path.exists() or stderr_path.exists():
        raise ValueError(f"predeclared task already has retained bytes; no retry permitted: {role}/{stem}")
    bundle_path = REPO / assignment["bundle"]["path"]
    bundle_data = bundle_path.read_bytes()
    if raw_sha256(bundle_data) != assignment["bundle"]["raw_sha256"]:
        raise ValueError("assignment bundle raw root drift")
    bundle = parse_json(bundle_data.decode("utf-8"))
    sender_output: dict[str, object] | None = None
    sender_digest: str | None = None
    if role == "receiver":
        sender_dir = RUNS_DIR / "sender"
        sender_observation = load_json(sender_dir / f"{stem}.observation.json")
        if sender_observation["terminal_state"] != "success":
            return retain_blocked_receiver(assignment, sender_observation)
        sender_output_path = REPO / sender_observation["output"]["path"]
        sender_bytes = sender_output_path.read_bytes()
        sender_digest = raw_sha256(sender_bytes)
        if sender_digest != sender_observation["output"]["raw_sha256"]:
            raise ValueError("sender output root drift")
        sender_output = parse_json(sender_bytes.decode("utf-8"))
    schema_path = SENDER_SCHEMA_PATH if role == "sender" else RECEIVER_SCHEMA_PATH
    schema = load_json(schema_path)
    prompt = role_prompt(role, assignment, bundle, sender_output, sender_digest)
    started_at = utc_now()
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix=f"vela-agent-eval-{role}-") as task_dir:
        try:
            completed = subprocess.run(
                codex_command(schema_path),
                input=prompt,
                text=True,
                cwd=task_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=900,
                check=False,
            )
            return_code = completed.returncode
            stdout = normalize_public_log(completed.stdout, task_dir)
            stderr = normalize_public_log(completed.stderr, task_dir)
            terminal_state = "success" if return_code == 0 else "error"
        except subprocess.TimeoutExpired as error:
            return_code = None
            stdout = normalize_public_log(error.stdout or "", task_dir)
            stderr = normalize_public_log(error.stderr or "", task_dir)
            terminal_state = "timeout"
    elapsed = time.monotonic() - started
    completed_at = utc_now()
    events: list[dict[str, object]] = []
    output: dict[str, object] | None = None
    usage: dict[str, object] | None = None
    parse_error: str | None = None
    try:
        for line in stdout.splitlines():
            if not line.strip():
                continue
            event = parse_json(line)
            events.append(event)
            if event.get("type") == "item.completed" and event.get("item", {}).get("type") == "agent_message":
                output = parse_json(event["item"]["text"])
            if event.get("type") == "turn.completed":
                usage = event.get("usage")
        if terminal_state == "success":
            if output is None:
                raise ValueError("no final agent JSON output")
            jsonschema.Draft202012Validator(schema).validate(output)
            if output["fixture_id"] != assignment["fixture_id"]:
                raise ValueError("output fixture drift")
            if output["condition"] != assignment["condition"]:
                raise ValueError("output condition drift")
            if output["packet_root"] != assignment["packet_root"]:
                raise ValueError("output packet root drift")
            issue_field = "issue_codes" if role == "sender" else "retained_issue_codes"
            if len(output[issue_field]) != len(set(output[issue_field])):
                raise ValueError("output repeats an issue code")
            if role == "receiver" and output["sender_output_sha256"] != sender_digest:
                raise ValueError("receiver sender-output root drift")
    except Exception as error:  # retained as an outcome, never retried
        terminal_state = "invalid_output"
        parse_error = f"{type(error).__name__}: {error}"
    role_dir.mkdir(parents=True, exist_ok=True)
    event_bytes = (stdout.rstrip("\n") + "\n").encode()
    stderr_bytes = stderr.encode()
    event_path.write_bytes(event_bytes)
    stderr_path.write_bytes(stderr_bytes)
    output_descriptor: dict[str, object] | None = None
    if output is not None:
        output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        output_bytes = output_path.read_bytes()
        output_descriptor = {
            "path": output_path.relative_to(REPO).as_posix(),
            "size": len(output_bytes),
            "raw_sha256": raw_sha256(output_bytes),
        }
    observation: dict[str, object] = {
        "schema": "vela.math.fc-audit.agent-task-observation.v0.1",
        "observation_id": f"{assignment['handoff_id']}::{role}",
        "role": role,
        "authority_effect": "none",
        "task_context_id": assignment[f"{role}_task_context_id"],
        "slot": assignment["slot"],
        "task_order": assignment["task_order"],
        "fixture_id": assignment["fixture_id"],
        "condition": assignment["condition"],
        "packet_root": assignment["packet_root"],
        "handoff_id": assignment["handoff_id"],
        "runner": {
            "model": MODEL,
            "provider": "openai",
            "runtime": RUNTIME,
            "reasoning_effort": REASONING_EFFORT,
            "session_policy": "fresh_ephemeral_task_context",
            "disabled_features": DISABLED_FEATURES,
            "sandbox": "read-only",
            "working_directory": "empty_temporary_directory_not_retained",
        },
        "independence_classification": "separate_task_context_same_model_provider_runtime_operator",
        "bundle": assignment["bundle"],
        "started_at": started_at,
        "completed_at": completed_at,
        "elapsed_seconds": round(elapsed, 6),
        "terminal_state": terminal_state,
        "return_code": return_code,
        "usage": usage,
        "output": output_descriptor,
        "event_log": {
            "path": event_path.relative_to(REPO).as_posix(),
            "size": len(event_bytes),
            "raw_sha256": raw_sha256(event_bytes),
            "normalization": ["home path replaced with $USER_HOME", "temporary task path replaced with $TASK_DIR"],
        },
        "stderr_log": {
            "path": stderr_path.relative_to(REPO).as_posix(),
            "size": len(stderr_bytes),
            "raw_sha256": raw_sha256(stderr_bytes),
            "normalization": ["home path replaced with $USER_HOME", "temporary task path replaced with $TASK_DIR"],
        },
        "parse_error": parse_error,
        "does_not_establish": [
            "This attributed agent task output is advisory evidence, not acceptance or Standing.",
            "Separate task contexts sharing a model and provider are not institutionally independent."
        ],
    }
    observation["observation_root"] = semantic_root(observation, "observation_root")
    observation_path.write_text(json.dumps(observation, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return observation


def retain_blocked_receiver(assignment: dict[str, object], sender_observation: dict[str, object]) -> dict[str, object]:
    stem = file_stem(assignment)
    receiver_dir = RUNS_DIR / "receiver"
    receiver_dir.mkdir(parents=True, exist_ok=True)
    observation_path = receiver_dir / f"{stem}.observation.json"
    if observation_path.exists():
        raise ValueError(f"receiver observation already exists: {stem}")
    now = utc_now()
    observation: dict[str, object] = {
        "schema": "vela.math.fc-audit.agent-task-observation.v0.1",
        "observation_id": f"{assignment['handoff_id']}::receiver",
        "role": "receiver",
        "authority_effect": "none",
        "task_context_id": assignment["receiver_task_context_id"],
        "slot": assignment["slot"],
        "task_order": assignment["task_order"],
        "fixture_id": assignment["fixture_id"],
        "condition": assignment["condition"],
        "packet_root": assignment["packet_root"],
        "handoff_id": assignment["handoff_id"],
        "runner": None,
        "independence_classification": "not_evaluated_sender_failed",
        "bundle": assignment["bundle"],
        "started_at": now,
        "completed_at": now,
        "elapsed_seconds": None,
        "terminal_state": "blocked_sender_failure",
        "return_code": None,
        "usage": None,
        "output": None,
        "event_log": None,
        "stderr_log": None,
        "parse_error": f"sender terminal state: {sender_observation['terminal_state']}",
        "does_not_establish": [
            "No receiver task ran, so missing duration and outcome are not zero.",
            "This record has no authority or Standing effect."
        ],
    }
    observation["observation_root"] = semantic_root(observation, "observation_root")
    observation_path.write_text(json.dumps(observation, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return observation


def run_role(role: str, assignments: list[dict[str, object]], workers: int) -> None:
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(execute_role, role, assignment): assignment for assignment in assignments}
        for completed_count, future in enumerate(as_completed(futures), start=1):
            assignment = futures[future]
            observation = future.result()
            print(
                f"[{role} {completed_count:02d}/{len(assignments)}] "
                f"slot={assignment['slot']} fixture={assignment['fixture_id']} "
                f"condition={assignment['condition']} state={observation['terminal_state']} "
                f"seconds={observation['elapsed_seconds']}",
                flush=True,
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    if not 1 <= args.workers <= 6:
        raise ValueError("workers must be in 1..6")
    allocation = load_json(ALLOCATION_PATH)
    if allocation["allocation_root"] != semantic_root(allocation, "allocation_root"):
        raise ValueError("allocation root drift")
    assignments = allocation["assignments"]
    if len(assignments) != 30:
        raise ValueError("evaluation requires exactly 30 predeclared assignments")
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    run_role("sender", assignments, args.workers)
    run_role("receiver", assignments, args.workers)


if __name__ == "__main__":
    main()
