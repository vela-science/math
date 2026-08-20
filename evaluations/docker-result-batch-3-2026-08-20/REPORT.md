# Independent evaluation — Docker Result Factory Batch 3

Frozen input: Math commit `082a118ea6ce7c9ca6a62f72aa425373228f7efe`,
tree `480aa298b947b144bdcd9e9574420dcb69b9b486`, parent
`5de716c896065c03c0a470d015ba2a328a527f73`, producer directory
`results/2026-08-20-docker-batch-3/`. All ten assigned cases remain in the
denominator. No producer byte, source repository, Vela record, authority
state, or external system was changed.

Rubric: `qualified_candidate` is a correct, source-backed bounded proposed
result; `needs_correction` has a usable central observation but a material
scope, evidence, or classification defect; `valid_non_result` is a correct
scoped abstention or dependency-only result; `duplicate` is correct but
already covered by an exact prior result; `invalid` has a wrong or unsupported
central conclusion.

## Accounting and common checks

The first parallel Docker launch produced five identical exit-1 setup events,
`No prompt provided via stdin.`, before inference because `docker run -i` was
missing. They are retained as one pre-inference setup incident with five
process exits and zero model attempts. The corrected invocation ran the ten
assigned sessions once each: 10 attempt-1 receipts, zero model retries,
1,290.59 summed producer seconds, and 85 retained shell calls.

All ten input/candidate/tool-call hashes reproduce their receipts, all ten
candidate packets validate against the frozen schema, and all ten FC files reproduce the declared
SHA-256 values. A detached FC worktree at commit/tree
`9c4d5821819656af53c5473ded2116ea14a7ff1c` /
`4ccf4dbcb68d8cc097551213ed13b184f910f110` built the support library
(`8066/8066`) under Lean `4.27.0` and Mathlib
`a3a10db0e9d66acbebf76c5e6a135066525ac900`; each of the ten exact source
modules then exited zero. Their assigned declarations remain `sorry` unless
stated otherwise below. Exact searches found no assigned target in Math parent
or reachable `lean-proofs@852ffa6...`; linked external proofs for the different
Erdős 1136 and 214 main declarations are not duplicates of these variants.

### Case 1 — Erdős 479 domain

- verdict: `qualified_candidate`
- correctness and scope: The prose has `k ≠ 1`, while Lean has `k > 1` over
  `ℕ`; the omitted value is exactly `k = 0`. The formal statement is
  syntactically weaker, but the missing conjunct is true: `n = 2^m` gives
  `n ∣ 2^n`, and the powers are pairwise distinct.
- exact evidence/build outcome: Source SHA-256
  `5c034287066750c318dae057cf5cfc5021cd958d7a948f2cd78daf136c1ac98e`.
  An independent exact Lean theorem proving
  `{n : ℕ | 2^n ≡ 0 [MOD n]}.Infinite` compiled; axioms were exactly
  `propext`, `Classical.choice`, `Quot.sound`. Binder elaboration confirmed
  that the proposed `k ≠ 1` replacement adds precisely this case.
- novelty or duplication status: No exact proof, correction packet, or target
  duplicate was found in the frozen reachable trees.
- unresolved assumptions/dependencies/rights: The `k > 1` research content
  remains open. FC bytes are Apache-2.0; retain source attribution and an
  explicit licence for any independently retained proof bytes.
- ready for a separate Vela conversion task: Yes, as a bounded statement-
  identity correction plus checked `k=0` bridge, not as a proof of Erdős 479.
- minimal correction if not ready: None. State that the two formulations are
  extensionally equivalent only after adjoining the independently checked
  `k=0` lemma.

### Case 2 — Erdős 849 solution count

- verdict: `needs_correction`
- correctness and scope: The proposed no-defect conclusion is correct. For
  fixed `n`, `choose n k` is strictly increasing on `1 ≤ k ≤ n/2`, so each
  projected `n` has at most one admissible `k`; pair count therefore equals
  first-coordinate count. The packet's `statement_correction` status
  contradicts that conclusion.
- exact evidence/build outcome: Source SHA-256
  `0ab7af0a6266830b9527c1a9a1b68ef8ad33a074d2a575c18572766d905ce9de`.
  Independently, the exact strict step
  `2*(k+1) ≤ n → choose n k < choose n (k+1)` compiled from
  `Nat.choose_succ_right_eq` and positivity, with only the three standard
  axioms. Iteration establishes the claimed uniqueness; no target proof was
  claimed or found.
- novelty or duplication status: No duplicate target or prior correction was
  found; the output is a fidelity confirmation, not a new theorem solution.
- unresolved assumptions/dependencies/rights: A full Lean `ncard`/projection
  equivalence term was not retained. FC source is Apache-2.0.
- ready for a separate Vela conversion task: No. There is no source defect or
  scientific target result to route in the current packet.
- minimal correction if not ready: Reclassify `result_status` from
  `statement_correction` to the existing `proof_sketch` status and label the
  result a statement-fidelity confirmation; optionally retain the full
  projection/ncard Lean lemma.

### Case 3 — Erdős 850 integer domain

- verdict: `qualified_candidate`
- correctness and scope: The docstring says unrestricted integers, while the
  theorem quantifies naturals and uses `Nat.primeFactors`, including its
  particular conventions at zero and one. Negative pairs reflect the three
  coordinates, but mixed-sign witnesses and the values around zero are not
  represented; exact bytes supply no positive-integer convention. Changing
  the prose to “natural numbers” is the smallest fidelity correction.
- exact evidence/build outcome: Source SHA-256
  `5128fc19d679a8b7f31c9a894c997a66173138192840531b763c4f3df8f06eaa`;
  exact module compiled and direct type/API inspection confirmed the domain
  and `primeFactors_zero` convention. No theorem proof is claimed.
- novelty or duplication status: No alternate integer formulation, proof, or
  prior packet was found.
- unresolved assumptions/dependencies/rights: Source-owner intent about
  “integers” remains editorial; the correction does not decide the existence
  question. FC source is Apache-2.0.
- ready for a separate Vela conversion task: Yes, as a bounded source-identity
  correction candidate, not as source-owner adoption or a theorem proof.
- minimal correction if not ready: None; retain the convention caveat.

### Case 4 — Erdős 1074 initial EHS numbers

- verdict: `qualified_candidate`
- correctness and scope: The retained computation correctly establishes
  `EHSNumbers ∩ [0,17] = {8,9,13,14,15,16,17}`, hence the first seven
  increasing members. It is a finite computational certificate, not a Lean
  proof of the source declaration.
- exact evidence/build outcome: Source SHA-256
  `72b74c90c3fbdf66fedcd744d6c90da05fdfc7e87673a016787ae4586c705c45`.
  Independent factorization of every `m!+1` for `m=0..17` reproduced every
  retained prime factor, exponent, residue, witness, and exclusion, including
  exact reconstruction of each integer. The member list was exactly
  `[8,9,13,14,15,16,17]`; retained command and stdout hash correctly.
- novelty or duplication status: The exact target has no reachable duplicate;
  the neighboring single-member examples and linked infinitude result do not
  establish this prefix.
- unresolved assumptions/dependencies/rights: No Lean bridge to `Nat.nth` is
  retained, and no checked Lean proof is claimed. FC is Apache-2.0; conversion
  should attach an explicit rights statement to the retained program/output.
- ready for a separate Vela conversion task: Yes, as an exact computational
  prefix certificate with the no-Lean-proof caveat.
- minimal correction if not ready: None. A stronger later artifact may add a
  checked finite-prefix-to-`Nat.nth` bridge, but must not rewrite this packet.

### Case 5 — Erdős 1063 Monier bound

- verdict: `valid_non_result`
- correctness and scope: The dependency reduction is correct. Showing `k!`
  belongs to the defining set with exceptional index zero proves the bound;
  beyond the routine `2*k ≤ k!`, the two substantive obligations are exactly
  nondivisibility by `k!` and divisibility by every `k!-i`, `0<i<k`.
- exact evidence/build outcome: Source SHA-256
  `fc5662ca5de6c05aafd2ad299b1cbab771918474957e6aaf44da523ee23b17f6`;
  exact definition and `Nat.sInf_le` goal shape inspected. Numerical replay
  for `k=3..12` found exceptional set exactly `{0}` each time. No general Lean
  term or duplicate lemma was found.
- novelty or duplication status: A useful exact dependency ledger, not a
  completed result and not a duplicate.
- unresolved assumptions/dependencies/rights: Both general divisibility
  lemmas remain unproved in retained bytes. FC source is Apache-2.0.
- ready for a separate Vela conversion task: No. The target remains a scoped
  non-result.
- minimal correction if not ready: Prove the product identity after cancelling
  `k!` in `choose (k!) k`; each `k!-i` is then a factor, while reduction modulo
  `k!` gives signed `(k-1)!`, which is nonzero for `k≥3`.

### Case 6 — Erdős 1136 multiples of three

- verdict: `qualified_candidate`
- correctness and scope: Both mathematical routes are correct. Multiples of
  three avoid sums equal to powers of two. Their count below `n` is
  `(n+2)/3` (zero plus the positive multiples), whose normalized real limit is
  `1/3`. The producer honestly supplied a proof sketch, not a checked target.
- exact evidence/build outcome: Source SHA-256
  `e9db3914f0a3722670777d3ea9604032e3a37ae15b090488f312e6569b1b9791`.
  An independent exact Lean proof of the avoidance conjunct compiled with
  only standard axioms. `Nat.card_multiples'`, the zero endpoint, the stated
  count formula, and the checked `Nat.hasDensity_even` template were inspected;
  no combined density term was retained or found.
- novelty or duplication status: No exact variant duplicate. The linked
  external Erdős 1136 main proof and the audited `general_upper_bound_infinite`
  declaration are different results.
- unresolved assumptions/dependencies/rights: The set-ncard bridge and
  three-residue/limit proof still need elaboration. FC source is Apache-2.0;
  independently retained proof bytes need explicit licensing.
- ready for a separate Vela conversion task: No. Correct mathematics is not
  yet a complete retained source-native proof artifact.
- minimal correction if not ready: Prove
  `({m | 3 ∣ m} ∩ Iio n).ncard = (n+2)/3`, adapt the three residue cases of
  `Nat.hasDensity_even`, and retain the combined exact target build/axioms.

### Case 7 — Erdős 120 finite set

- verdict: `qualified_candidate`
- correctness and scope: The classical theorem and quantifier diagnosis are
  correct. Negating `Erdos120For A` requires one common affine pair `(a,b)`
  for all points of finite `A`; the difference-set Steinhaus theorem alone
  supplies only pair-dependent witnesses. A density-point plus finite-
  intersection argument supplies the common pair.
- exact evidence/build outcome: Source SHA-256
  `ba3ea6bd91fdf936a6687f386cbfeb7867463035c7250020d4b7b9eb7f6a6450`.
  An independent Lean propositional lemma compiled the exact negation into
  `∀ E, MeasurableSet E → 0 < volume E → ∃ a b, a ≠ 0 ∧ a • A + b ⊆ E`
  (written with the source image), using only standard axioms. Available
  density/Steinhaus APIs do not package the finite common-translation lemma;
  no full proof term was retained.
- novelty or duplication status: No exact target duplicate or packaged bridge
  was found.
- unresolved assumptions/dependencies/rights: The density-point selection,
  common-neighborhood estimates, and finite-intersection lemma remain to be
  formalized. FC source is Apache-2.0.
- ready for a separate Vela conversion task: No. The sketch is mathematically
  qualified but not yet a complete checkable artifact.
- minimal correction if not ready: Prove a reusable finite-homothetic-copy
  lemma for measurable positive-measure subsets of `ℝ`, then close the exact
  negation theorem.

### Case 8 — Erdős 214 bounds bridge

- verdict: `valid_non_result`
- correctness and scope: The conditional bridge is exact. Antitonicity plus
  `HasRedCopies 4` gives nonemptiness/lower bound; antitonicity plus
  `¬HasRedCopies 8` bounds the set by seven, giving the upper bound. It does
  not independently prove the two scientific inputs or antitonicity.
- exact evidence/build outcome: Source SHA-256
  `7b385ee0fc14ea75c391b84abb6981061a707892c216e4dd163bade87dc5dc1e`.
  The generic proposed `sSup` bridge compiled independently with the required
  `BddAbove` and nonempty side conditions and only standard axioms. The source
  `juhasz` and `csizmadia_toth` declarations remain `sorry`; no exact
  antitonicity implementation was found.
- novelty or duplication status: No exact bounds-variant duplicate. The linked
  external main theorem `Erdos214.theorem_2` is a different result.
- unresolved assumptions/dependencies/rights: Needs a source-native proof of
  `Antitone HasRedCopies` and independent proof evidence for the 4- and
  8-point inputs. FC source is Apache-2.0.
- ready for a separate Vela conversion task: No. This is an honest conditional
  dependency result, not a closed target proof.
- minimal correction if not ready: First formalize extension/restriction of
  finite injective configurations to prove antitonicity; then bind independently
  proved `h4` and `h8` rather than importing source `sorryAx` declarations.

### Case 9 — Erdős 251 negative control

- verdict: `valid_non_result`
- correctness and scope: The scoped abstention is correct. Lean's zero-based
  sum is twice the prose's one-based series, subject to summability/reindexing;
  nonzero rational scaling preserves irrationality, so the indexing defect
  does not settle or materially alter the open question.
- exact evidence/build outcome: Source SHA-256
  `d2ab131b7662a7ea25717dc65ca227be0927c63d954c74c5d43680194d633184`;
  exact elaboration is a real tsum, and inspected APIs confirm the zero-based
  prime and rational-scaling facts. No proof or counterexample was found.
- novelty or duplication status: No hidden proof, counterexample, or exact
  duplicate in the frozen trees.
- unresolved assumptions/dependencies/rights: Irrationality and the formal
  convergence/reindexing bridge remain unproved. FC source is Apache-2.0.
- ready for a separate Vela conversion task: No. This is a valid negative
  control.
- minimal correction if not ready: No packet correction; a changing result
  requires exact proof or counterexample evidence.

### Case 10 — Erdős 938 negative control

- verdict: `valid_non_result`
- correctness and scope: The scoped abstention and indexing observation are
  correct. `Nat.Powerful` contains zero and `Nat.nth` is zero-indexed, adding
  one initial formal triple and shifting later triples; a finite prefix change
  cannot change finiteness. `IsAPOfLength 3` prevents collapsed Finsets.
- exact evidence/build outcome: Source SHA-256
  `23d1782dd0600610fbc0597542be2ae2e86bd14eebc43600e4ab2c1342904ed1`;
  exact definitions and AP-cardinality condition inspected. No proof,
  counterexample, or target duplicate was found.
- novelty or duplication status: No hidden result or prior packet.
- unresolved assumptions/dependencies/rights: The finiteness theorem remains
  open in inspected bytes. FC source is Apache-2.0.
- ready for a separate Vela conversion task: No. This is a valid negative
  control.
- minimal correction if not ready: No packet correction; provide an exact
  proof/counterexample or a checked reduction to a known theorem.

## Aggregate

- proposed-result precision: `5/8 = 62.5%` (`qualified_candidate` among the
  eight producer `proposed_result` packets)
- valid-negative rate: `2/2 = 100%` (`valid_non_result` among the two producer
  `typed_non_result` packets)
- verdict counts: 5 qualified, 1 needs correction, 4 valid non-results,
  0 duplicates, 0 invalid
- conversion-ready: `3/10` (Cases 1, 3, and 4)
- setup accounting: one pre-inference setup incident, five process exits,
  zero model attempts; ten assigned model sessions remain the denominator
- independent evaluation wall time: 1,093 seconds (18 minutes 13 seconds)
  through the final content-validation gate
- smallest evidence-backed next step: open a separate computational conversion
  task for Case 4 first, retaining the exact command/stdout/receipts and the
  no-Lean-proof caveat. Queue Cases 1 and 3 as separate statement-identity
  correction tasks. Do not route Cases 6 or 7 until their full source-native
  proofs are retained, and correct Session 2's status before reuse.
