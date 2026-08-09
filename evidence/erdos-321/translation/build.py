#!/usr/bin/env python3
"""Build and verify the Erdős 321 science-translation experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
CASE = HERE.parent
MATH_COMMIT = "27cb6e407f1d42177169c2a02ccd337e1c7bdcc6"
FORMAL_COMMIT = "59f30aa314ba225fcd9268723ce8291616df1ab0"
STARFLEET_COMMIT = "a8c2872a27cf8d11cf6744ca4a2c5b49ace5fea0"
FORMAL_SHA256 = "601d8486743aede6803feaaefc7bbb73f0aa8873d0296a6a1c5400fd86c32357"
STARFLEET_SHA256 = "6f8edd294e9a5dfb2475468c23518722a736798ea3e6e51822f826c1e4672a74"
RUN_TIME = "2026-08-09T07:01:38Z"

FORMAL_URL = (
    "https://raw.githubusercontent.com/google-deepmind/formal-conjectures/"
    f"{FORMAL_COMMIT}/FormalConjectures/ErdosProblems/321.lean"
)
STARFLEET_URL = (
    "https://raw.githubusercontent.com/williamjblair/lean-proofs/"
    f"{STARFLEET_COMMIT}/starfleet/erdos-321/Research/Basic.lean"
)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def utf16_sort_key(value: str) -> bytes:
    return value.encode("utf-16-be", errors="surrogatepass")


def jcs(value: Any) -> bytes:
    """RFC 8785 for this closed fact subset (no floats, safe integers only)."""
    if value is None:
        return b"null"
    if value is True:
        return b"true"
    if value is False:
        return b"false"
    if isinstance(value, int) and not isinstance(value, bool):
        if abs(value) > 9_007_199_254_740_991:
            raise ValueError("integer exceeds the interoperable JSON range")
        return str(value).encode("ascii")
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite JSON number")
        raise ValueError("the deterministic fact set does not admit floats")
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if isinstance(value, list):
        return b"[" + b",".join(jcs(item) for item in value) + b"]"
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise ValueError("JSON object keys must be strings")
        items = []
        for key in sorted(value, key=utf16_sort_key):
            items.append(jcs(key) + b":" + jcs(value[key]))
        return b"{" + b",".join(items) + b"}"
    raise TypeError(f"unsupported JSON value: {type(value)!r}")


def rendered(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def snapshot_target(source: str, text: str, exact: str) -> dict[str, Any]:
    if text.count(exact) != 1:
        raise ValueError(f"selector quote occurs {text.count(exact)} times: {exact!r}")
    start = text.index(exact)
    end = start + len(exact)
    return {
        "type": "SpecificResource",
        "source": source,
        "selector": [
            {
                "type": "TextQuoteSelector",
                "exact": exact,
                "prefix": text[max(0, start - 32) : start],
                "suffix": text[end : end + 32],
            },
            {"type": "TextPositionSelector", "start": start, "end": end},
        ],
    }


def annotation(
    identifier: str,
    label: str,
    bridge: str,
    precision: str,
    targets: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "id": f"urn:vela:reference:erdos-321:{identifier}",
        "type": "Annotation",
        "motivation": "linking",
        "body": {
            "type": "TextualBody",
            "purpose": "describing",
            "format": "text/plain",
            "language": "en",
            "value": bridge,
        },
        "target": targets,
        "vela:label": label,
        "vela:precision": precision,
        "vela:authorityEffect": "none",
    }


def build_documents() -> dict[str, Any]:
    v1_path = CASE / "definition-correspondence.v1.json"
    v2_path = CASE / "definition-correspondence.v2.json"
    formal_path = HERE / "sources/formal-conjectures-321.lean"
    starfleet_path = HERE / "sources/starfleet-basic.lean"

    if sha256_file(formal_path) != FORMAL_SHA256:
        raise ValueError("Formal Conjectures snapshot digest drift")
    if sha256_file(starfleet_path) != STARFLEET_SHA256:
        raise ValueError("Star Fleet snapshot digest drift")

    v1 = load_json(v1_path)
    v2 = load_json(v2_path)
    formal = formal_path.read_text(encoding="utf-8")
    starfleet = starfleet_path.read_text(encoding="utf-8")

    if v1.get("schema") != "vela.evidence.definition-correspondence.v1":
        raise ValueError("unexpected predecessor evidence schema")
    if v2.get("corrects") != "evidence/erdos-321/definition-correspondence.v1.json":
        raise ValueError("successor evidence does not name the predecessor")

    reciprocal_star = "def reciprocalSubsetSum (S : Finset ℕ) : ℚ :=\n  ∑ n ∈ S, ((n : ℚ)⁻¹)"
    reciprocal_formal = "(fun (S : Finset ℕ) ↦ ∑ n ∈ S, (1 : ℚ) / n)"
    valid_star = (
        "def Valid (A : Finset ℕ) : Prop :=\n"
        "  ∀ S ∈ A.powerset, ∀ T ∈ A.powerset,\n"
        "    reciprocalSubsetSum S = reciprocalSubsetSum T → S = T"
    )
    valid_formal = "Set.InjOn (fun (S : Finset ℕ) ↦ ∑ n ∈ S, (1 : ℚ) / n) A.powerset"
    admissible_star = (
        "def Admissible (N : ℕ) (A : Finset ℕ) : Prop :=\n"
        "  A ⊆ Finset.Icc 1 N ∧ Valid A"
    )
    subset_formal = "A ⊆ Finset.Icc 1 N"
    extremal_star = (
        "noncomputable def candidateSets (N : ℕ) : Finset (Finset ℕ) := by\n"
        "  classical\n"
        "  exact (Finset.Icc 1 N).powerset.filter Valid\n\n"
        "/-- The exact answer to Erdős Problem 321 at parameter `N`. -/\n"
        "noncomputable def extremalSize (N : ℕ) : ℕ :=\n"
        "  (candidateSets N).sup Finset.card"
    )
    extremal_formal = (
        "noncomputable def R (N : ℕ) : ℕ :=\n"
        "  sSup { #A | (A) (_ : A ⊆ Finset.Icc 1 N)\n"
        "      (_ : Set.InjOn (fun (S : Finset ℕ) ↦ ∑ n ∈ S, (1 : ℚ) / n) A.powerset) }"
    )

    annotations = {
        "@context": [
            "http://www.w3.org/ns/anno.jsonld",
            {"vela": "https://vela.space/ns/translation#"},
        ],
        "id": "urn:vela:reference-collection:erdos-321:v1",
        "type": "AnnotationCollection",
        "label": "Erdős 321 exact definition references",
        "total": 4,
        "items": [
            annotation(
                "reciprocal-sum",
                "reciprocalSubsetSum ↔ reciprocal-sum lambda",
                "The rational functions are extensionally equal: n⁻¹ = 1 / n.",
                "exact",
                [
                    snapshot_target(STARFLEET_URL, starfleet, reciprocal_star),
                    snapshot_target(FORMAL_URL, formal, reciprocal_formal),
                ],
            ),
            annotation(
                "validity",
                "Valid ↔ Set.InjOn",
                "The quantified equality implication is Set.InjOn on A.powerset.",
                "exact",
                [
                    snapshot_target(STARFLEET_URL, starfleet, valid_star),
                    snapshot_target(FORMAL_URL, formal, valid_formal),
                ],
            ),
            annotation(
                "admissibility",
                "Admissible ↔ both set-builder side conditions",
                "Admissible is the conjunction of the subset and injectivity conditions; it is not identical to either condition alone.",
                "exact",
                [
                    snapshot_target(STARFLEET_URL, starfleet, admissible_star),
                    snapshot_target(FORMAL_URL, formal, subset_formal),
                    snapshot_target(FORMAL_URL, formal, valid_formal),
                ],
            ),
            annotation(
                "extremal-value",
                "extremalSize ↔ R",
                "Both take the maximum cardinality of the same finite nonempty family; this bridge uses the three references above.",
                "exact",
                [
                    snapshot_target(STARFLEET_URL, starfleet, extremal_star),
                    snapshot_target(FORMAL_URL, formal, extremal_formal),
                ],
            ),
        ],
    }

    facts = [
        {
            "fact": "denotational_conclusion",
            "before": "extremalSize N = R N",
            "after": "extremalSize N = R N",
            "materiality": "unchanged",
            "confidence": "established-at-pinned-sources",
        },
        {
            "fact": "correspondence_structure",
            "before": "four pairwise-identical definitions",
            "after": "three distinct correspondences plus a conjunction that reuses two of them",
            "materiality": "corrected-derivation",
            "confidence": "exact-source-comparison",
        },
        {
            "fact": "admissible_relation",
            "before": "Admissible is identical to the interval-subset condition",
            "after": "Admissible implies the interval-subset condition and additionally requires Valid",
            "materiality": "false-converse-removed",
            "confidence": "exact-source-comparison",
        },
        {
            "fact": "fixed_statement_availability",
            "before": "no fixed formal statement exists in the file",
            "after": "no fixed statement exists for the open question; fixed solved lower and upper variants are present",
            "materiality": "scope-caveat-added",
            "confidence": "exact-source-comparison",
        },
        {
            "fact": "solved_variant_comparison",
            "before": "not identified",
            "after": "identified but not compared",
            "materiality": "next-valid-work",
            "confidence": "declared-gap",
        },
    ]
    semantic_diff = {
        "schema": "vela.source-experiment.semantic-diff.v1",
        "case": "erdos:321",
        "algorithm": {
            "name": "closed-fact-comparison",
            "version": 1,
            "canonicalization": "RFC 8785",
            "generated_prose_in_fact_set": False,
        },
        "inputs": [
            {"path": "../definition-correspondence.v1.json", "sha256": sha256_file(v1_path)},
            {"path": "../definition-correspondence.v2.json", "sha256": sha256_file(v2_path)},
        ],
        "facts": facts,
        "fact_set_root": f"sha256:{sha256_bytes(jcs(facts))}",
        "correction_impact": {
            "predecessor_claim_id": "vcl_7dcd3ce703085fd34b2710229e0e68c1b661688050b352261821ef9bb376524a",
            "successor_claim_id": "vcl_8ea6c5aa6c39f13cd1e1209b8723957f16d291f7365ed7fb4e15b56ec7c48aed",
            "standing_effect": "successor accepted; predecessor retained as corrected history",
            "scientific_conclusion_changed": False,
            "review_reason_changed": True,
        },
    }

    loss_report = {
        "schema": "vela.source-experiment.semantic-loss.v1",
        "case": "erdos:321",
        "source_roots": {
            "formal_conjectures_sha256": f"sha256:{FORMAL_SHA256}",
            "starfleet_sha256": f"sha256:{STARFLEET_SHA256}",
        },
        "reference_resolution": {
            "exact": 4,
            "approximate": 0,
            "ambiguous": 0,
            "unresolved": 0,
            "failure_rule": "A quote that is absent or non-unique stops generation; it is never attached heuristically.",
        },
        "declared_losses": [
            {
                "kind": "proof-term-omission",
                "detail": "The reference map compares definitions and theorem statements, not Lean proof terms or the transitive dependency cone.",
                "authority_effect": "none",
            },
            {
                "kind": "normalization-to-semantic-facts",
                "detail": "Whitespace, comments, declaration order, and notation spelling are absent from the semantic fact set; exact source snapshots remain retained.",
                "authority_effect": "none",
            },
            {
                "kind": "unperformed-statement-comparison",
                "detail": "The Star Fleet terminal theorem is not compared with erdos_321.variants.lower or .upper.",
                "authority_effect": "blocks any claim of statement fidelity to those variants",
            },
            {
                "kind": "attestation-read-not-rebuild",
                "detail": "The kernel gate is the retained CI attestation at the pinned Star Fleet commit; this experiment does not rerun Lean.",
                "authority_effect": "none; Verification scope remains unchanged",
            },
            {
                "kind": "single-reviewer-ground-truth",
                "detail": "No independent expert-labelled semantic-diff corpus or review-time baseline exists yet.",
                "authority_effect": "experiment cannot support general accuracy or productivity claims",
            },
        ],
        "does_not_establish": [
            "That Erdős problem 321 is resolved or that the bound is optimal.",
            "That the semantic diff is accurate beyond this one corrected case.",
            "That a Web Annotation link or provenance record is Verification or acceptance.",
        ],
    }

    source_manifest = {
        "schema": "vela.source-experiment.snapshots.v1",
        "sources": [
            {
                "path": "sources/formal-conjectures-321.lean",
                "content_url": FORMAL_URL,
                "commit": FORMAL_COMMIT,
                "sha256": f"sha256:{FORMAL_SHA256}",
            },
            {
                "path": "sources/starfleet-basic.lean",
                "content_url": STARFLEET_URL,
                "commit": STARFLEET_COMMIT,
                "sha256": f"sha256:{STARFLEET_SHA256}",
            },
        ],
    }

    workflow = {
        "schema": "vela.source-experiment.translation-workflow.v1",
        "name": "Erdős 321 source-to-formalization translation",
        "steps": [
            "verify retained source snapshot digests",
            "resolve every Web Annotation quote exactly once and record character positions",
            "compare the closed correction fact set",
            "emit the explicit loss report",
            "bind inputs, activity, agent, and outputs in RO-Crate and PROV-O",
        ],
        "determinism": "All committed outputs are functions of retained bytes and constants in build.py; --check performs no network access.",
        "authority_effect": "none",
    }

    documents: dict[str, Any] = {
        "reference-annotations.v1.json": annotations,
        "semantic-diff.v1.json": semantic_diff,
        "semantic-loss.v1.json": loss_report,
        "source-snapshots.v1.json": source_manifest,
        "translation-workflow.v1.json": workflow,
    }
    output_digests = {name: sha256_bytes(rendered(value)) for name, value in documents.items()}

    graph: list[dict[str, Any]] = [
        {
            "@id": "ro-crate-metadata.json",
            "@type": "CreativeWork",
            "about": {"@id": "./"},
            "conformsTo": [
                {"@id": "https://w3id.org/ro/crate/1.1"},
                {"@id": "https://w3id.org/ro/crate/1.3"},
            ],
        },
        {
            "@id": "./",
            "@type": "Dataset",
            "name": "Erdős 321 source-to-formalization translation experiment",
            "description": "Exact cross-source references, a deterministic correction diff, declared semantic losses, and retrospective provenance for the corrected Erdős 321 definition correspondence.",
            "datePublished": "2026-08-09",
            "license": {"@id": "https://spdx.org/licenses/CC-BY-4.0"},
            "conformsTo": [
                {"@id": "https://w3id.org/ro/crate/1.3"},
                {"@id": "https://w3id.org/ro/wfrun/workflow/0.5"},
            ],
            "mainEntity": {"@id": "build.py"},
            "hasPart": [
                *({"@id": name} for name in documents),
                {"@id": "build.py"},
                {"@id": "sources/formal-conjectures-321.lean"},
                {"@id": "sources/starfleet-basic.lean"},
                {"@id": f"https://raw.githubusercontent.com/vela-science/math/{MATH_COMMIT}/evidence/erdos-321/definition-correspondence.v1.json"},
                {"@id": f"https://raw.githubusercontent.com/vela-science/math/{MATH_COMMIT}/evidence/erdos-321/definition-correspondence.v2.json"},
            ],
        },
        {
            "@id": "build.py",
            "@type": [
                "File",
                "SoftwareSourceCode",
                "ComputationalWorkflow",
                "https://bioschemas.org/ComputationalWorkflow",
            ],
            "name": "Deterministic Erdős 321 translation builder",
            "programmingLanguage": {"@id": "#python"},
            "conformsTo": {"@id": "https://w3id.org/workflowhub/workflow-ro-crate/1.0"},
        },
        {
            "@id": "#python",
            "@type": "ComputerLanguage",
            "name": "Python 3",
            "url": "https://www.python.org/",
        },
        {
            "@id": "#translation-run",
            "@type": ["CreateAction", "prov:Activity"],
            "name": "Build the Erdős 321 translation records",
            "actionStatus": "CompletedActionStatus",
            "startTime": RUN_TIME,
            "endTime": RUN_TIME,
            "instrument": {"@id": "build.py"},
            "agent": {"@id": "#codex-agent"},
            "object": [
                {"@id": f"https://raw.githubusercontent.com/vela-science/math/{MATH_COMMIT}/evidence/erdos-321/definition-correspondence.v1.json"},
                {"@id": f"https://raw.githubusercontent.com/vela-science/math/{MATH_COMMIT}/evidence/erdos-321/definition-correspondence.v2.json"},
                {"@id": "sources/formal-conjectures-321.lean"},
                {"@id": "sources/starfleet-basic.lean"},
            ],
            "result": [{"@id": name} for name in documents if name != "translation-workflow.v1.json"],
            "prov:wasAssociatedWith": {"@id": "#codex-agent"},
            "prov:used": [
                {"@id": f"https://raw.githubusercontent.com/vela-science/math/{MATH_COMMIT}/evidence/erdos-321/definition-correspondence.v1.json"},
                {"@id": f"https://raw.githubusercontent.com/vela-science/math/{MATH_COMMIT}/evidence/erdos-321/definition-correspondence.v2.json"},
                {"@id": "sources/formal-conjectures-321.lean"},
                {"@id": "sources/starfleet-basic.lean"},
            ],
            "prov:generated": [
                {"@id": name} for name in documents if name != "translation-workflow.v1.json"
            ],
        },
        {
            "@id": "#codex-agent",
            "@type": ["SoftwareApplication", "prov:Agent"],
            "name": "Codex workspace agent",
        },
        {
            "@id": "https://w3id.org/ro/crate/1.1",
            "@type": "CreativeWork",
            "name": "RO-Crate Metadata Specification 1.1",
        },
        {
            "@id": "https://w3id.org/ro/crate/1.3",
            "@type": "CreativeWork",
            "name": "RO-Crate Metadata Specification 1.3",
        },
        {
            "@id": "https://w3id.org/ro/wfrun/workflow/0.5",
            "@type": "CreativeWork",
            "name": "Workflow Run Crate profile 0.5",
        },
        {
            "@id": "https://w3id.org/workflowhub/workflow-ro-crate/1.0",
            "@type": "CreativeWork",
            "name": "Workflow RO-Crate profile 1.0",
        },
        {
            "@id": f"https://raw.githubusercontent.com/vela-science/math/{MATH_COMMIT}/evidence/erdos-321/definition-correspondence.v1.json",
            "@type": ["File", "prov:Entity"],
            "sha256": sha256_file(v1_path),
            "version": MATH_COMMIT,
        },
        {
            "@id": f"https://raw.githubusercontent.com/vela-science/math/{MATH_COMMIT}/evidence/erdos-321/definition-correspondence.v2.json",
            "@type": ["File", "prov:Entity"],
            "sha256": sha256_file(v2_path),
            "version": MATH_COMMIT,
        },
        {
            "@id": "sources/formal-conjectures-321.lean",
            "@type": ["File", "SoftwareSourceCode", "prov:Entity"],
            "contentUrl": FORMAL_URL,
            "sha256": FORMAL_SHA256,
            "version": FORMAL_COMMIT,
        },
        {
            "@id": "sources/starfleet-basic.lean",
            "@type": ["File", "SoftwareSourceCode", "prov:Entity"],
            "contentUrl": STARFLEET_URL,
            "sha256": STARFLEET_SHA256,
            "version": STARFLEET_COMMIT,
        },
    ]
    for name, digest in output_digests.items():
        entity = {
            "@id": name,
            "@type": ["File", "prov:Entity"],
            "encodingFormat": "application/ld+json" if name == "reference-annotations.v1.json" else "application/json",
            "sha256": digest,
            "prov:wasGeneratedBy": {"@id": "#translation-run"},
        }
        if name in {"semantic-diff.v1.json", "semantic-loss.v1.json"}:
            entity["prov:wasDerivedFrom"] = [
                {"@id": f"https://raw.githubusercontent.com/vela-science/math/{MATH_COMMIT}/evidence/erdos-321/definition-correspondence.v1.json"},
                {"@id": f"https://raw.githubusercontent.com/vela-science/math/{MATH_COMMIT}/evidence/erdos-321/definition-correspondence.v2.json"},
            ]
        graph.append(entity)
    documents["ro-crate-metadata.json"] = {
        "@context": [
            "https://w3id.org/ro/crate/1.3/context",
            "https://w3id.org/ro/terms/workflow-run/context",
            {"prov": "http://www.w3.org/ns/prov#"},
        ],
        "@graph": graph,
    }
    return documents


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if generated files drift")
    args = parser.parse_args()

    documents = build_documents()
    drift: list[str] = []
    for name, value in documents.items():
        expected = rendered(value)
        path = HERE / name
        if args.check:
            if not path.exists() or path.read_bytes() != expected:
                drift.append(name)
        else:
            path.write_bytes(expected)

    if drift:
        raise SystemExit("translation artifacts drift: " + ", ".join(drift))
    if args.check:
        print(f"erdos-321-translation: ok ({len(documents)} generated documents)")
    else:
        print(f"erdos-321-translation: wrote {len(documents)} generated documents")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
