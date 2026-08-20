#!/usr/bin/env python3
"""Validate and render the frozen, non-authoritative Formal Conjectures build audit.

`verify` re-derives the deterministic roots of the frozen inputs and rejects
schema drift, invented authority effects, outcome vocabularies outside the
closed rubric, drift against the static audit this one extends, an axiom
finding that names no link, a claim of clean axioms on a checkout that was
never built, and retained third-party source text. It needs no network, no
Lean toolchain and no checkouts.

`report` derives every aggregate cell from `builds.json` and writes
`report.json`. It counts; it does not score and does not rank. The linked
repositories are not competitors, and a build failure months after the fact is
ordinary toolchain drift rather than a defect of anyone's mathematics.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent
STATIC_RESULTS = BASE.parent / "fc-conditional-proof-audit-v1" / "results.json"
INPUTS = ("builds.json", "findings.json", "rubric.json")

SCHEMAS = {
    "builds.json": "vela-math.fc-build-audit-builds.v1",
    "findings.json": "vela-math.fc-build-audit-findings.v1",
    "rubric.json": "vela-math.fc-build-audit-rubric.v1",
}

OUTCOMES = {
    "built",
    "build_failed",
    "build_timeout",
    "toolchain_unavailable",
    "no_manifest",
    "target_not_found",
    "fetch_failed",
    "skipped_disk_floor",
    "skipped_budget",
    "not_attempted",
    "no_github_checkout",
}
# Outcomes that mean a kernel actually looked at the target. Nothing else may
# ever be reported as evidence about a proof.
ATTEMPTED = OUTCOMES - {
    "not_attempted",
    "skipped_disk_floor",
    "skipped_budget",
    "no_github_checkout",
}
CONCLUSIVE = {"built"}

AXIOM_READING_STATUS = {"read", "not_found", "not_read", "probe_failed", "unparsed"}
HYPOTHESIS_STATUS = {"read", "unavailable"}
AXIOM_FLAGS = {"sorryAx", "native_decide", "nonstandard_axiom"}
STANDARD_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}
FINDING_KINDS = {
    "axiom_clause_failure",
    "pinned_revision_build_failure",
    "unpinned_revision_build_failure",
    "target_not_locatable",
}
PINNING = {"pinned_commit", "branch_or_tag", "repository_root", "not_github"}

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

    A build failure prints goal states, which are derived from third-party
    source. `build.py` caps each excerpt; this re-checks the frozen file so a
    hand edit cannot smuggle a proof in.
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


def axiom_flags(axioms: list[str]) -> list[str]:
    flags = []
    extra = set(axioms) - STANDARD_AXIOMS
    if "sorryAx" in extra:
        flags.append("sorryAx")
    if extra & {"Lean.ofReduceBool", "Lean.trustCompiler"}:
        flags.append("native_decide")
    if extra - {"Lean.ofReduceBool", "Lean.trustCompiler", "sorryAx"}:
        flags.append("nonstandard_axiom")
    return sorted(flags)


def verify_files(base: Path = BASE, static: Path = STATIC_RESULTS) -> dict[str, Any]:
    values = load_inputs(base)
    walk_keys(values)
    for name, value in values.items():
        if value.get("schema") != SCHEMAS[name]:
            raise InvalidAudit(f"schema drift: {name}")
        if value.get("authority_effect") != "none":
            raise InvalidAudit(f"every evaluation input must have authority_effect none: {name}")

    # `builds.json` is generated FROM third-party checkouts.
    enforce_rights_shape(values["builds.json"], "builds.json")
    enforce_rights_shape(values["findings.json"], "findings.json", HAND_AUTHORED_LIMIT)
    enforce_rights_shape(values["rubric.json"], "rubric.json", HAND_AUTHORED_LIMIT)

    builds = values["builds.json"]
    findings = values["findings.json"]
    rubric = values["rubric.json"]
    checkouts = builds["checkouts"]
    links = builds["links"]

    # ---- rubric is closed and states what a build result cannot show
    if set(rubric["outcomes"]) != OUTCOMES:
        raise InvalidAudit("rubric outcome vocabulary drift")
    for name, text in rubric["outcomes"].items():
        if not text:
            raise InvalidAudit(f"rubric outcome without a definition: {name}")
    if not rubric.get("a_build_failure_is_not_an_accusation"):
        raise InvalidAudit("rubric must carry the not-an-accusation statement")
    if not rubric.get("what_a_clean_axiom_set_does_not_establish"):
        raise InvalidAudit("rubric must state what a clean axiom set does not establish")
    for surface in ("axiom_closure", "prop_hypotheses"):
        if surface not in (rubric.get("trust_surfaces") or {}):
            raise InvalidAudit(f"rubric must define the {surface} surface")
    if not rubric["trust_surfaces"]["axiom_closure"].get("known_leaks"):
        raise InvalidAudit("rubric must name the known leaks in the axiom closure")

    # ---- the population is exactly the static audit's, unchanged
    static_results = json.loads(static.read_text())
    if builds["source"]["static_results_root"] != static_results["results_root"]:
        raise InvalidAudit("static audit results_root drift")
    if len(checkouts) != len(static_results["checkouts"]):
        raise InvalidAudit("checkout-count drift against the static audit")
    if len(links) != len(static_results["links"]):
        raise InvalidAudit("link-count drift against the static audit")
    static_keys = {f"{c['repo']}@{c['requested_rev']}" for c in static_results["checkouts"]}
    if {row["checkout"] for row in checkouts} != static_keys:
        raise InvalidAudit("checkout identity drift against the static audit")

    # ---- confidence is carried through from the static audit, not re-derived
    static_confidence = {
        (row["fc_file"], row["fc_line"], row["fc_decl"]): row.get("target_locator_confidence")
        for row in static_results["links"]
    }
    for row in links:
        key = (row["fc_file"], row["fc_line"], row["fc_decl"])
        if key not in static_confidence:
            raise InvalidAudit(f"link is not in the static audit: {key}")
        if row["target_locator_confidence"] != static_confidence[key]:
            raise InvalidAudit(f"locator confidence altered: {key}")
        if row["revision_pinning"] not in PINNING:
            raise InvalidAudit(f"revision pinning vocabulary: {key}")

    # ---- per-checkout vocabulary, and a result never outruns its evidence
    by_key = {}
    for row in checkouts:
        outcome = row.get("outcome")
        if outcome not in OUTCOMES:
            raise InvalidAudit(f"outcome vocabulary: {row['checkout']}")
        by_key[row["checkout"]] = row
        if outcome not in ATTEMPTED:
            if row.get("axioms"):
                raise InvalidAudit(f"unattempted checkout carries axiom readings: {row['checkout']}")
            continue
        if outcome in {"build_failed", "build_timeout", "toolchain_unavailable", "fetch_failed"}:
            if not row.get("error"):
                raise InvalidAudit(f"failure without exact text: {row['checkout']}")
        if outcome == "built":
            if not any(
                item.get("status") == "read" for item in (row.get("axioms") or {}).values()
            ):
                raise InvalidAudit(f"`built` without a single axiom reading: {row['checkout']}")
        for decl, reading in (row.get("axioms") or {}).items():
            if reading.get("status") not in AXIOM_READING_STATUS:
                raise InvalidAudit(f"axiom reading status: {row['checkout']}/{decl}")
            if reading["status"] != "read":
                continue
            if not isinstance(reading.get("axioms"), list):
                raise InvalidAudit(f"axiom reading without an axiom list: {row['checkout']}/{decl}")
            # The two trust surfaces are recorded separately and neither may go
            # missing. A clean axiom closure is necessary and not sufficient —
            # `@[csimp]` (lean4#7463) can swap an unverified implementation in
            # without touching the closure — so a reading that reports only the
            # closure is an incomplete reading, not a clean one.
            hypotheses = reading.get("prop_hypotheses")
            if not isinstance(hypotheses, dict):
                raise InvalidAudit(
                    f"reading without a prop_hypotheses field: {row['checkout']}/{decl}"
                )
            if hypotheses.get("status") not in HYPOTHESIS_STATUS:
                raise InvalidAudit(f"prop_hypotheses status: {row['checkout']}/{decl}")
            if hypotheses["status"] == "read":
                if not isinstance(hypotheses.get("prop_binders"), int):
                    raise InvalidAudit(f"prop_hypotheses without a count: {row['checkout']}/{decl}")
                if hypotheses["prop_binders"] > hypotheses.get("total_binders", -1):
                    raise InvalidAudit(
                        f"more Prop binders than binders: {row['checkout']}/{decl}"
                    )
            elif hypotheses.get("prop_binders") is not None:
                # `unavailable` must never be reported as a count. "No
                # hypotheses" and "the probe did not run" are different claims.
                raise InvalidAudit(
                    f"unavailable prop_hypotheses carries a count: {row['checkout']}/{decl}"
                )
        declared = set(row.get("axiom_flags") or [])
        if declared - AXIOM_FLAGS:
            raise InvalidAudit(f"axiom flag vocabulary: {row['checkout']}")
        derived: set[str] = set()
        for reading in (row.get("axioms") or {}).values():
            if reading.get("status") == "read":
                derived.update(axiom_flags(reading["axioms"]))
        if declared != derived:
            raise InvalidAudit(f"axiom flags not derived from the axiom sets: {row['checkout']}")

    # ---- every link's build outcome is its checkout's, verbatim
    for row in links:
        if row["checkout"] is None:
            # 16 links point at no GitHub repository. They carry the population
            # forward and must never be given a build result.
            if row["build_outcome"] != "no_github_checkout":
                raise InvalidAudit(f"checkout-less link with a build outcome: {row['fc_decl']}")
            if row["axiom_readings"] or row["axiom_flags"]:
                raise InvalidAudit(f"checkout-less link carries readings: {row['fc_decl']}")
            continue
        parent = by_key.get(row["checkout"])
        if parent is None:
            raise InvalidAudit(f"link references an unrecorded checkout: {row['checkout']}")
        if row["build_outcome"] != parent["outcome"]:
            raise InvalidAudit(f"link outcome disagrees with its checkout: {row['fc_decl']}")

    # ---- every finding binds to a real link and every flag has a finding
    link_index = {f"{row['fc_file']}:{row['fc_line']}": row for row in links}
    for case in findings["cases"]:
        if case["kind"] not in FINDING_KINDS:
            raise InvalidAudit(f"finding kind vocabulary: {case['id']}")
        if not case.get("links"):
            raise InvalidAudit(f"finding names no link: {case['id']}")
        for ref in case["links"]:
            if ref not in link_index:
                raise InvalidAudit(f"finding references no link: {ref}")
        if case["kind"] == "axiom_clause_failure":
            if not case.get("axioms"):
                raise InvalidAudit(f"axiom finding without the axiom set: {case['id']}")
            if not axiom_flags(case["axioms"]):
                raise InvalidAudit(f"axiom finding whose axiom set is standard: {case['id']}")
            for ref in case["links"]:
                if not link_index[ref]["axiom_flags"]:
                    raise InvalidAudit(f"axiom finding on a link with no flag: {ref}")
        if case["kind"].endswith("build_failure"):
            parent = by_key[link_index[case["links"][0]]["checkout"]]
            if parent["outcome"] not in {"build_failed", "build_timeout", "toolchain_unavailable"}:
                raise InvalidAudit(f"build-failure finding on a checkout that built: {case['id']}")
            if not case.get("drift_reading"):
                raise InvalidAudit(
                    f"a build failure must be read as drift or not, explicitly: {case['id']}"
                )
    flagged_links = {
        f"{row['fc_file']}:{row['fc_line']}" for row in links if row["axiom_flags"]
    }
    covered = {
        ref
        for case in findings["cases"]
        if case["kind"] == "axiom_clause_failure"
        for ref in case["links"]
    }
    if flagged_links - covered:
        raise InvalidAudit(f"axiom flag with no finding: {sorted(flagged_links - covered)[:3]}")

    # ---- the headline negatives are re-derived, never taken on trust
    failure_outcomes = {"build_failed", "build_timeout", "toolchain_unavailable"}
    negatives = findings.get("stated_negatives")
    if not negatives:
        raise InvalidAudit("findings must state its negative results so they can be checked")
    derived = {
        "build_failures_at_a_pinned_revision": sum(
            1
            for row in checkouts
            if row["outcome"] == "build_failed" and row.get("revision_pinned_by_link")
        ),
        "build_failures_at_an_unpinned_revision": sum(
            1
            for row in checkouts
            if row["outcome"] == "build_failed" and not row.get("revision_pinned_by_link")
        ),
        "build_timeouts": sum(1 for row in checkouts if row["outcome"] == "build_timeout"),
        "toolchains_unavailable": sum(
            1 for row in checkouts if row["outcome"] == "toolchain_unavailable"
        ),
        "declarations_whose_closure_contains_sorryAx": sum(
            1
            for row in checkouts
            for reading in (row.get("axioms") or {}).values()
            if reading.get("status") == "read" and "sorryAx" in reading["axioms"]
        ),
        "declarations_whose_hypothesis_probe_was_unavailable": sum(
            1
            for row in checkouts
            for reading in (row.get("axioms") or {}).values()
            if reading.get("status") == "read"
            and (reading.get("prop_hypotheses") or {}).get("status") != "read"
        ),
    }
    for name, value in derived.items():
        if negatives.get(name) != value:
            raise InvalidAudit(
                f"stated negative disagrees with builds.json: {name} "
                f"claimed {negatives.get(name)}, derived {value}"
            )
    if not negatives.get("reading"):
        raise InvalidAudit("stated negatives must be read in prose, not left as bare zeros")
    if failure_outcomes & {row["outcome"] for row in checkouts} and not any(
        case["kind"].endswith("build_failure") for case in findings["cases"]
    ):
        raise InvalidAudit("a build failure occurred but no finding records it")

    # ---- the run's own honesty about coverage
    attempted = [row for row in checkouts if row["outcome"] in ATTEMPTED]
    if findings["coverage"]["checkouts_attempted"] != len(attempted):
        raise InvalidAudit("coverage drift: checkouts_attempted")
    if findings["coverage"]["checkouts_total"] != len(checkouts):
        raise InvalidAudit("coverage drift: checkouts_total")
    if len(attempted) < len(checkouts) and not findings["coverage"].get("why_partial"):
        raise InvalidAudit("a partial run must state why it is partial")

    roots = {name: sha256(canonical(values[name])) for name in INPUTS}
    roots["implementation"] = sha256((base / "evaluate.py").read_bytes())
    roots["collector"] = sha256((base / "build.py").read_bytes())
    roots["static_results"] = static_results["results_root"]
    roots["evaluation_root"] = sha256(canonical({name: values[name] for name in INPUTS}))
    return {"values": values, "roots": roots}


def build_report(base: Path = BASE, static: Path = STATIC_RESULTS) -> dict[str, Any]:
    verified = verify_files(base, static)
    values = verified["values"]
    builds = values["builds.json"]
    checkouts = builds["checkouts"]
    links = builds["links"]

    attempted = [row for row in checkouts if row["outcome"] in ATTEMPTED]
    built = [row for row in checkouts if row["outcome"] == "built"]
    seconds = sum(row.get("seconds", 0) or 0 for row in checkouts)

    axiom_sets: Counter[str] = Counter()
    read_declarations = 0
    for row in built:
        for reading in (row.get("axioms") or {}).values():
            if reading.get("status") != "read":
                continue
            read_declarations += 1
            axiom_sets[", ".join(sorted(reading["axioms"]))] += 1

    hypothesis_read = 0
    hypothesis_unavailable = 0
    hypothesis_conditional = 0
    hypothesis_histogram: Counter[str] = Counter()
    for row in built:
        for reading in (row.get("axioms") or {}).values():
            if reading.get("status") != "read":
                continue
            hypotheses = reading.get("prop_hypotheses") or {}
            if hypotheses.get("status") != "read":
                hypothesis_unavailable += 1
                continue
            hypothesis_read += 1
            count = hypotheses["prop_binders"]
            hypothesis_histogram[str(count)] += 1
            if count:
                hypothesis_conditional += 1

    flagged = [row for row in links if row["axiom_flags"]]
    pinned_failures = [
        row
        for row in checkouts
        if row["outcome"] in {"build_failed", "build_timeout", "toolchain_unavailable"}
        and row.get("revision_pinned_by_link")
    ]
    unpinned_failures = [
        row
        for row in checkouts
        if row["outcome"] in {"build_failed", "build_timeout", "toolchain_unavailable"}
        and not row.get("revision_pinned_by_link")
    ]

    return {
        "schema": "vela-math.fc-build-audit-report.v1",
        "authority_effect": "none",
        "source": builds["source"],
        "input_roots": verified["roots"],
        "coverage": {
            "checkouts_total": len(checkouts),
            "checkouts_attempted": len(attempted),
            "checkouts_built": len(built),
            "links_total": len(links),
            "links_under_an_attempted_checkout": sum(
                1 for row in links if row["build_outcome"] in ATTEMPTED
            ),
            "links_under_a_built_checkout": sum(
                1 for row in links if row["build_outcome"] == "built"
            ),
            # The primary number. A repository's headline outcome is its
            # busiest project's, so a link can carry a real kernel reading while
            # sitting under a checkout whose headline is `target_not_found`.
            # This counts links by what was actually read for them.
            "links_with_an_axiom_reading": sum(
                1
                for row in links
                if any(r.get("status") == "read" for r in row["axiom_readings"].values())
            ),
            "why_partial": values["findings.json"]["coverage"].get("why_partial"),
        },
        "outcomes": {
            "by_checkout": dict(sorted(Counter(r["outcome"] for r in checkouts).items())),
            "by_link": dict(sorted(Counter(r["build_outcome"] for r in links).items())),
        },
        "axioms": {
            "declarations_read": read_declarations,
            "distinct_axiom_sets": dict(sorted(axiom_sets.items())),
            "links_with_a_flagged_axiom_set": len(flagged),
            "flag_counts": dict(
                sorted(Counter(flag for row in flagged for flag in row["axiom_flags"]).items())
            ),
            "flagged_links_by_locator_confidence": dict(
                sorted(Counter(row["target_locator_confidence"] for row in flagged).items())
            ),
        },
        "prop_hypotheses": {
            "declarations_with_a_reading": hypothesis_read,
            "declarations_probe_unavailable": hypothesis_unavailable,
            "declarations_with_at_least_one_prop_binder": hypothesis_conditional,
            "prop_binder_histogram": dict(sorted(hypothesis_histogram.items())),
            "note": (
                "A propositional binder is not a defect. Formal Conjectures statements "
                "carry hypotheses of their own and a linked proof mirroring them is "
                "correct. This field is recorded because a hypothesis is invisible to "
                "`#print axioms`, so the two surfaces have to be read together."
            ),
        },
        "build_failures": {
            "at_a_pinned_revision": len(pinned_failures),
            "at_an_unpinned_revision": len(unpinned_failures),
            "pinned_repositories": dict(
                sorted(Counter(row["repo"] for row in pinned_failures).items())
            ),
            "unpinned_repositories": dict(
                sorted(Counter(row["repo"] for row in unpinned_failures).items())
            ),
        },
        "toolchains": {
            "declared": dict(
                sorted(
                    Counter(
                        row["toolchain_declared"]
                        for row in checkouts
                        if row.get("toolchain_declared")
                    ).items()
                )
            ),
            "checkouts_depending_on_mathlib": sum(
                1 for row in checkouts if row.get("depends_on_mathlib")
            ),
        },
        "compute": {
            "total_seconds": round(seconds, 1),
            "total_hours": round(seconds / 3600, 2),
            "median_seconds_per_built_checkout": (
                sorted(row.get("seconds", 0) for row in built)[len(built) // 2] if built else None
            ),
            "note": builds["host"]["note"],
        },
        "findings": {
            "cases": len(values["findings.json"]["cases"]),
            "by_kind": dict(
                sorted(Counter(c["kind"] for c in values["findings.json"]["cases"]).items())
            ),
        },
        "limitations": values["rubric.json"]["limitations"],
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
        builds = verified["values"]["builds.json"]
        attempted = sum(1 for row in builds["checkouts"] if row["outcome"] in ATTEMPTED)
        print(f"builds: {verified['roots']['builds.json']}")
        print(f"evaluation: {verified['roots']['evaluation_root']}")
        print(
            f"audit: ok ({attempted} of {len(builds['checkouts'])} checkouts attempted, "
            f"{len(builds['links'])} links)"
        )
        return

    output = build_report()
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(f"report: {sha256(canonical(output))}")


if __name__ == "__main__":
    main()
