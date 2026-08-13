#!/usr/bin/env python3
"""Root the pre-inference invalid-schema attempt."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
FAILED = HERE / "failed-attempt-01-invalid-schema"
OUTPUT = FAILED / "failure-manifest.v0.2.json"


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def main() -> None:
    files = []
    terminal_states = {}
    model_outputs = 0
    for path in sorted((FAILED / "runs").glob("*")):
        data = path.read_bytes()
        files.append({"path": path.relative_to(REPO).as_posix(), "size": len(data), "raw_sha256": digest(data)})
        if path.name.endswith(".observation.json"):
            value = json.loads(data)
            terminal_states[value["terminal_state"]] = terminal_states.get(value["terminal_state"], 0) + 1
            model_outputs += int(value["output"] is not None)
    document = {
        "schema": "vela.math.fc-audit.handoff-revision-failed-attempt.v0.2",
        "authority_effect": "none",
        "attempt": "failed-attempt-01-invalid-schema",
        "observation_count": sum(terminal_states.values()),
        "terminal_states": terminal_states,
        "model_output_count": model_outputs,
        "files": files,
        "does_not_establish": [
            "No model outcome was observed.",
            "The failure is an execution finding, not evidence about either handoff interface."
        ]
    }
    document["failure_root"] = digest(canonical(document))
    OUTPUT.write_text(json.dumps(document, indent=2) + "\n")


if __name__ == "__main__":
    main()
