#!/usr/bin/env python3
"""Run the frozen paired handoff receiver evaluation."""

from __future__ import annotations

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
REPO = HERE.parents[3]
ALLOCATION = HERE / "handoff-revision-allocation.v0.2.json"
SCHEMA_PATH = HERE / "receiver-output.schema.v0.2.json"
AMENDMENT_PATH = HERE / "execution-amendment.v0.2.json"
RUNS = HERE / "runs"
MODEL = "gpt-5.6-sol"
RUNTIME = "codex-cli 0.145.0"
DISABLED = ["plugins", "apps", "memories", "browser_use", "in_app_browser", "computer_use", "image_generation", "goals", "workspace_dependencies", "multi_agent", "shell_tool", "unified_exec"]


def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate key: {key}")
        value[key] = item
    return value


def load(path: Path) -> Any:
    return json.loads(path.read_text(), object_pairs_hook=reject_duplicates)


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def semantic_root(value: dict[str, Any], field: str) -> str:
    unrooted = dict(value)
    unrooted.pop(field, None)
    return digest(canonical(unrooted))


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def safe_load(descriptor: dict[str, Any]) -> Any:
    path = REPO / descriptor["path"]
    data = path.read_bytes()
    if len(data) != descriptor["size"] or digest(data) != descriptor["raw_sha256"]:
        raise ValueError("retained input drift")
    return json.loads(data, object_pairs_hook=reject_duplicates)


def command() -> list[str]:
    result = ["codex", "exec", "--ephemeral", "--ignore-user-config", "--skip-git-repo-check", "--sandbox", "read-only", "--model", MODEL, "--config", 'model_reasoning_effort="high"']
    for feature in DISABLED:
        result.extend(["--disable", feature])
    result.extend(["--output-schema", str(SCHEMA_PATH), "--json", "-"])
    return result


def run_one(assignment: dict[str, Any]) -> dict[str, Any]:
    pair_slug = assignment["pair_id"].replace("agent-eval-handoff-", "").replace("::handoff-revision-v0.2", "")
    stem = f"{pair_slug}--{assignment['condition']}"
    observation_path = RUNS / f"{stem}.observation.json"
    output_path = RUNS / f"{stem}.output.json"
    events_path = RUNS / f"{stem}.events.jsonl"
    stderr_path = RUNS / f"{stem}.stderr.txt"
    if any(path.exists() for path in [observation_path, output_path, events_path, stderr_path]):
        raise ValueError(f"no retry permitted: {stem}")
    sender = safe_load(assignment["sender_output"])
    bundle = safe_load(assignment["bundle"])
    compact = safe_load(assignment["compact_handoff"])
    if assignment["condition"] == "legacy_full_audit_handoff":
        material = {"sender_output": sender, "full_audit_bundle": bundle}
    else:
        material = {"compact_handoff": compact}
    source = bundle["public_source"]
    binding = {
        "source_commit": source["commit"],
        "source_path": source["source_path"],
        "source_raw_sha256": source["raw_sha256"],
        "sender_output_sha256": assignment["sender_output"]["raw_sha256"],
        "original_packet_root": assignment["packet_root"],
        "authority_effect": "none",
    }
    prompt = (
        "You are a fresh attributed AI receiver in a frozen paired evaluation. Actor class is provenance, not a quality rank. "
        "Use only the supplied JSON. Do not call tools, browse, use memory, or inspect a repository. Continue the exact sender review. "
        "Confirm or correct the verdict and issue codes, bind every provenance field from EXPECTED BINDINGS, state the immediate next action, "
        "and preserve authority limits. evidence_locators_retained is true only if the material retains exact evidence locators supporting the review. "
        "A review, check, merge, or commit is not acceptance or Standing. Return one JSON object matching the schema, without Markdown. "
        f"Your task-context identity is {assignment['receiver_task_context_id']}.\n\n"
        + json.dumps({"assignment": assignment, "expected_bindings": binding, "material": material}, ensure_ascii=False, sort_keys=True)
    )
    started_at = now()
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="vela-handoff-v02-") as temp:
        completed = subprocess.run(command(), input=prompt, text=True, cwd=temp, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=900, check=False)
        stdout = completed.stdout.replace(str(Path.home()), "$USER_HOME").replace(temp, "$TASK_DIR")
        stderr = completed.stderr.replace(str(Path.home()), "$USER_HOME").replace(temp, "$TASK_DIR")
    elapsed = time.monotonic() - started
    events: list[dict[str, Any]] = []
    output: dict[str, Any] | None = None
    usage: dict[str, Any] | None = None
    terminal = "success" if completed.returncode == 0 else "error"
    parse_error: str | None = None
    try:
        for line in stdout.splitlines():
            if not line.strip():
                continue
            event = json.loads(line, object_pairs_hook=reject_duplicates)
            events.append(event)
            if event.get("type") == "item.completed" and event.get("item", {}).get("type") == "agent_message":
                output = json.loads(event["item"]["text"], object_pairs_hook=reject_duplicates)
            if event.get("type") == "turn.completed":
                usage = event.get("usage")
        if terminal == "success":
            if output is None:
                raise ValueError("missing output")
            jsonschema.Draft202012Validator(load(SCHEMA_PATH)).validate(output)
            if len(output["retained_issue_codes"]) != len(set(output["retained_issue_codes"])):
                raise ValueError("output repeats an issue code")
            expected = {
                "fixture_id": assignment["fixture_id"],
                "condition": assignment["condition"],
                "packet_root": assignment["packet_root"],
                "sender_output_sha256": assignment["sender_output"]["raw_sha256"],
            }
            for key, value in expected.items():
                if output[key] != value:
                    raise ValueError(f"output {key} drift")
    except Exception as error:
        terminal = "invalid_output"
        parse_error = f"{type(error).__name__}: {error}"
    RUNS.mkdir(exist_ok=True)
    events_data = (stdout.rstrip("\n") + "\n").encode()
    stderr_data = stderr.encode()
    events_path.write_bytes(events_data)
    stderr_path.write_bytes(stderr_data)
    output_descriptor = None
    if output is not None:
        output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
        data = output_path.read_bytes()
        output_descriptor = {"path": output_path.relative_to(REPO).as_posix(), "size": len(data), "raw_sha256": digest(data)}
    observation: dict[str, Any] = {
        "schema": "vela.math.fc-audit.handoff-revision-observation.v0.2",
        "authority_effect": "none",
        "observation_id": assignment["pair_id"] + "::" + assignment["condition"],
        "pair_id": assignment["pair_id"],
        "fixture_id": assignment["fixture_id"],
        "condition": assignment["condition"],
        "task_context_id": assignment["receiver_task_context_id"],
        "packet_root": assignment["packet_root"],
        "runner": {"model": MODEL, "runtime": RUNTIME, "reasoning_effort": "high"},
        "execution_amendment": {"path": AMENDMENT_PATH.relative_to(REPO).as_posix(), "raw_sha256": digest(AMENDMENT_PATH.read_bytes())},
        "started_at": started_at,
        "completed_at": now(),
        "elapsed_seconds": elapsed,
        "terminal_state": terminal,
        "return_code": completed.returncode,
        "usage": usage,
        "output": output_descriptor,
        "events": {"path": events_path.relative_to(REPO).as_posix(), "size": len(events_data), "raw_sha256": digest(events_data)},
        "stderr": {"path": stderr_path.relative_to(REPO).as_posix(), "size": len(stderr_data), "raw_sha256": digest(stderr_data)},
        "parse_error": parse_error,
    }
    observation["observation_root"] = semantic_root(observation, "observation_root")
    observation_path.write_text(json.dumps(observation, indent=2) + "\n")
    return observation


def main() -> None:
    allocation = load(ALLOCATION)
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(run_one, assignment) for assignment in allocation["assignments"]]
        for future in as_completed(futures):
            result = future.result()
            print(result["observation_id"], result["terminal_state"], flush=True)


if __name__ == "__main__":
    main()
