# Independent evaluation — Docker Result Factory Batch 2

Frozen input: Math commit `badf9efb9723561d096defbfb7a4567c38fdeb24`, tree `29979ae495d46a9a7e91335078c75e49f397d040`, parent `5de716c896065c03c0a470d015ba2a328a527f73`, producer directory `results/2026-08-20-docker-batch-2/`. All ten assigned cases remain in the denominator. No producer byte, source repository, Vela record, authority state, or external system was changed.

Rubric: `qualified_candidate` means the proposed bounded result is correct and source-backed; `needs_correction` means the central observation is usable but a material scope or evidence statement must be corrected; `valid_non_result` means abstention is correct and well scoped; `invalid` means the central conclusion is wrong or unsupported.

## Disposition

Cases 1, 5, and 8 are ready for separate, non-authoritative Vela conversion tasks. Case 5 is the strongest first route because the exact theorem was independently kernel-checked without `sorryAx`. Case 6 is mathematically qualified but not conversion-ready until its asymptotic and endpoint sketch is retained as a complete checkable argument. Case 3 is mathematically correct, but its producer packet calls an unretained external run an “exact finite certificate.” Cases 2, 4, 7, and 10 are valid non-results. Case 9 needs a packet correction because `proposed_result` is blank.

### Case 1 — Erdős 697 delta bound

- verdict: `qualified_candidate`
- correctness and scope: Correctly falsifies the exact universal theorem at `m = 0`. In `Nat.ModEq` modulo zero, `d ≡ 1 [MOD 0]` reduces to `d = 1`, contradicting the required `1 < d`; the density set is empty, `δ 0 α = 0`, and Lean's real division by zero makes the right side zero. Adding `m ≠ 0` (equivalently `0 < m`) removes this counterexample but does not prove the repaired analytic inequality.
- exact evidence/build outcome: Formal Conjectures commit/tree `9c4d5821819656af53c5473ded2116ea14a7ff1c` / `4ccf4dbcb68d8cc097551213ed13b184f910f110`, source SHA-256 `52bd695b7cf25cdf02972e50c53b0b3f6290a681d7aa1f58fdcd7618cde9e10a`; Lean 4.27.0 / Mathlib `a3a10db0e9d66acbebf76c5e6a135066525ac900`. The exact source module compiled, and an independent scratch theorem proving `δ 0 α = 0` and the false specialization compiled. Its axioms are `propext`, `sorryAx`, `Classical.choice`, `Quot.sound`; `sorryAx` is inherited from the source's `density_exists`, whose chosen witness defines `δ`.
- novelty or duplication status: No covering proof or prior packet was found in Math parent `5de716c...` or reachable `lean-proofs@852ffa6...`; only the exact FC declaration was found.
- unresolved assumptions/dependencies/rights: The counterexample follows the source's own `density_exists` declaration, which remains `sorry`; the repaired `m ≠ 0` bound is unproved. FC source is Apache-2.0; retain source attribution and the inherited-axiom disclosure.
- ready for a separate Vela conversion task: Yes, as a bounded source-statement counterexample/correction candidate, not as a proof of the repaired bound and not as acceptance.
- minimal correction if not ready: None for routing. The conversion must preserve the `sorryAx` dependency and state only that `m ≠ 0` removes the exhibited contradiction.

### Case 2 — Erdős 822 negative control

- verdict: `valid_non_result`
- correctness and scope: Correctly abstains for the exact positive-density target and bounds absence to the two pinned source trees and Math audit bytes. The GIL24 citation and TODO are not proof-bearing Lean declarations.
- exact evidence/build outcome: Exact source SHA-256 `0ee0e9ac7f08f6de4ed165f8b6f18ffcadee0021d7170d6a8e0f9d296609b94a`; complete source inspection found only the target `sorry` and the explicit missing-library-interface TODO. Exact searches of FC and `lean-proofs@852ffa6...` found no theorem giving positive density to `range (fun n => n + Nat.totient n)`. No candidate proof existed to build.
- novelty or duplication status: No hidden proof/witness evidence or prior Math packet was found.
- unresolved assumptions/dependencies/rights: A formal GIL24 interface or an exact `HasPosDensity` theorem is missing. FC source is Apache-2.0; the paper's mathematical rights and correctness were not evaluated.
- ready for a separate Vela conversion task: No. This is a valid abstention, not a scientific Result candidate.
- minimal correction if not ready: No packet correction. The smallest changing evidence is a kernel-checked exact positive-density theorem.

### Case 3 — Erdős 1 least `N = 5`

- verdict: `needs_correction`
- correctness and scope: The mathematical result is correct: `{3,6,11,12,13}` has 32 distinct subset sums, and no five-subset of `{1,...,12}` is sum-distinct. The producer overstates its retained evidence as an “exact finite certificate.”
- exact evidence/build outcome: Exact source SHA-256 `6754c87ff3e02086075f6911afbe771875ae1967f15c41f1f8882fe207da6cf0`. Independent enumeration checked all `C(12,5)=792` candidates with zero successes and all `C(13,5)=1287` candidates with exactly two successes, `{3,6,11,12,13}` and `{6,9,11,12,13}`. An independent exact Lean theorem compiled using a finite `native_decide` certificate; axioms are `propext`, `Classical.choice`, `Lean.ofReduceBool`, `Lean.trustCompiler`, `Quot.sound`. The producer artifacts retain the enumeration source and exit code in `tool-calls.json`, but not stdout, a certificate artifact, or a checked Lean term.
- novelty or duplication status: No covering proof or prior packet was found in the exact Math/FC/lean-proofs sources.
- unresolved assumptions/dependencies/rights: The producer's computation is not replayable from retained output alone; a `native_decide` route adds compiler trust and must disclose it. FC source is Apache-2.0; a retained proof/certificate needs an explicit compatible licence and attribution.
- ready for a separate Vela conversion task: No. The output's claimed certificate is absent from the producer packet even though the result independently checks.
- minimal correction if not ready: Retain and build the exact Lean theorem (or retain deterministic program, stdout, digest, and a checked bridge to the theorem) and disclose `Lean.trustCompiler`/`Lean.ofReduceBool` if using `native_decide`.

### Case 4 — Erdős 291 infinite gcd

- verdict: `valid_non_result`
- correctness and scope: Correctly keeps the family `n_r = 2 * 3^(r+1)` conditional. Under the exact `steinerberger_generalization`, its leading base-3 digit is 2, the rational sum is `3/2`, and 3 divides the gcd; injectivity then gives infinitude. The generalization itself remains `sorry`, so this is not an unconditional target proof.
- exact evidence/build outcome: Exact source SHA-256 `f2cbf68a5592d5ba6f2e265fa9e53743b709e510cf02638142134534b004e648`; the target and dependency were compared exactly, including the necessary exponent start that avoids `n=2` and `n=4`. No closed specialized lemma or duplicate proof was found; no unconditional term existed to build.
- novelty or duplication status: No covering proof or prior packet was found; the family is an explicit instantiation of source prose/dependency, not an independent unconditional result.
- unresolved assumptions/dependencies/rights: Essential dependency is `steinerberger_generalization` or the specialized 3-adic lemma. FC source is Apache-2.0.
- ready for a separate Vela conversion task: No. The assigned theorem remains a non-result until the specialized divisibility lemma is proved without the source `sorry`.
- minimal correction if not ready: No correction to the abstention. Prove `∀ r, 3 ∣ gcd (a (2*3^(r+1))) (L (2*3^(r+1)))` directly.

### Case 5 — Erdős 399 Cambie variant

- verdict: `qualified_candidate`
- correctness and scope: Correct for the exact coprime plus-sign fourth-power target. The residue identity `z^4 % 8 = z % 2` covers all eight residues. For `n ≥ 4`, divisibility by 8 forces both variables even, contradicting coprimality; `n=3` has residue 6 versus a sum in `{0,1,2}`; `n=0,1,2` are excluded using `1 < x*y` and the exact factorial values.
- exact evidence/build outcome: Exact source SHA-256 `79c50670ecacbd211abb8211814729c8e3aacc5c7055f3790842e381e53f36be`. Under Lean 4.27.0 / Mathlib `a3a10db...`, an independent theorem with the exact target type compiled through every small and general case. `#print axioms` returned exactly `propext`, `Classical.choice`, `Quot.sound`; no `sorryAx`, `Lean.trustCompiler`, or extra mathematical axiom appears.
- novelty or duplication status: No exact duplicate was found in Math parent, FC beyond the `sorry`, or `lean-proofs@852ffa6...`. The closed main counterexample is a different minus-sign, non-coprime result.
- unresolved assumptions/dependencies/rights: No mathematical dependency remains. FC is Apache-2.0; a conversion task should retain an independently authored/licensed proof artifact and exact occurrence binding.
- ready for a separate Vela conversion task: Yes. It is the strongest conversion candidate in the batch: exact theorem fidelity, deterministic build, standard axioms, no duplicate.
- minimal correction if not ready: None for routing; conversion still must retain the proof bytes, toolchain roots, occurrence binding, and non-acceptance caveats.

### Case 6 — Erdős 945 equivalence

- verdict: `qualified_candidate`
- correctness and scope: The two mathematical directions are sound for the exact definitions. Forward, a long collision-free closed interval yields an injective `Ioc` block via `n = ceil(x)-1`, and bounded `O` cannot dominate a higher fixed log power. Reverse, applying the collision property at `n+1` bounds blocks beginning beyond the threshold; one fixed interval bounds all earlier starts. This accounts for the excluded `n`/included `n+k` endpoint and for the closed real interval. It does not supply a complete Lean proof.
- exact evidence/build outcome: Exact source SHA-256 `7caf8d1ea9efca08a6ec421c7fb4526f4ad626feb08775d9b6e8c56fa6d3cf41`; the module compiled under the pinned toolchain with the equivalence and four other source declarations still warning on `sorry`. Independent definition-level inspection confirmed `F` uses `sSup` of `Ioc` blocks, `O =O 1` gives an eventual absolute exponent bound, and `Erdos945Constant` uses two naturals in a closed real interval. No complete asymptotic inequality chain or Lean term was retained or built.
- novelty or duplication status: No covering proof or prior packet was found in the exact source trees.
- unresolved assumptions/dependencies/rights: Formal details remain for `sSup` bounds, ceil/floor rounding, eventual positivity/monotonicity of real powers, and `log(x + log(x)^C) ~ log x`. FC is Apache-2.0.
- ready for a separate Vela conversion task: No. Correctness is credible, but the retained evidence is still a proof sketch rather than a complete checkable argument.
- minimal correction if not ready: Retain a complete proof with explicit thresholds and rounding inequalities in both directions, preferably as a pinned Lean build or a fully checkable mathematical artifact.

### Case 7 — Erdős 318 positive density

- verdict: `valid_non_result`
- correctness and scope: Correctly presents `Odd ∪ {0}` only as a conditional witness. It has exactly one even member, but both `contain_single_even` and the needed exact density/finite-perturbation bridge are unproved in the inspected bytes.
- exact evidence/build outcome: Exact source SHA-256 `a4b903ccdada7879aedb81a9b02c435cc0a45cdcfbbcefb9fbd74b9db4ad5177`; complete inspection confirmed both relevant declarations are `sorry`. The density API contains `Nat.hasDensity_even` and finite-set density zero but no directly usable odd-complement/finite-perturbation theorem. No closed target term existed to build.
- novelty or duplication status: No covering proof or prior packet was found.
- unresolved assumptions/dependencies/rights: `contain_single_even` and exact density `1/2` for the proposed union remain essential. FC source is Apache-2.0.
- ready for a separate Vela conversion task: No. The output is a valid conditional abstention.
- minimal correction if not ready: No correction to the packet. Close both named dependencies before routing a target Result.

### Case 8 — Erdős 697 threshold identity

- verdict: `qualified_candidate`
- correctness and scope: Exact byte-level swap confirmed. The prose for part i says `α < 1/log 2` with limit 0, while Lean has `1/log 2 < α`; the prose for part ii says `1/log 2 < α` with limit 1, while Lean has `α < 1/log 2`. Swapping only the two hypotheses restores prose/Lean fidelity without changing either conclusion.
- exact evidence/build outcome: Complete exact source SHA-256 `52bd695b...e10a`; lines 51–60 were compared directly. Repository-wide exact searches found no alternative formulation that changes the threshold pairing. This is a byte comparison, so no proof build is relevant.
- novelty or duplication status: No prior packet or duplicate corrected formulation was found.
- unresolved assumptions/dependencies/rights: This establishes a source identity defect, not either analytic limit. FC source is Apache-2.0; source owners retain editorial authority.
- ready for a separate Vela conversion task: Yes, as a bounded statement-identity/correction candidate with no claim of theorem truth or source-owner adoption.
- minimal correction if not ready: None for routing. Preserve the exact bytes, source-owner boundary, and the fact that no limit theorem was proved.

### Case 9 — Erdős 683/961 identity

- verdict: `needs_correction`
- correctness and scope: The substantive abstention is correct: the source contains only a TODO equivalence assertion, and the direct interval/binomial bridge yields a fixed-power scale rather than the polylogarithmic bound in Erdős 961. No two-direction exact map was found. However, the schema-valid packet leaves `proposed_result` as the empty string, so it does not actually state its non-result in the designated field.
- exact evidence/build outcome: Exact hashes `0b143cd140a099a504577866c493966df2eccd94cbaa1b7ce2d79d260fb017b7` and `667451a3842127bc52225a47cee1d13122fac01886c8f5dcff7ffe820e098e19` matched. Complete source and reachable-tree searches found no proof beyond the TODO. The packet's `result_type` is `typed_non_result`, but `proposed_result` has byte length zero.
- novelty or duplication status: No equivalence proof or prior packet was found; the only duplicate assertion is the unproved source TODO.
- unresolved assumptions/dependencies/rights: A quantitative upgrade, rounding/range conditions, the reverse map, and the small-start branch remain unresolved. FC source is Apache-2.0.
- ready for a separate Vela conversion task: No. A blank result field is not a convertable scientific assertion, even when supporting evidence is informative.
- minimal correction if not ready: Populate `proposed_result` with the bounded non-result already supported by the packet, without claiming the TODO is false or globally unproved.

### Case 10 — Erdős 260 negative control

- verdict: `valid_non_result`
- correctness and scope: Correctly finds no proof, refutation, or proof-bearing bounded lemma in the exact reachable bytes. The two stronger growth directions are comments, not Lean propositions or dependencies.
- exact evidence/build outcome: Exact source SHA-256 `eeaeb6e213873ec1af670edaca0e422e76f5a98026f78e4006f5efa6f66f13f7`; complete source inspection and exact searches found only the target `sorry` and two TODO comments. Under the repository's default answer elaboration, the target requires the full universal irrationality assertion. No candidate term existed to build.
- novelty or duplication status: No hidden proof, counterexample, relevant formalized stronger variant, or prior packet was found.
- unresolved assumptions/dependencies/rights: The open universal irrationality theorem and both informal stronger variants remain unresolved. FC source is Apache-2.0.
- ready for a separate Vela conversion task: No. This is a valid negative control.
- minimal correction if not ready: No packet correction. A changing result requires an exact proof, counterexample, or formally stated and proved stronger variant.

## Aggregate

- proposed-result precision: `4/5 = 80.0%` (`qualified_candidate` among five producer `proposed_result` outputs)
- valid non-result rate: `4/5 = 80.0%` (`valid_non_result` among five producer `typed_non_result` outputs)
- invalid outputs: `0/10`
- conversion-ready: `3/10` (Cases 1, 5, and 8)
- evaluation wall time: 1,522 seconds (25 minutes 22 seconds) through the final content-validation gate, including exact dependency materialization, four pinned source-module compiles, three independent scratch theorem checks, source inspection, and duplicate search
- smallest evidence-backed next step: open one separate conversion task for Case 5 first, retaining the exact Lean proof and pinned roots. Queue Cases 1 and 8 as separate source-correction candidates; do not route Cases 3 or 6 until their proof evidence is retained, and repair Case 9's blank result field before any reuse.
