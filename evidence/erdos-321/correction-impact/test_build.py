#!/usr/bin/env python3
"""Hostile checks for the bounded Erdős 321 correction-impact record."""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("correction_impact_build", HERE / "build.py")
assert SPEC and SPEC.loader
build = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build)
sys.modules["build"] = build
COLD_SPEC = importlib.util.spec_from_file_location("correction_cold_reader", HERE / "cold_reader.py")
assert COLD_SPEC and COLD_SPEC.loader
cold_reader = importlib.util.module_from_spec(COLD_SPEC)
COLD_SPEC.loader.exec_module(cold_reader)


def refuses(document, message: str) -> None:
    try:
        build.validate_document(document)
    except build.BuildError as error:
        assert message in str(error), error
    else:
        raise AssertionError(f"expected refusal: {message}")


def main() -> int:
    document = build.load_json(HERE / "correction-impact.v1.json")
    build.validate_document(document)

    changed = copy.deepcopy(document)
    changed["authority_effect"] = "standing"
    changed = build.reroot(changed)
    refuses(changed, "schema or authority effect")

    changed = copy.deepcopy(document)
    changed["relation_slice"][0]["category"] = "unaffected"
    changed = build.reroot(changed)
    refuses(changed, "bounded relation inventory")

    changed = copy.deepcopy(document)
    changed["relation_slice"].pop()
    changed = build.reroot(changed)
    refuses(changed, "bounded relation inventory")

    changed = copy.deepcopy(document)
    changed["replay"]["stages"][-1]["repository_root"] = "sha256:" + "0" * 64
    changed = build.reroot(changed)
    refuses(changed, "does not match retained sources")

    changed = copy.deepcopy(document)
    changed["source_lineage"]["current_authority_generation"]["accepted_successor"]["decision"]["raw_sha256"] = "sha256:" + "0" * 64
    changed = build.reroot(changed)
    refuses(changed, "does not match retained sources")

    try:
        build.load_json_bytes(b'{"schema":"x","schema":"y"}')
    except build.BuildError as error:
        assert "duplicate JSON key" in str(error)
    else:
        raise AssertionError("duplicate JSON key accepted")

    assert document["repair_obligation"]["status"] == "open"
    assert document["repair_obligation"]["standing_effect"] == "none"
    assert all(stage["ok"] is True for stage in document["replay"]["stages"])

    result = build.load_json(HERE / "cold-reader-result.v1.json")
    evaluation = build.load_json(HERE / "cold-reader-evaluation.v1.json")
    cold_reader.validate_result(result)
    cold_reader.validate_evaluation(evaluation, result)

    changed_result = copy.deepcopy(result)
    changed_result["arms"][0]["score"]["correct"] = 7
    changed_result = build.reroot(changed_result)
    try:
        cold_reader.validate_result(changed_result)
    except build.BuildError as error:
        assert "score drift" in str(error)
    else:
        raise AssertionError("changed cold-reader score accepted")

    changed_evaluation = copy.deepcopy(evaluation)
    changed_evaluation["disposition"]["status"] = "continue"
    changed_evaluation = build.reroot(changed_evaluation)
    try:
        cold_reader.validate_evaluation(changed_evaluation, result)
    except build.BuildError as error:
        assert "does not match retained result" in str(error)
    else:
        raise AssertionError("changed cold-reader disposition accepted")

    print("erdos-321-correction-impact-tests: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
