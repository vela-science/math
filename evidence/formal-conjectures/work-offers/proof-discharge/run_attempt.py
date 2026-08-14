#!/usr/bin/env python3
"""Prepare a clean exact-source workspace for the Erdős 887 proof attempt."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]
INDEX_PATH = HERE.parent / "index.v1.json"
OFFER_BUILDER = HERE.parent / "build.py"
TARGET_ID = "erdos:887:proof-discharge"
SOURCE_REPOSITORY = "https://github.com/google-deepmind/formal-conjectures.git"
SOURCE_COMMIT = "158727e43d3be335f902ac7ef6b9beb819e38c9d"
SOURCE_TREE = "80d17febad5b2f724165561f5af74e19156e34d5"
SOURCE_PATH = "FormalConjectures/ErdosProblems/887.lean"
SOURCE_BLOB = "21c7d60d90d013de645b46f318980ba4b4a5d9f7"
SOURCE_RAW_SHA256 = "sha256:c2225a17de2f5210dbdb010bf7e915940d6776daf4ba4220d59b3002856a429a"


class AttemptPreparationError(RuntimeError):
    """Raised when an exact-source attempt workspace cannot be prepared."""


def _run(*args: str, cwd: Path | None = None) -> str:
    try:
        return subprocess.check_output(
            list(args),
            cwd=cwd,
            text=True,
            stderr=subprocess.STDOUT,
        ).strip()
    except subprocess.CalledProcessError as error:
        raise AttemptPreparationError(error.output.strip() or f"command failed: {' '.join(args)}") from error


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _sha256(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _load_offer() -> dict[str, Any]:
    _run("python3", "-B", str(OFFER_BUILDER.relative_to(REPO_ROOT)), "--check", cwd=REPO_ROOT)
    index = json.loads(INDEX_PATH.read_bytes())
    matches = [target for target in index.get("targets", []) if target.get("id") == TARGET_ID]
    if len(matches) != 1 or matches[0].get("presence") != "open":
        raise AttemptPreparationError("exact open proof-discharge Work Offer is unavailable")
    return matches[0]


def prepare(destination: Path) -> dict[str, Any]:
    offer = _load_offer()
    destination = destination.resolve()
    if destination.exists():
        raise AttemptPreparationError(f"destination already exists: {destination}")
    source = destination / "source"
    try:
        destination.mkdir(parents=True)
        _run(
            "git",
            "-c",
            "credential.helper=",
            "clone",
            "--filter=blob:none",
            "--no-checkout",
            SOURCE_REPOSITORY,
            str(source),
        )
        _run("git", "checkout", "--detach", SOURCE_COMMIT, cwd=source)
        actual_commit = _run("git", "rev-parse", "HEAD", cwd=source)
        actual_tree = _run("git", "show", "-s", "--format=%T", "HEAD", cwd=source)
        actual_blob = _run("git", "rev-parse", f"HEAD:{SOURCE_PATH}", cwd=source)
        raw = (source / SOURCE_PATH).read_bytes()
        if (actual_commit, actual_tree, actual_blob, _sha256(raw)) != (
            SOURCE_COMMIT,
            SOURCE_TREE,
            SOURCE_BLOB,
            SOURCE_RAW_SHA256,
        ):
            raise AttemptPreparationError("prepared source identity drift")
        if _run("git", "status", "--porcelain", cwd=source):
            raise AttemptPreparationError("prepared source checkout is dirty")
        context = {
            "schema": "vela.math.proof-attempt-context.v1",
            "authority_effect": "none",
            "target_id": TARGET_ID,
            "execution_binding": offer["execution_binding"],
            "packet": offer["packet"],
            "source": {
                "repository": SOURCE_REPOSITORY.removesuffix(".git"),
                "commit": actual_commit,
                "tree": actual_tree,
                "path": SOURCE_PATH,
                "git_blob_oid": actual_blob,
                "raw_sha256": _sha256(raw),
                "checkout": "source",
            },
            "declared_bounds": {
                "wall_clock_minutes": 90,
                "paid_external_compute": False,
                "upstream_writes": False,
            },
            "next_steps": [
                "Record performer/model/tool provenance before changing source.",
                "Keep changes within Erdos887.erdos_887.parts.ii or directly required supporting declarations.",
                "Retain the exact patch, commands, stdout, stderr, environment, and terminal goals.",
                "A proved candidate must build and #print axioms must contain no sorryAx.",
                "Return an honest bounded non-success record if the proof is not discharged.",
            ],
            "nonclaims": [
                "Preparing this workspace starts no Vela authority action and changes no Standing.",
                "The public checkout authorizes no upstream write, comment, review, branch, or pull request.",
            ],
        }
        (destination / "attempt-context.v1.json").write_bytes(_canonical_bytes(context) + b"\n")
        return context
    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--prepare",
        type=Path,
        help="new destination directory; defaults to a new system temporary directory",
    )
    args = parser.parse_args()
    destination = args.prepare or Path(tempfile.mkdtemp(prefix="vela-erdos-887-proof-discharge-"))
    if args.prepare is None:
        destination.rmdir()
    context = prepare(destination)
    print(json.dumps({
        "ok": True,
        "workspace": str(destination.resolve()),
        "packet_root": context["execution_binding"]["packet_root"],
        "source_commit": context["source"]["commit"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
