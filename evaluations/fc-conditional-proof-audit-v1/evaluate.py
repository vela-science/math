#!/usr/bin/env python3
"""Validate and render the frozen, non-authoritative conditional-proof audit.

`verify` re-derives the deterministic roots of the frozen inputs and rejects
schema drift, invented authority effects, population drift against `audit.json`,
retained third-party source text, and outcome vocabularies outside the closed
rubric. It needs no network and no checkouts.

`report` derives every aggregate cell from `results.json` and writes
`report.json`. It computes counts, not a score and not a ranking: the linked
repositories are not competitors and this evaluation does not rank them.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent
INPUTS = ("audit.json", "calibration.json", "results.json", "rubric.json", "tier2.json")

SCHEMAS = {
    "audit.json": "vela-math.fc-conditional-proof-audit.v1",
    "calibration.json": "vela-math.fc-conditional-proof-calibration.v1",
    "results.json": "vela-math.fc-conditional-proof-results.v1",
    "rubric.json": "vela-math.fc-conditional-proof-rubric.v1",
    "tier2.json": "vela-math.fc-conditional-proof-tier2.v1",
}

DISCRIMINATORS = (
    "d1_conditional_on_uninhabited",
    "d2_sealed_core",
    "d3_ordinary_gate",
    "d4_assumed_false_fields",
)
D1_OUTCOMES = {
    "clear",
    "flagged_conditional_construction",
    "flagged_uninhabited",
    "undetermined",
}
D2_OUTCOMES = {"no_opaque", "opaque_present_not_reached", "reaches_opaque", "undetermined"}
ASSESSMENTS = {"assessed", "undetermined"}
PINNING = {"pinned_commit", "branch_or_tag", "repository_root", "not_github"}
TIER2_OUTCOMES = {
    "confirmed_conditional",
    "confirmed_nonstandard_axioms",
    "confirmed_unconditional",
    "build_infeasible",
    "build_failed",
    "not_attempted",
}

BANNED_KEYS = {
    "body",
    "source_text",
    "proof_text",
    "lean_source",
    "file_text",
    "page_text",
    "chunk",
    "signature",
}
BANNED_SCORING_KEYS = {"score", "scores", "winner", "ranking", "rank"}
MAX_RETAINED_STRING = 512
HAND_AUTHORED_LIMIT = 2048


class InvalidAudit(ValueError):
    pass


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def sha256(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def load_inputs(base: Path = BASE) -> dict[str, Any]:
    return {name: json.loads((base / name).read_text()) for name in INPUTS}


def walk_keys(value: Any, path: str = "") -> None:
    """Reject third-party source bodies and aggregate-scoring fields anywhere."""
    if isinstance(value, dict):
        for key, item in value.items():
            if key in BANNED_KEYS:
                raise InvalidAudit(f"third-party source field forbidden: {path}.{key}")
            if key in BANNED_SCORING_KEYS:
                raise InvalidAudit(f"aggregate scoring field forbidden: {path}.{key}")
            walk_keys(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            walk_keys(item, f"{path}[{index}]")


def enforce_rights_shape(value: Any, path: str = "input", limit: int = MAX_RETAINED_STRING) -> None:
    """No retained string may be large enough to be copied Lean source.

    Applied to the files that carry material derived from third-party
    checkouts. `rubric.json`, `audit.json` and `RECOMMENDATIONS.md` are authored
    here and hold method prose, so they get the looser hand-authored limit.
    """
    if isinstance(value, str):
        if len(value) > limit:
            raise InvalidAudit(f"oversized retained external text: {path}")
    elif isinstance(value, dict):
        for key, item in value.items():
            enforce_rights_shape(item, f"{path}.{key}", limit)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            enforce_rights_shape(item, f"{path}[{index}]", limit)


def verify_files(base: Path = BASE) -> dict[str, Any]:
    values = load_inputs(base)
    walk_keys(values)
    for name, value in values.items():
        if value.get("schema") != SCHEMAS[name]:
            raise InvalidAudit(f"schema drift: {name}")
        if value.get("authority_effect") != "none":
            raise InvalidAudit(f"every evaluation input must have authority_effect none: {name}")
    # `results.json` and `calibration.json` are generated FROM third-party
    # checkouts and must hold nothing but names, counts and locators.
    for name in ("results.json", "calibration.json"):
        enforce_rights_shape(values[name], name)
    # `tier2.json` is hand-authored, so it gets a looser cap that still stops a
    # proof from being pasted in.
    enforce_rights_shape(values["tier2.json"], "tier2.json", HAND_AUTHORED_LIMIT)

    audit = values["audit.json"]
    calibration = values["calibration.json"]
    results = values["results.json"]
    rubric = values["rubric.json"]
    tier2 = values["tier2.json"]

    # ---- rubric is closed and states its own error modes
    ids = tuple(row["id"] for row in rubric["discriminators"])
    if ids != DISCRIMINATORS:
        raise InvalidAudit("rubric discriminator drift")
    for row in rubric["discriminators"]:
        if not row.get("false_positives") or not row.get("false_negatives"):
            raise InvalidAudit(f"rubric must state error modes both ways: {row['id']}")
    if not rubric.get("not_an_accusation"):
        raise InvalidAudit("rubric must carry the not-an-accusation statement")

    # ---- population matches what was actually parsed
    links = results["links"]
    checkouts = results["checkouts"]
    population = audit["population"]
    if results["source"]["commit"] != audit["source"]["commit"]:
        raise InvalidAudit("source commit drift between audit and results")
    if population["formal_proof_attributes"] != len(links):
        raise InvalidAudit("population link-count drift")
    if population["distinct_repository_revision_pairs"] != len(checkouts):
        raise InvalidAudit("population checkout-count drift")
    observed_repos = {row["target_repo"] for row in links if row.get("target_repo")}
    if population["distinct_github_repositories"] != len(observed_repos):
        raise InvalidAudit("population repository-count drift")

    counted_pinning = Counter(row["revision_pinning"] for row in links)
    if set(counted_pinning) - PINNING:
        raise InvalidAudit("revision pinning vocabulary")
    for key, expected in population["revision_pinning"].items():
        if counted_pinning.get(key, 0) != expected:
            raise InvalidAudit(f"revision pinning drift: {key}")

    # ---- per-link vocabularies, and undetermined never silently reads as clear
    for row in links:
        if row.get("assessment") not in ASSESSMENTS:
            raise InvalidAudit(f"assessment vocabulary: {row['fc_file']}:{row['fc_line']}")
        if row["assessment"] == "undetermined":
            if not row.get("assessment_reason"):
                raise InvalidAudit(f"undetermined without reason: {row['fc_file']}:{row['fc_line']}")
            if row.get("d1") not in (None, "undetermined"):
                raise InvalidAudit(f"undetermined row carries a D1 verdict: {row['fc_file']}")
            continue
        if row.get("d1") not in D1_OUTCOMES:
            raise InvalidAudit(f"D1 vocabulary: {row['fc_file']}:{row['fc_line']}")
        if row.get("d2") not in D2_OUTCOMES:
            raise InvalidAudit(f"D2 vocabulary: {row['fc_file']}:{row['fc_line']}")
        if row["d1"] == "flagged_uninhabited" and not row.get("d1_uninhabited_binder_types"):
            raise InvalidAudit(f"D1 flag without a named binder type: {row['fc_file']}")
        if row["d1"] == "flagged_conditional_construction" and not row.get(
            "d1_conditional_binder_types"
        ):
            raise InvalidAudit(f"D1 flag without a named binder type: {row['fc_file']}")
        if row.get("checkout") not in {c["repo"] + "@" + c["requested_rev"] for c in checkouts}:
            raise InvalidAudit(f"link references an unrecorded checkout: {row['fc_file']}")

    # ---- calibration separates a conditional theorem from an unconditional one
    outcomes = {row["declaration"]: row["d1"] for row in calibration["declarations"]}
    if not any(value.startswith("flagged") for value in outcomes.values()):
        raise InvalidAudit("calibration must flag the known-conditional declarations")
    if "clear" not in outcomes.values():
        raise InvalidAudit("calibration must pass the known-unconditional declaration")
    gate = calibration["ordinary_gate_on_artifact"]
    if gate["sorry"] != 0 or gate["axiom"] != 0:
        raise InvalidAudit("calibration artifact no longer passes the ordinary gate")
    calibration_repo = calibration["artifact"]["repository"]
    if calibration_repo in observed_repos:
        raise InvalidAudit("calibration artifact must not be inside the measured population")

    # ---- tier 2 binds to real links and never guesses
    link_index = {f"{row['fc_file']}:{row['fc_line']}": row for row in links}
    for case in tier2["cases"]:
        if case["link"] not in link_index:
            raise InvalidAudit(f"tier 2 case references no link: {case['link']}")
        if case["outcome"] not in TIER2_OUTCOMES:
            raise InvalidAudit(f"tier 2 outcome vocabulary: {case['link']}")
        if case["outcome"] in {"build_infeasible", "build_failed", "not_attempted"} and not case.get(
            "reason"
        ):
            raise InvalidAudit(f"tier 2 non-result without an exact reason: {case['link']}")
        if not str(link_index[case["link"]].get("d1", "")).startswith("flagged") and case[
            "outcome"
        ] == "confirmed_conditional":
            raise InvalidAudit(f"tier 2 confirms a case Tier 1 did not flag: {case['link']}")

    roots = {name: sha256(canonical(values[name])) for name in INPUTS}
    roots["implementation"] = sha256((base / "evaluate.py").read_bytes())
    roots["collector"] = sha256((base / "analyze.py").read_bytes())
    roots["evaluation_root"] = sha256(canonical({name: values[name] for name in INPUTS}))
    return {"values": values, "roots": roots}


def build_report(base: Path = BASE) -> dict[str, Any]:
    verified = verify_files(base)
    values = verified["values"]
    results = values["results.json"]
    links = results["links"]
    checkouts = {c["repo"] + "@" + c["requested_rev"]: c for c in results["checkouts"]}

    assessed = [row for row in links if row["assessment"] == "assessed"]
    undetermined = [row for row in links if row["assessment"] != "assessed"]
    located = [row for row in assessed if row["d1"] != "undetermined"]

    d1 = Counter(row["d1"] for row in assessed)
    d2 = Counter(row["d2"] for row in assessed)
    basis = Counter(row["target_locator_basis"] for row in assessed)

    d3_tokens: dict[str, int] = defaultdict(int)
    d3_links = Counter()
    for row in assessed:
        target = row.get("d3_target")
        if isinstance(target, dict) and target:
            d3_links["target_declaration"] += 1
            for token, count in target.items():
                d3_tokens[token] += count
        if row.get("d3_target_file"):
            d3_links["target_file"] += 1

    d4_checkouts = [key for key, value in checkouts.items() if value["d4_false_field_types"]]
    # Only a located target can carry one; an `undetermined` row records the
    # string "undetermined" here and must not be counted as a finding.
    d4_links = sum(1 for row in assessed if isinstance(row.get("d4_on_target"), list) and row["d4_on_target"])

    flagged = [row for row in located if row["d1"].startswith("flagged")]
    by_repo = Counter(row["target_repo"] for row in flagged)

    return {
        "schema": "vela-math.fc-conditional-proof-report.v1",
        "authority_effect": "none",
        "source": results["source"],
        "input_roots": verified["roots"],
        "population": {
            "formal_proof_attributes": len(links),
            "distinct_github_repositories": len(
                {row["target_repo"] for row in links if row.get("target_repo")}
            ),
            "distinct_repository_revision_pairs": len(checkouts),
            "revision_pinning": dict(sorted(Counter(r["revision_pinning"] for r in links).items())),
            "fc_declared_conditional": sum(1 for r in links if r["fc_declares_conditional"]),
            "proof_kind": dict(sorted(Counter(r["proof_kind"] for r in links).items())),
        },
        "assessability": {
            "assessed": len(assessed),
            "undetermined": len(undetermined),
            "undetermined_reasons": dict(
                sorted(Counter(r["assessment_reason"] for r in undetermined).items())
            ),
            "target_located": len(located),
            "target_locator_basis": dict(sorted(basis.items())),
        },
        "d1_conditional_on_uninhabited": {
            "denominator_links_with_located_target": len(located),
            "outcomes": dict(sorted(d1.items())),
            "flagged_links": len(flagged),
            "flagged_repositories": dict(sorted(by_repo.items())),
        },
        "d2_sealed_core": {
            "outcomes": dict(sorted(d2.items())),
            "checkouts_declaring_opaque": sum(
                1 for value in checkouts.values() if value["opaque_declaration_count"]
            ),
        },
        "d3_ordinary_gate": {
            "links_whose_target_declaration_trips_a_token": d3_links["target_declaration"],
            "links_whose_target_file_trips_a_token": d3_links["target_file"],
            "token_counts_over_target_declarations": dict(sorted(d3_tokens.items())),
        },
        "d4_assumed_False_fields": {
            "checkouts_with_a_False_field_type": len(d4_checkouts),
            "links_whose_flagged_binder_type_has_a_False_field": d4_links,
        },
        "tier2": {
            "cases": len(values["tier2.json"]["cases"]),
            "outcomes": dict(
                sorted(Counter(c["outcome"] for c in values["tier2.json"]["cases"]).items())
            ),
        },
        "calibration": {
            "artifact": values["calibration.json"]["artifact"],
            "in_population": False,
            "outcomes": dict(
                sorted(
                    Counter(r["d1"] for r in values["calibration.json"]["declarations"]).items()
                )
            ),
        },
        "limitations": [
            "D1 and D2 are text-level heuristics with false positives and false negatives; rubric.json enumerates both.",
            "A D1 flag records the shape of a signature. It is not a finding of error, unsoundness, or bad faith against any repository or author.",
            "Undetermined links are excluded from every rate rather than counted as clear.",
            "D3 is a textual substitute for `#print axioms` and cannot see what the kernel actually used.",
            "No linked repository is admitted here. Nothing in this directory is a Submission, Verification, Decision, Event, or Standing.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("verify")
    report = subparsers.add_parser("report")
    report.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.command == "verify":
        verified = verify_files()
        results = verified["values"]["results.json"]
        print(f"results: {verified['roots']['results.json']}")
        print(f"evaluation: {verified['roots']['evaluation_root']}")
        print(
            f"audit: ok ({len(results['links'])} links, "
            f"{len(results['checkouts'])} checkouts)"
        )
        return

    output = build_report()
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(f"report: {sha256(canonical(output))}")


if __name__ == "__main__":
    main()
