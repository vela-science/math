#!/usr/bin/env python3
"""Generate the minimal public producer inputs and equivalence evidence.

This does not create evaluator-held check cards or concealed X/Y/Z mappings.
Those remain owned by the frozen Stage 2 evaluator procedure.
"""

import argparse
import hashlib
import json
import pathlib
import re
import subprocess

PILOT = "RESULTS-BREAKTHROUGH-01"
FC_COMMIT = "e13dd7284e72012a1616806d09cb6b8025e387af"
FC_TREE = "7d2b7c17ff144393c2b4a39973ed212387b3e783"
MATH_COMMIT = "5de716c896065c03c0a470d015ba2a328a527f73"
MATH_TREE = "56e37a5058c80e69f3c343b8ae624c08b5417229"
LEAN_COMMIT = "accf62cb636c8909dd7e098e3f82b2140d3a192e"
LEAN_TREE = "608ce332d1d5d8f14abc7d39349f4a29102f5aba"
VELA_COMMIT = "88fcc0105eba35ee22ed1816d3aabba3322bebc1"
VELA_TREE = "2cb85fe1e1c3525ba97ff2aec25945417ea7b372"
CURRENT_IMAGE = "526fdb202378ca02eb5946c75bc4d319751336c0ad88162c671fbe89950d1750"

TARGETS = [
    {
        "id": "T01", "number": "23", "category": "proof_opportunity", "smoke": True,
        "declaration": "Erdos23.erdos_23.variants.n1",
        "canonical_statement": "∀ (G : SimpleGraph (Fin 5)), G.CliqueFree 3 → ∃ (H : SimpleGraph (Fin 5)), H ≤ G ∧ H.IsBipartite ∧ (G.edgeFinset \\ H.edgeFinset).card ≤ 1",
        "domain": ["G ranges over SimpleGraph (Fin 5)", "G is CliqueFree 3", "H must be a subgraph of G and bipartite", "at most one G edge is absent from H"],
        "objective": "Produce an exact checked Lean proof, or a correctly scoped typed non-result. Enumeration alone is a computational certificate until the declaration builds.",
        "semantic": ["Check all graph, clique-free, subgraph, bipartite, and edge-difference conditions against the exact theorem type.", "If enumeration is used, independently confirm exhaustive coverage of SimpleGraph (Fin 5)."],
        "prior": "No exact declaration occurrence or checked proof was found in frozen Math or lean-proofs; the FC declaration remains sorry.",
    },
    {
        "id": "T02", "number": "138", "category": "proof_opportunity", "smoke": True,
        "declaration": "Erdos138.monoAPNumber_two_two",
        "canonical_statement": "W 2 = 3, where W k := sInf (monoAP_guarantee_set 2 k)",
        "domain": ["colorings have domain Finset.Icc 1 N and codomain Fin 2", "W is a Nat sInf", "the lower and upper directions and nonempty/sInf dependencies must be explicit"],
        "objective": "Independently realize an exact source-native checked proof of W 2 = 3 from mounted bytes. This objective permits independent proof production but forbids claiming theorem novelty.",
        "semantic": ["Check both W 2 ≤ 3 and 3 ≤ W 2 under the exact Nat sInf definition.", "Inspect the dependency on monoAP_guarantee_set_nonempty and any axioms used."],
        "prior": "Frozen Math contains occurrence/provenance metadata pointing to XC0R/formal-conjectures@6c7a16e..., but records build_outcome not_attempted and axiom status not_read; those external proof bytes are absent from the mounted source set.",
    },
    {
        "id": "T03", "number": "359", "category": "proof_opportunity", "smoke": False,
        "declaration": "Erdos359.erdos_359.variants.isGoodFor_1_low_values",
        "canonical_statement": "∀ A : ℕ → ℕ, IsGoodFor A 1 → A '' (Set.Iic 7) = {1, 2, 4, 5, 8, 10, 14, 15}",
        "domain": ["indices are Nat and the image domain is Set.Iic 7", "IsGoodFor includes A 0 = 1, StrictMono A, and an IsLeast recurrence"],
        "objective": "Derive the exact eight-value image equality in Lean or retain a typed non-result.",
        "semantic": ["Check every index 0 through 7 and both inclusions of the image equality.", "Check consecutive-sum exclusions and leastness, not only numeric plausibility."],
        "prior": "No exact declaration occurrence or checked proof was found in frozen Math or lean-proofs; the FC declaration remains sorry.",
    },
    {
        "id": "T04", "number": "1052", "category": "proof_opportunity", "smoke": False,
        "declaration": "Erdos1052.isUnitaryPerfect_87360",
        "canonical_statement": "IsUnitaryPerfect 87360",
        "domain": ["properUnitaryDivisors uses Finset.Ico 1 n", "a divisor d must divide n and be coprime to n / d", "the divisor sum equals n and 0 < n"],
        "objective": "Replace the deliberate stop with the smallest checked proof that completes inside the frozen resource limit, or retain an exact certificate/performance non-result.",
        "semantic": ["Recompute all proper unitary divisors and their exact sum independently.", "A computed certificate is not a Lean theorem unless the exact declaration builds."],
        "prior": "No exact declaration occurrence or checked proof was found in frozen Math or lean-proofs; FC contains a deliberate stop before a known-too-slow tactic route.",
    },
    {
        "id": "T05", "number": "1062", "category": "statement_correction", "smoke": False,
        "declaration": "Erdos1062.ForkFree",
        "canonical_statement": "ForkFree (A : Set ℕ) := ∀ a ∈ A, ({b | b ∈ A \\ {a} ∧ a ∣ b} : Set ℕ).Subsingleton",
        "domain": ["A is a Set Nat and ForkFree alone permits zero", "the downstream f restricts A ⊆ Set.Icc 1 n"],
        "objective": "Determine whether the positive-integer wording requires a documentation change, definition change, or no change, and prove every claimed equivalence or edge case.",
        "semantic": ["Test sets containing zero under Nat divisibility.", "Separate semantics of ForkFree alone from its constrained use in f."],
        "prior": "No exact declaration occurrence was found in frozen Math or lean-proofs; this is a source-semantics correction target, not a theorem novelty claim.",
    },
    {
        "id": "T06", "number": "170", "category": "statement_correction", "smoke": False,
        "declaration": "Erdos170.PerfectRuler",
        "canonical_statement": "PerfectRuler N A := ∀ k ∈ Finset.range (N + 1), ∃ᵉ (a₀ ∈ A) (a₁ ∈ A), k = a₁ - a₀",
        "domain": ["Finset.range (N + 1) includes k = 0", "Nat subtraction is truncated", "N = 0 and empty/nonempty ruler edge cases matter"],
        "objective": "Classify the zero clause as redundant, edge-case strengthening, documentation issue, source bug, or no correction using exact source semantics.",
        "semantic": ["Prove or refute equivalence with quantification over positive k ≤ N.", "Check N = 0, empty A, and singleton A."],
        "prior": "No exact declaration occurrence was found in frozen Math or lean-proofs; this is a source-semantics correction target.",
    },
    {
        "id": "T07", "number": "835", "category": "dependency_trust", "smoke": False,
        "declaration": "Erdos835.johnsonGraph_chromaticNumber_odd_of_johnson_chromaticNumber_composite",
        "canonical_statement": "(type_of% johnson_chromaticNumber_composite) → (type_of% johnson_chromaticNumber_odd)",
        "domain": ["the bridge is an implication between exact theorem types", "johnson_chromaticNumber_composite remains sorry", "the bridge alone proves neither premise nor unconditional odd case"],
        "objective": "Validate the checked implication and exact dependency closure, and only if possible discharge or narrow the load-bearing unresolved premise.",
        "semantic": ["Run the exact bridge proof and print its axioms/dependencies.", "Do not promote a checked implication into an unconditional chromatic-number theorem."],
        "prior": "No exact declaration occurrence was found in frozen Math or lean-proofs; the bridge has proof bytes in FC but its premise is unresolved.",
    },
    {
        "id": "T08", "number": "1145", "category": "dependency_trust", "smoke": False,
        "declaration": "Erdos1145.erdos_1145.test_implies_erdos_28",
        "canonical_statement": "Erdos1145Prop → type_of% Erdos28.erdos_28",
        "domain": ["Erdos1145Prop quantifies over infinite Set Nat", "the formalization intentionally includes zero", "the imported target is FormalConjectures.ErdosProblems.28"],
        "objective": "Validate the checked implication and inclusion-of-zero convention; distinguish the bridge from proof of either open conjecture.",
        "semantic": ["Build the bridge against the exact imported 28.lean bytes.", "Inspect both theorem types and report axioms without claiming either premise."],
        "prior": "No exact declaration occurrence was found in frozen Math or lean-proofs; the implication has proof bytes in FC and both open conjecture assertions remain unresolved.",
        "related": ["FormalConjectures/ErdosProblems/28.lean"],
    },
    {
        "id": "T09", "number": "14", "category": "negative_control", "smoke": False,
        "declaration": "Erdos14.erdos_14.parts.i",
        "canonical_statement": "answer(sorry) ↔ ∀ A, ∀ ε > 0, nonUniqueSumCount A ≫ almostSquareRoot ε",
        "domain": ["A is a Set Nat", "ε is real and positive", "the asymptotic relation and answer placeholder are exact source semantics"],
        "objective": "Search the frozen sources for a checked proof, counterexample, exact correction, or dependency discharge; otherwise return a precise typed non-result.",
        "semantic": ["Do not infer literature status from absence in the mounted corpus.", "A valid non-result must report strongest verified partial progress and the exact blocker."],
        "prior": "No exact declaration occurrence or checked proof was found in frozen Math or lean-proofs; FC remains sorry.",
    },
    {
        "id": "T10", "number": "208", "category": "negative_control", "smoke": False,
        "declaration": "Erdos208.erdos_208.parts.i",
        "canonical_statement": "answer(sorry) ↔ ∀ ε > (0 : ℝ), (fun n => (s (n + 1) - s n : ℝ)) =O[atTop] (fun n => (s n : ℝ)^ε)",
        "domain": ["s n := Nat.nth Squarefree", "ε is real and positive", "the claim is an atTop Big-O statement"],
        "objective": "Search the frozen sources for a checked proof, counterexample, correction, or dependency discharge; otherwise return a precise typed non-result.",
        "semantic": ["Do not infer current literature truth from corpus absence.", "A valid non-result must report strongest verified partial progress and the exact blocker."],
        "prior": "No exact declaration occurrence or checked proof was found in frozen Math or lean-proofs; FC remains sorry.",
    },
]


def run(*args, cwd=None, check=True):
    return subprocess.run(args, cwd=cwd, check=check, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def git(repo, *args, check=True):
    return run("git", "-C", str(repo), *args, check=check)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical(value) + "\n", encoding="utf-8")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_fact(fact_id, role, uri, commit, tree, path, data, note=None):
    return {
        "fact_id": fact_id,
        "role": role,
        "source": {"uri": uri, "commit_or_version": commit, "tree": tree, "path": path, "byte_range": None},
        "payload_sha256": sha(data),
        "byte_length": len(data),
        "media_type": "application/json" if path.endswith(".json") else "text/plain; charset=utf-8",
        "interpretation_note": note,
    }


def grep_records(repo, commit, query):
    result = git(repo, "grep", "-n", "-F", query, commit, "--", check=False)
    if result.returncode not in (0, 1):
        raise RuntimeError(result.stderr.decode())
    records = []
    for line in result.stdout.decode("utf-8").splitlines():
        match = re.match(r"^[0-9a-f]+:(.*?):([0-9]+):(.*)$", line)
        if not match:
            raise RuntimeError(f"unexpected git grep record: {line!r}")
        path, line_number, text = match.groups()
        records.append({"path": path, "line": int(line_number), "text": text.strip()})
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment-root", type=pathlib.Path, required=True)
    parser.add_argument("--math", type=pathlib.Path, required=True)
    parser.add_argument("--fc", type=pathlib.Path, required=True)
    parser.add_argument("--lean-proofs", type=pathlib.Path, required=True)
    parser.add_argument("--vela", type=pathlib.Path, required=True)
    args = parser.parse_args()
    root = args.experiment_root.resolve()

    expected = [(args.math, MATH_COMMIT), (args.fc, FC_COMMIT), (args.lean_proofs, LEAN_COMMIT), (args.vela, VELA_COMMIT)]
    for repo, commit in expected:
        git(repo, "cat-file", "-e", commit + "^{commit}")

    common_prompt = (root / "prompts/common-objective.txt").read_bytes()
    parameters = (root / "runtime/parameters.json").read_bytes()
    tools = (root / "runtime/tool-allowlist.json").read_bytes()
    runner_bytes = (root / "scripts/run-cell.sh").read_bytes()
    secret_scan_bytes = (root / "scripts/secret-scan.py").read_bytes()
    blind_packager_bytes = (root / "scripts/package-blind.py").read_bytes()
    materializer_bytes = (root / "scripts/materialize-facts.py").read_bytes()
    mount_verifier_bytes = (root / "scripts/verify-mounts.sh").read_bytes()
    source_bindings = {
        "math": {"commit": MATH_COMMIT, "tree": MATH_TREE, "git_archive_tar_sha256": "f3b983aba2ea5c8056b82e039204ec973246fe7f7c66a7b250b238a9fe4e6779"},
        "formal_conjectures": {"commit": FC_COMMIT, "tree": FC_TREE, "git_archive_tar_sha256": "6a929b14796348e84badc6972524640688d98eac40fbbc91eadd0d744f39d647"},
        "lean_proofs": {"commit": LEAN_COMMIT, "tree": LEAN_TREE, "git_archive_tar_sha256": "b28285a85b08e472cc5183c4dfeebaea821127f0c65baa3a4eb865daf5ed6ee9"},
        "vela": {"commit": VELA_COMMIT, "tree": VELA_TREE, "git_archive_tar_sha256": "05a87f07789e0c8d77d85665c25504712cd70bea328b2c0f9e7ce57dc5b01c24"},
    }
    write_json(root / "runtime/source-bindings.json", source_bindings)
    source_binding_bytes = (root / "runtime/source-bindings.json").read_bytes()
    wrapper_analysis = {
        "policy": "Arm wrapper files are byte-identical, so their token sequences are identical under any common tokenizer. They are organization-only and excluded from normalized scientific prompt hashes. The common runner enforces the same 8192 UTF-8-byte result.json allowance for every arm.",
        "tokenizer_count_available": False,
        "tokenizer_count_not_required_reason": "Byte identity plus a common model and tokenizer implies token-sequence identity; no model-specific tokenizer estimate is substituted for that exact check.",
        "wrappers": {},
    }
    for arm in ("N", "G", "V"):
        data = (root / "prompts" / f"arm-{arm}.txt").read_bytes()
        wrapper_analysis["wrappers"][arm] = {"bytes": len(data), "lines": len(data.splitlines()), "sha256": sha(data)}
    write_json(root / "runtime/wrapper-analysis.json", wrapper_analysis)
    wrapper_analysis_bytes = (root / "runtime/wrapper-analysis.json").read_bytes()

    duplicate_records = []
    for target in TARGETS:
        target_path = f"FormalConjectures/ErdosProblems/{target['number']}.lean"
        target_bytes = git(args.fc, "show", f"{FC_COMMIT}:{target_path}").stdout
        blob = git(args.fc, "rev-parse", f"{FC_COMMIT}:{target_path}").stdout.decode().strip()
        line = next(i for i, value in enumerate(target_bytes.decode().splitlines(), 1) if target["declaration"].split(".")[-1] in value)
        card = {
            "kind": "producer_input_card",
            "pilot_id": PILOT,
            "target_id": target["id"],
            "category": target["category"],
            "smoke": target["smoke"],
            "source_bindings": [{
                "repository": "https://github.com/google-deepmind/formal-conjectures.git",
                "commit": FC_COMMIT,
                "tree": FC_TREE,
                "path": target_path,
                "line": line,
                "git_blob": blob,
                "sha256": sha(target_bytes),
            }],
            "declaration": target["declaration"],
            "canonical_statement": target["canonical_statement"],
            "domain_conditions": target["domain"],
            "objective": target["objective"],
            "known_prior_result_or_metadata": target["prior"],
            "allowed_dependencies": ["exact mounted source trees in runtime/source-bindings.json", "frozen toolchain and dependency locks"],
            "forbidden_dependencies": ["unmounted external proof bytes", "network source discovery", "sorry/stop as proof", "another arm's output", "canonical authority"],
            "trust_boundary": "Lean kernel/build, declared imported axioms, or exact replayed checker only; build success is not source-owner acceptance.",
            "smallest_source_native_commands": [["lake", "env", "lean", target_path], ["lake", "env", "lean", f"/work/checks/{target['id']}-axioms.lean"]],
            "semantic_checks": target["semantic"],
            "rights": "Formal Conjectures Apache-2.0; candidate-created artifacts must declare compatible inspect/execute/redistribute rights.",
            "valid_non_result_rule": "Report the strongest verified partial progress, exact failed route or dependency, and corpus-limited scope; do not call absence proof of openness or impossibility.",
            "resource_limit": {"wall_seconds": 720, "memory_bytes": 8589934592},
        }
        if target.get("related"):
            for related in target["related"]:
                data = git(args.fc, "show", f"{FC_COMMIT}:{related}").stdout
                card["source_bindings"].append({
                    "repository": "https://github.com/google-deepmind/formal-conjectures.git",
                    "commit": FC_COMMIT, "tree": FC_TREE, "path": related,
                    "git_blob": git(args.fc, "rev-parse", f"{FC_COMMIT}:{related}").stdout.decode().strip(),
                    "sha256": sha(data),
                })
        card_path = root / "cards" / f"{target['id']}.json"
        write_json(card_path, card)

        exact_math = grep_records(args.math, MATH_COMMIT, target["declaration"])
        exact_lean = grep_records(args.lean_proofs, LEAN_COMMIT, target["declaration"])
        path_math = grep_records(args.math, MATH_COMMIT, target_path)
        duplicate = {
            "target_id": target["id"],
            "declaration": target["declaration"],
            "universe": source_bindings,
            "exact_declaration_matches": {"math": exact_math, "lean_proofs": exact_lean},
            "source_path_matches_in_math": path_math,
            "formal_conjectures_status": "checked_bridge" if target["id"] in {"T07", "T08"} else ("deliberate_stop" if target["id"] == "T04" else "sorry_or_definition"),
            "external_linked_commits_present_in_mounted_fc_objects": ({
                commit: git(args.fc, "cat-file", "-e", commit + "^{commit}", check=False).returncode == 0
                for commit in ("6c7a16e8998d1c597fa2a5c6329bc9301fcc56e2", "6ac8d0cbe1a85e71747c62c1391a84788015ebc1")
            } if target["id"] == "T02" else None),
            "conclusion": (
                "known_occurrence_metadata_only; mounted FC declaration remains sorry; external linked proof bytes are absent; target retained solely for explicitly allowed independent proof realization and no theorem-novelty claim"
                if target["id"] == "T02" else
                "no exact declaration occurrence in frozen Math or lean-proofs; this is not a claim about sources outside the frozen universe"
            ),
        }
        duplicate_path = root / "duplicates" / f"{target['id']}.json"
        write_json(duplicate_path, duplicate)
        duplicate_records.append(duplicate)

        facts = [
            file_fact("target-source", "target_statement", "https://github.com/google-deepmind/formal-conjectures.git", FC_COMMIT, FC_TREE, target_path, target_bytes, "Entire exact target file; declaration identified by the producer card."),
            file_fact("producer-card", "constraint", "producer-preregistration", "successor-of-0bbf3b8", None, f"cards/{target['id']}.json", card_path.read_bytes(), "Candidate-facing card; not the evaluator-held check card."),
            file_fact("duplicate-record", "prior_result", "producer-preregistration", "successor-of-0bbf3b8", None, f"duplicates/{target['id']}.json", duplicate_path.read_bytes(), "Search is limited to the frozen universe and distinguishes metadata from proof bytes."),
            file_fact("source-bindings", "dependency_trust", "producer-preregistration", "successor-of-0bbf3b8", None, "runtime/source-bindings.json", source_binding_bytes),
            file_fact("common-objective", "tool_instruction", "producer-preregistration", "successor-of-0bbf3b8", None, "prompts/common-objective.txt", common_prompt),
            file_fact("runtime-parameters", "constraint", "producer-preregistration", "successor-of-0bbf3b8", None, "runtime/parameters.json", parameters),
            file_fact("tool-allowlist", "constraint", "producer-preregistration", "successor-of-0bbf3b8", None, "runtime/tool-allowlist.json", tools),
            file_fact("wrapper-analysis", "constraint", "producer-preregistration", "successor-of-0bbf3b8", None, "runtime/wrapper-analysis.json", wrapper_analysis_bytes),
            file_fact("cell-runner", "tool_instruction", "producer-preregistration", "successor-of-0bbf3b8", None, "scripts/run-cell.sh", runner_bytes),
            file_fact("credential-scan", "tool_instruction", "producer-preregistration", "successor-of-0bbf3b8", None, "scripts/secret-scan.py", secret_scan_bytes),
            file_fact("blind-packager", "tool_instruction", "producer-preregistration", "successor-of-0bbf3b8", None, "scripts/package-blind.py", blind_packager_bytes),
            file_fact("fact-materializer", "tool_instruction", "producer-preregistration", "successor-of-0bbf3b8", None, "scripts/materialize-facts.py", materializer_bytes),
            file_fact("mount-verifier", "tool_instruction", "producer-preregistration", "successor-of-0bbf3b8", None, "scripts/verify-mounts.sh", mount_verifier_bytes),
        ]
        license_bytes = git(args.fc, "show", f"{FC_COMMIT}:LICENSE").stdout
        facts.append(file_fact("source-license", "rights_license", "https://github.com/google-deepmind/formal-conjectures.git", FC_COMMIT, FC_TREE, "LICENSE", license_bytes))
        for index, related in enumerate(target.get("related", []), 1):
            data = git(args.fc, "show", f"{FC_COMMIT}:{related}").stdout
            facts.append(file_fact(f"related-source-{index}", "lemma", "https://github.com/google-deepmind/formal-conjectures.git", FC_COMMIT, FC_TREE, related, data))
        if target["id"] == "T02":
            for index, path in enumerate(("evaluations/fc-build-audit-v1/builds.json", "evaluations/fc-conditional-proof-audit-v1/results.json"), 1):
                data = git(args.math, "show", f"{MATH_COMMIT}:{path}").stdout
                facts.append(file_fact(f"known-occurrence-metadata-{index}", "prior_result", "https://github.com/vela-science/math.git", MATH_COMMIT, MATH_TREE, path, data, "Occurrence/provenance metadata, not mounted external proof bytes or a checked proof."))
        # Order is load-bearing: do not sort. This binds the exact fact sequence
        # and detects a semantically meaningful reordering.
        root_lines = [canonical({key: fact[key] for key in ("fact_id", "payload_sha256", "byte_length", "role")}) for fact in facts]
        fact_root = sha(("\n".join(root_lines) + "\n").encode())
        fact_pack = {"pilot_id": PILOT, "target_id": target["id"], "facts": facts, "scientific_fact_root": fact_root}
        write_json(root / "fact-packs" / f"{target['id']}.json", fact_pack)

    write_json(root / "duplicates/index.json", {
        "pilot_id": PILOT,
        "generated_from": source_bindings,
        "target_count": len(duplicate_records),
        "records": duplicate_records,
        "prior_result_factory_exclusions": ["321", "750", "56", "94", "887", "697-delta", "822", "1", "291", "399", "945", "318", "697-threshold", "683/961", "260", "479", "849", "850", "1074", "1063", "1136", "120", "214", "251", "938"],
    })

    smoke = ["T01-N", "T02-G", "T01-V", "T02-N", "T01-G", "T02-V"]
    remaining = ["T03-V", "T04-N", "T05-G", "T06-V", "T07-N", "T08-G", "T09-V", "T10-N", "T03-N", "T04-G", "T05-V", "T06-N", "T07-G", "T08-V", "T09-N", "T10-G", "T03-G", "T04-V", "T05-N", "T06-G", "T07-V", "T08-N", "T09-G", "T10-V"]
    write_json(root / "assignments.json", {
        "pilot_id": PILOT,
        "candidate_cells": 30,
        "smoke_sequence": smoke,
        "post_smoke_sequence": remaining,
        "per_target_arm_order": {t["id"]: [cell.split("-")[1] for cell in smoke + remaining if cell.startswith(t["id"] + "-")] for t in TARGETS},
        "concealed_blind_permutation": "evaluator-owned Stage 2 held-out material; absent from producer bytes",
        "stage2_held_out_aggregate_sha256": None,
    })

    context_lines = ["mode\ttype\tgit_oid\tsha256\tbytes\tpath"]
    for record in git(args.vela, "ls-tree", "-r", "-z", VELA_COMMIT).stdout.split(b"\0"):
        if not record:
            continue
        meta, path_bytes = record.split(b"\t", 1)
        mode, kind, oid = meta.decode().split(" ")
        if kind != "blob":
            raise RuntimeError(f"unsupported Vela context object: {kind} {path_bytes!r}")
        data = git(args.vela, "cat-file", "blob", oid).stdout
        path_text = path_bytes.decode("utf-8")
        context_lines.append(f"{mode}\t{kind}\t{oid}\t{sha(data)}\t{len(data)}\t{path_text}")
    context_bytes = ("\n".join(context_lines) + "\n").encode()
    context_path = root / "build/vela-context.tsv"
    context_path.parent.mkdir(parents=True, exist_ok=True)
    context_path.write_bytes(context_bytes)
    dockerfile_sha = sha((root / "Dockerfile").read_bytes())
    write_json(root / "build/BUILD-LOCK.json", {
        "schema": "results-breakthrough-build-lock.v1",
        "vela_commit": VELA_COMMIT,
        "vela_tree": VELA_TREE,
        "context_file_count": len(context_lines) - 1,
        "context_manifest_sha256": sha(context_bytes),
        "dockerfile_sha256": dockerfile_sha,
        "builder_image": "rust:1.97.1-bookworm@sha256:0e2bcaef56d041a486784e54104a81aebe0da44bd03019bd70bc0401e42e4a97",
        "runtime_base_image": "vela-math-result-candidate@sha256:c290b6490fb78c3702694b311fe9f07bd03002d7c1c979b3e5723d6b9f579e01",
        "proposed_machine_id": "af94b40fa642620275e6d617be97a542\n",
        "build_command": ["scripts/build-image.sh", "--approval-receipt", "<commit-bound-independent-pass.json>", "--vela-repo", "<complete-vela-clone>"],
        "authorized_now": False,
    })

    reader_paths = [root / "readers/reader-1.json", root / "readers/reader-2.json"]
    if all(path.exists() for path in reader_paths):
        reader_reports = [json.loads(path.read_text()) for path in reader_paths]
        review_method_report = json.loads((root / "readers/review-method-schema-validation.json").read_text())
        for target in TARGETS:
            fact_pack = json.loads((root / "fact-packs" / f"{target['id']}.json").read_text())
            normalized = common_prompt + b"\n" + (root / "cards" / f"{target['id']}.json").read_bytes()
            for arm in ("N", "G", "V"):
                suffix = "record.sh" if arm == "N" else ("record.py" if arm == "G" else "lifecycle.sh")
                organization = [root / "prompts" / f"arm-{arm}.txt", root / "arms" / arm / suffix]
                reports = reader_reports
                if arm == "V":
                    organization.extend([
                        root / "arms/V/blinded-review-method.json",
                        root / "arms/V/review-method.schema.json",
                        root / "scripts/validate-review-method.py",
                    ])
                    reports = reader_reports + [review_method_report]
                manifest = {
                    "pilot_id": PILOT,
                    "target_id": target["id"],
                    "arm": arm,
                    "scientific_fact_root": fact_pack["scientific_fact_root"],
                    "normalized_prompt_sha256": sha(normalized),
                    "organization_files": [{"path": str(p.relative_to(root)), "sha256": sha(p.read_bytes()), "classification": "organization_only"} for p in organization],
                    "runtime": {
                        "model": "gpt-5.6-sol",
                        "parameters_sha256": sha(parameters),
                        "tool_allowlist_sha256": sha(tools),
                        "container_sha256": CURRENT_IMAGE,
                        "timeout_seconds": 720,
                        "retry_limit": 0,
                        "scientific_output_budget": 8192,
                    },
                    "reader_verdicts": [{"reader": r["reader"], "verdict": r["verdict"], "discrepancies": r["discrepancies"]} for r in reports],
                }
                write_json(root / "equivalence" / f"{target['id']}-{arm}.json", manifest)


if __name__ == "__main__":
    main()
