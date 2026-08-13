#!/usr/bin/env python3
"""Retain the five exact public source files used by the agent evaluation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PACKETS_PATH = REPO / "evidence/formal-conjectures/audit-pilot/condition-packet-set.v0.1.json"
OUTPUT_DIR = HERE / "public-source"
MANIFEST_PATH = HERE / "public-source-manifest.v0.1.json"


def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_keys)


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def root(value: object) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(value)).hexdigest()


def git_blob_sha1(data: bytes) -> str:
    framed = f"blob {len(data)}\0".encode() + data
    return hashlib.sha1(framed, usedforsecurity=False).hexdigest()


def source_records() -> list[dict[str, object]]:
    packets = load_json(PACKETS_PATH)
    by_fixture: dict[str, dict[str, object]] = {}
    for packet in packets["packets"]:
        fixture_id = packet["fixture_id"]
        if fixture_id in by_fixture:
            continue
        command = packet["public_source_command"]
        if command[:4] != ["git", "-C", "$SOURCE_CHECKOUT", "show"] or len(command) != 5:
            raise ValueError(f"unsupported source command for {fixture_id}")
        revision_path = command[4]
        commit, source_path = revision_path.split(":", 1)
        files_path = REPO / packet["pull_request"]["files_observation"]["path"]
        files = load_json(files_path)["files"]
        matching = [item for item in files if item["filename"] == source_path]
        if len(matching) != 1:
            raise ValueError(f"exact changed source is not unique for {fixture_id}")
        by_fixture[fixture_id] = {
            "fixture_id": fixture_id,
            "repository": packet["pull_request"]["repository"],
            "commit": commit,
            "source_path": source_path,
            "git_blob_sha1": matching[0]["sha"],
            "source_url": (
                "https://raw.githubusercontent.com/google-deepmind/formal-conjectures/"
                f"{commit}/{source_path}"
            ),
        }
    return [by_fixture[key] for key in sorted(by_fixture)]


def main() -> None:
    artifacts: list[dict[str, object]] = []
    for source in source_records():
        local_path = Path("evidence/formal-conjectures/agent-evaluation/public-source") / source["fixture_id"] / Path(source["source_path"]).name
        output_path = REPO / local_path
        if output_path.exists():
            data = output_path.read_bytes()
        else:
            acquisition = subprocess.run(
                [
                    "curl",
                    "--fail",
                    "--location",
                    "--silent",
                    "--show-error",
                    "--max-time",
                    "30",
                    "--user-agent",
                    "vela-math-agent-evaluation/0.1",
                    source["source_url"],
                ],
                check=True,
                stdout=subprocess.PIPE,
            )
            data = acquisition.stdout
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(data)
        actual_blob = git_blob_sha1(data)
        if actual_blob != source["git_blob_sha1"]:
            raise ValueError(f"Git blob drift for {source['fixture_id']}: {actual_blob}")
        artifacts.append(
            {
                **source,
                "local_path": local_path.as_posix(),
                "size": len(data),
                "raw_sha256": "sha256:" + hashlib.sha256(data).hexdigest(),
            }
        )
    document: dict[str, object] = {
        "schema": "vela.math.fc-audit.agent-public-source-manifest.v0.1",
        "authority_effect": "none",
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "nonclaims": [
            "The retained bytes do not establish source fidelity or correctness.",
            "Public availability does not create Verification, Decision, or Standing."
        ],
    }
    document["manifest_root"] = root(document)
    MANIFEST_PATH.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
