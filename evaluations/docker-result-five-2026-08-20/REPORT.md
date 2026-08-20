# Independent evaluation — Docker Result Factory five

Frozen input: Math commit `8b53d5d16b8eb30ba7f3d8e1aaefee3db8b6cc14`, tree `f2a7be8fd54f6c3fad74e066d79d167f6026076e`, producer directory `results/2026-08-20-docker-five/`. All five assigned cases remain in the denominator. No producer byte, source repository, Vela record, authority state, or external system was changed.

Rubric: `qualified_candidate` means the proposed bounded result is correct and source-backed, even if duplication or authority scope prevents conversion; `needs_correction` means the central observation is usable but a material scope or evidence statement must be corrected; `valid_non_result` means abstention is correct and well scoped; `invalid` means the central conclusion is wrong or unsupported.

## Disposition

No case is ready for a separate Vela conversion task. Cases 2 and 4 are correct bounded candidates, but both duplicate retained exact evidence; Case 4 already has an accepted current Math Claim. Case 1 is a valid non-result. Cases 3 and 5 require scoped corrections before reuse.

### Case 4 — Erdős 94 sum multiplicity

- verdict: `qualified_candidate`
- correctness and scope: Correct for `Erdos94.erdos_94.variants.sum_multiplicity` only. The exact proof explicitly identifies every off-diagonal `Sym2` fiber with the two distinct representatives `(a,b)` and `(b,a)`, proves the ordered fiber cardinality is twice the unordered fiber cardinality before natural-number division, partitions unordered pairs by distance, and applies `Sym2.card_image_offDiag`. It does not address the cubic Erdős 94 theorem or the other variants.
- exact evidence/build outcome: Proof commit/tree `423344341fbfdf4f8f684a302c5d05379125e7dc` / `eae3c8d1941c997f1055f5ea561cb719088b9202`; proof SHA-256 `412975add8b6963bb44378f5d8ef41fd1f860b9ec06495432ab97e8ca60ffbe0`; target commit/tree `94a278e06a8bcbc2e4f2935e491c0c115ec832e0` / `3caf62b9e8c71e670ca6de049bb715c1c1f1c278`. The target definitions are syntactically equivalent to the ordered `offDiag.image` distance set and ordered-cardinality-divided-by-two multiplicity used by the proof. A clean Lean 4.29.1 / Mathlib `5e932f97dd25535344f80f9dd8da3aab83df0fe6` checkout built `ErdosProblems.Erdos94SumMultiplicity` successfully (`8248/8248` jobs); `#print axioms Erdos94.variants.sum_multiplicity` returned exactly `propext`, `Classical.choice`, `Quot.sound`.
- novelty or duplication status: Exact duplicate of the current accepted Math assertion over the same proof and target bytes, current Claim `vcl_6763ba247d40303408a268b226c3e27d7a753b63fca3eb0de99619d509346bfb` at root `sha256:aaaf6ebbf510ad08e6376c5958d23f4eb7704944f7d37916eee4ae253e809b3b`.
- unresolved assumptions/dependencies/rights: Occurrence association remains navigation-only and does not establish cross-source semantic equivalence; source-owner adoption and external acceptance remain absent. These do not undermine the bounded theorem.
- ready for a separate Vela conversion task: No. Conversion would duplicate an already accepted exact Claim and add no scientific content.
- minimal correction if not ready: No mathematical correction. Add a pre-proposal duplicate check against current Vela Claims and suppress this output from conversion routing.

### Case 5 — Erdős 887 negative control

- verdict: `needs_correction`
- correctness and scope: The core non-result is correct for the open uniform-upper-bound assertion: the retained source and repair contain no closed witness `K` and no proof of `Erdos887.erdos_887.variant_i`. The blanket statement that no proof-bearing related declaration or number-theory argument is present is too broad.
- exact evidence/build outcome: Retained source, patch, and replay roots match `3e4c9376...706c5`, `0fee5a4d...fa24`, and `21d7b291...dc6a`. Applying the zero-context repair to fork commit/tree `288608562e684a2f3c97ba0ce960a2649a71370b` / `db331ce2429aa6a53e30a66325493e0ad6b1d0b5` produced the recorded content root `249ba4bc...8f01`; Lean 4.22.0 elaborated it with exactly four `declaration uses 'sorry'` warnings. Separately, the retained conditional-proof audit points to `jarekkoch-hub/erdos887-lean@230bf2cd0bc15f971ad9d0e36f36f2056dd9d8b7`, where a clean Lean 4.26.0-rc2 build completed `7663/7663` jobs and `#print axioms` for `erdos_887_variants_rosenfeld_infinite` returned only `propext`, `Classical.choice`, `Quot.sound`. That theorem constructs a related lower-bound family with `C = 64`; it does not construct the open upper-bound witness `K`. The apparent `erdos_887_parts_ii` upper theorem still takes an unclosed `ExternalReconstructionSource` argument.
- novelty or duplication status: The repaired-source non-result duplicates the already retained accepted replay claim. The Rosenfeld lower-bound proof is related evidence already named in `evaluations/fc-conditional-proof-audit-v1/`, not a new discovery by the Docker output and not an exact proof of `variant_i`.
- unresolved assumptions/dependencies/rights: No closed upper-bound reconstruction package or `K` witness exists in the inspected bytes. The external related repository is MIT-licensed at the pinned commit; statement fidelity to any exact Formal Conjectures variant was not established here.
- ready for a separate Vela conversion task: No. The assigned open assertion remains a non-result, and the missed related theorem is neither the requested witness nor a candidate packet with exact occurrence fidelity.
- minimal correction if not ready: Restrict the absence claim to `evidence/current/erdos-887` and its current Math records; explicitly disclose the separate unconditional Rosenfeld lower-bound theorem and explain why it does not prove or imply the uniform upper bound.

### Case 1 — Erdős 321 status conflict

- verdict: `valid_non_result`
- correctness and scope: Correct. `teorth/erdosproblems` says overall/informal `solved` and formal `unformalized`; Formal Conjectures marks the exact-answer, `IsTheta`, `IsBigO`, and `IsLittleO` occurrences `research open`. Metadata disagreement alone identifies neither a solution nor its statement scope.
- exact evidence/build outcome: Clean exact checkouts reproduced `teorth/erdosproblems@931e7db4ee3c97705598f802e8358a201b9e422c` (tree `9400db56013775cafa03530d85f4090e956d4580`) and `formal-conjectures@9f5ee773841921f460b4a26a3552f5eca4accaa0` (tree `cca3d86e3081eaf75667fbc8a62a3fdb03b95ef6`). Running the exact Formal Conjectures status logic against the exact YAML returned `{'number': '321', 'lean_status': 'open', 'yaml_status': 'solved'}`. The retained FC snapshot SHA-256 `601d8486...2357` matches the pinned source exactly.
- novelty or duplication status: Duplicate of the existing bounded packet and known open status mismatch; it adds no mathematical result and does not supersede the accepted Math Claim's explicit “remains open” caveat.
- unresolved assumptions/dependencies/rights: The citation/result behind `solved` and its mapping to each of the four Lean occurrences remain unknown. Source owners control status meaning; Math authority cannot infer it.
- ready for a separate Vela conversion task: No. This is a correct abstention, not a convertable scientific Result.
- minimal correction if not ready: No correction to the non-result. The smallest new evidence that could change it is the exact source-owner-backed result behind `solved`, followed by a four-occurrence statement comparison.

### Case 2 — Erdős 750 conditional dependency

- verdict: `qualified_candidate`
- correctness and scope: Correct as an exact external-source conditional result: `Erdos750.erdos_750_FC` derives its universe-0 graph assertion from `Erdos750.stiebitz_lower_bound`. It is not an unconditional proof of Stiebitz or of the universe-polymorphic Formal Conjectures occurrence.
- exact evidence/build outcome: Clean checkout `Shashi456/erdos-formalizations@286f856aa3fc08957b80950fd18a45aab8d045ea`, tree `7afc730ddbd7261707240eeae90a0da808802d72`, built `Erdos.P750.Proof` under Lean 4.27.0 / Mathlib `a3a10db0e9d66acbebf76c5e6a135066525ac900` (`7885/7885` jobs). `#print axioms Erdos750.erdos_750_FC` returned exactly `propext`, `Classical.choice`, `Erdos750.stiebitz_lower_bound`, `Quot.sound`. Full elaboration confirms the external existential uses universe 0. A literal `Type*` comparison proposition elaborates as `typeStarStatement.{u} : Prop` and is not definitionally equal to the `Type` proposition; the attempted `rfl` comparison fails. No checked `ULift`/graph-transport bridge is retained.
- novelty or duplication status: Duplicates the existing source-bound packet and exact build-audit finding. The useful Result is the already disclosed conditional dependency, not a new proof.
- unresolved assumptions/dependencies/rights: Stiebitz remains an axiom; complete universe-polymorphic statement fidelity remains unproved; the static locator is medium confidence. The external repository is Apache-2.0. Current Math profile authority excludes Erdős 750.
- ready for a separate Vela conversion task: No. It is duplicate evidence, its exact Formal Conjectures fidelity is incomplete, and it is outside current Math authority.
- minimal correction if not ready: Type-check an explicit universe-polymorphic bridge using an appropriate lifted vertex type and transported graph/properties, then bind any future packet to the exact declaration under a separately scoped Repository. Do not describe the universe-0 theorem alone as the exact Formal Conjectures result.

### Case 3 — Erdős 56 trust/axiom/licence

- verdict: `needs_correction`
- correctness and scope: The trust disclosure is correct for the exact external declaration, but “statement fidelity unresolved” is too weak: the inspected theorem texts are materially different. The external theorem quantifies eventually over `(N ≥ 2) (k > 0)` and adds `N ≥ k.nth Nat.Prime` as an implication; Formal Conjectures quantifies eventually over `(k > 0) (N ≥ (k-1).nth Nat.Prime)`. The logical orientation is also written oppositely. The external closure therefore must not be presented as evidence that the exact FC declaration is proved.
- exact evidence/build outcome: Clean checkout `plby/lean-proofs@bebe632f2f6227a40e00b145bfbf7b3e1d68f8c2`, tree `7747fa02d3b81f88e6000cd589ff2c1b5e9c5ab2`, built `src/v4.24.0/ErdosProblems/Erdos56.lean` under Lean 4.24.0 / Mathlib `f897ebcf72cd16f89ab4577d0c826cd14afaafc7` (`7351/7351` jobs). `#print axioms Erdos56.erdos_56` returned exactly `propext`, `Classical.choice`, `Lean.ofReduceBool`, `Lean.trustCompiler`, `Quot.sound`; `native_decide` is absent from the target declaration and present in supporting source, confirming the transitive trust dependency.
- novelty or duplication status: Exact duplicate of the retained `erdos-56-native-decide-transitive` build-audit finding. The Docker output adds no new trust fact.
- unresolved assumptions/dependencies/rights: Proof-owner trust policy remains unknown. There is no repository-root licence and no licence in `src/v4.24.0`; licence files exist only in other version subtrees, so reuse/contribution rights for these bytes remain unresolved. Current Math authority excludes Erdős 56.
- ready for a separate Vela conversion task: No. The trust fact is duplicated, the external/FC statements are not exact matches, rights are unresolved, and the case is outside current Math authority.
- minimal correction if not ready: Replace “statement fidelity unresolved” with the explicit declaration mismatch and scope the Result only to the external theorem's trust closure; do not treat it as a proof of the linked FC statement. Preserve the bounded licence warning.

## Aggregate

- proposed-result precision: `2/3 = 66.7%` (`qualified_candidate` among the three producer `proposed_result` outputs)
- valid non-result rate: `1/2 = 50.0%` (`valid_non_result` among the two producer `typed_non_result` outputs)
- invalid outputs: `0/5`
- conversion-ready: `0/5`
- evaluation wall time: 1,921 seconds (32 minutes 1 second) through the final content-validation gate, including clean dependency materialization and four pinned Lean builds
- smallest evidence-backed next step: route no case into a new Vela conversion task. Record this batch as a stop result; if one bounded follow-up is justified later, first close Case 2's explicit universe-transport check under a separately scoped consumer rather than creating a duplicate Math Claim.
