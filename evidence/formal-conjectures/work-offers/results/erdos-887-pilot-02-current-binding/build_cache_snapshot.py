#!/usr/bin/env python3
"""Root the two public compiled artifacts used by the Erdős 887 replay."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
SNAPSHOTS = HERE / "public-cache-snapshots"
OUTPUT = HERE / "public-cache-snapshot.v1.json"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def raw_descriptor(name: str) -> dict[str, Any]:
    path = SNAPSHOTS / name
    raw = path.read_bytes()
    return {
        "path": str(path.relative_to(HERE)),
        "raw_sha256": "sha256:" + hashlib.sha256(raw).hexdigest(),
        "size": len(raw),
    }


def rooted(value: dict[str, Any]) -> str:
    preimage = copy.deepcopy(value)
    preimage.pop("cache_snapshot_root", None)
    return "sha256:" + hashlib.sha256(canonical(preimage)).hexdigest()


def build() -> dict[str, Any]:
    leansearch_url = (
        "https://reservoir.lean-lang.org/api/v1/packages/leanprover-community/"
        "LeanSearchClient/barrel?rev=99657ad92e23804e279f77ea6dbdeebaa1317b98&"
        "toolchain=leanprover%2Flean4%3Av4.22.0"
    )
    proofwidgets_url = (
        "https://github.com/leanprover-community/ProofWidgets4/releases/download/"
        "v0.0.68/ProofWidgets4.tar.gz"
    )
    value: dict[str, Any] = {
        "schema": "vela.math.public-compiled-cache-snapshot.v1",
        "authority_effect": "none",
        "custody": {
            "access": "public",
            "participant_private_data_allowed": False,
            "selective_snapshot": True,
        },
        "artifacts": [
            {
                "id": "leansearchclient-reservoir-barrel",
                "package": "LeanSearchClient",
                "package_revision": "99657ad92e23804e279f77ea6dbdeebaa1317b98",
                "toolchain": "leanprover/lean4:v4.22.0",
                "public_url": leansearch_url,
                "request_headers": {
                    "X-Lake-Registry-Api-Version": "0.1.0",
                    "X-Reservoir-Api-Version": "1.0.0",
                },
                "snapshot": raw_descriptor("LeanSearchClient-build.barrel"),
                "normalized_acquisition_command_metadata": {
                    "command": ["curl", "-s", "-S", "-f", "-o", "$OUTPUT", "-L", leansearch_url],
                    "observed_from": "Lake trace normalized to remove the runtime-local output path",
                    "http_status": "not_retained_by_original_trace",
                    "final_url": "not_retained_by_original_trace",
                },
            },
            {
                "id": "proofwidgets-github-release-archive",
                "package": "proofwidgets",
                "package_revision": "1253a071e6939b0faf5c09d2b30b0bfc79dae407",
                "release_tag": "v0.0.68",
                "toolchain": "leanprover/lean4:v4.22.0-rc4",
                "public_url": proofwidgets_url,
                "request_headers": {},
                "snapshot": raw_descriptor("ProofWidgets4.tar.gz"),
                "normalized_acquisition_command_metadata": {
                    "command": ["curl", "-s", "-S", "-f", "-o", "$OUTPUT", "-L", proofwidgets_url],
                    "observed_from": "Lake trace normalized to remove the runtime-local output path",
                    "http_status": "not_retained_by_original_trace",
                    "final_url": "not_retained_by_original_trace",
                },
            },
        ],
        "replay_metadata": {
            "source": "canonical normalized Lake acquisition-command metadata; raw traces are intentionally excluded because they contain runtime-local private paths",
            "network_required_for_replay": False,
            "materialization": "validated Python standard-library tarfile extraction into each package .lake/build directory",
        },
        "nonclaims": [
            "These public compiled artifacts are selectively retained replay inputs, not source-build evidence.",
            "Their use does not establish independent reproduction, scientific correctness, Vela Verification, Decision, or Standing.",
        ],
        "cache_snapshot_root_definition": "sha256 of canonical JSON after removing only cache_snapshot_root",
    }
    value["cache_snapshot_root"] = rooted(value)
    if b"/private/" in canonical(value) or b"/Users/" in canonical(value):
        raise ValueError("public cache snapshot contains a private local path")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    raw = canonical(build()) + b"\n"
    if args.check:
        if OUTPUT.read_bytes() != raw:
            raise SystemExit("public cache snapshot bytes drifted")
    else:
        OUTPUT.write_bytes(raw)
    print(build()["cache_snapshot_root"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
