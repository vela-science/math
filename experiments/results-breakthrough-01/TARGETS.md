# Frozen target slate

All targets use `google-deepmind/formal-conjectures` commit
`e13dd7284e72012a1616806d09cb6b8025e387af`, tree
`7d2b7c17ff144393c2b4a39973ed212387b3e783`. The entire exact file and the
complete read-only source clones are inputs; the snippets below identify the
question rather than replacing source context. Formal Conjectures is
Apache-2.0.

The regenerated frozen duplicate index is
`duplicates/index.json`. Nine targets have no exact declaration occurrence in
Math `5de716c8` or lean-proofs `accf62cb`; this is only a statement about that
frozen universe. T02 is the deliberate exception: Math contains three exact
occurrence/provenance metadata matches, described below. Across the assigned FC
bytes, target declarations remain `sorry`, `stop`, definitions needing semantic
comparison, or deliberately checked dependency bridges exactly as described.
A source drift or newly reachable proof before launch invalidates the freeze;
it is not silently ignored or substituted.

## Smoke targets

The two-target smoke is T01 and T02, across all three arms. They test a finite
graph proof and a small exact-number proof with different APIs. The remaining
eight targets are not assigned until smoke information-equivalence, isolation,
credential, lifecycle, and receipt gates pass.

## Proof opportunities (4)

### T01 — Erdős 23 finite graph case

- Target: `Erdos23.erdos_23.variants.n1`.
- File: `FormalConjectures/ErdosProblems/23.lean`.
- Git blob: `346d29667313a32382bbf42b87588d53bb208400`.
- File SHA-256:
  `a40f99ea631aaa62c270793f6354e138ca4456c6a09b24d4d3c7b9d39bb169da`.
- Exact objective: prove, counterexample, or precisely fail to resolve the
  statement that every triangle-free `SimpleGraph (Fin 5)` has a bipartite
  subgraph obtained by deleting at most one edge. A computational enumeration
  is a certificate, not a Lean theorem, until the exact declaration builds.

### T02 — Erdős 138, `W(2)=3`

- Target: `Erdos138.monoAPNumber_two_two`.
- File: `FormalConjectures/ErdosProblems/138.lean`.
- Git blob: `061c7b62abe53b0db18a3d795b8e71ea4efc70c0`.
- File SHA-256:
  `c65c7f26e09baefa0b0f640c3e37b6d173a05c4b173a3a5685c6bcb547037298`.
- Exact objective: independently realize a checked source-native proof of
  `W 2 = 3` from the current definitions, retaining the lower and upper
  directions and exact `sInf`/nonempty dependencies. Frozen Math already has
  occurrence/provenance metadata pointing to
  `XC0R/formal-conjectures@6c7a16e...`, but records build `not_attempted` and
  axiom status `not_read`; those external proof bytes are not in the mounted
  inputs. T02 may qualify only as explicitly allowed independent proof
  production. It must not claim theorem novelty, treat the URL as proof bytes,
  or infer that the linked proof builds.

### T03 — Erdős 359 finite prefix

- Target: `Erdos359.erdos_359.variants.isGoodFor_1_low_values`.
- File: `FormalConjectures/ErdosProblems/359.lean`.
- Git blob: `62635546c38f181610242b83e1e5d5ca86b5d64a`.
- File SHA-256:
  `184ece2c4fb5e0d29e72210c9d75573b93ba3ccc4b559619e1f3b4319ea20f61`.
- Exact objective: derive the image prefix
  `{1,2,4,5,8,10,14,15}` from `IsGoodFor A 1`, including the leastness and
  consecutive-sum exclusions, or retain an exact typed non-result.

### T04 — Erdős 1052 optimized checked computation

- Target: `Erdos1052.isUnitaryPerfect_87360`.
- File: `FormalConjectures/ErdosProblems/1052.lean`.
- Git blob: `7cad758989e63bf21308e2738e2a1b2bd1730d70`.
- File SHA-256:
  `1be8d7df96b8c3fa3ce6bc0c341ed62a023850a04e889fd5c9d8d91baacfcffe`.
- Exact objective: replace the current deliberate `stop` with the smallest
  source-native checked proof of `IsUnitaryPerfect 87360`, or produce a
  retained certificate/typed performance non-result. Compilation time and
  trust closure are part of the result.

## Statement/status corrections (2)

### T05 — Erdős 1062 positive-integer domain

- Target: `Erdos1062.ForkFree` and its use by `Erdos1062.f`.
- File: `FormalConjectures/ErdosProblems/1062.lean`.
- Git blob: `3f7ccf1a845ef966b2dfbcb11918f88308c336bb`.
- File SHA-256:
  `ee47c66fe29bcdd5e6bde2d8c325fcf8a511f5a147f8cef8c1065cd28716fae3`.
- Exact objective: compare the docstring's “set of positive integers” with
  `ForkFree (A : Set Nat)`, which does not itself exclude zero, and with `f`,
  which restricts witnesses to `Set.Icc 1 n`. Decide whether the truthful
  smallest change is documentation, a definition correction, or no change;
  prove every claimed semantic equivalence and identify downstream breakage.

### T06 — Erdős 170 zero measurement in a perfect ruler

- Target: `Erdos170.PerfectRuler`.
- File: `FormalConjectures/ErdosProblems/170.lean`.
- Git blob: `9fe34ed7ac92dc442947488f6651325b4b0019c8`.
- File SHA-256:
  `cb0e87eedb7818b9639ee2d7875f0083d90e7fb0fe5fdaa357db26aff038b7d1`.
- Exact objective: compare “each positive integer `k <= N`” with iteration over
  `Finset.range (N + 1)`, which includes zero. Determine exactly whether the
  zero clause is redundant for the intended downstream domain or changes edge
  cases such as `N=0`/empty rulers, and classify source bug, harmless
  strengthening, documentation issue, or no correction.

## Dependency/trust cases (2)

### T07 — Erdős 835 checked bridge versus unresolved premise

- Target:
  `Erdos835.johnsonGraph_chromaticNumber_odd_of_johnson_chromaticNumber_composite`.
- File: `FormalConjectures/ErdosProblems/835.lean`.
- Git blob: `948ac76c6dacca85e312edfb8d550d9b5f8d768f`.
- File SHA-256:
  `f163f1f5a6fead133f3a66ae400305fcb40c6019321ce21e869ce5b3c0ab89a0`.
- Exact objective: state what the checked implication establishes and what it
  does not while `johnson_chromaticNumber_composite` remains `sorry`; inspect
  the exact proof/dependency closure and, only if possible within the target,
  discharge or narrow the load-bearing dependency.

### T08 — Erdős 1145 implication to Erdős 28

- Target: `Erdos1145.erdos_1145.test_implies_erdos_28`.
- File: `FormalConjectures/ErdosProblems/1145.lean`.
- Git blob: `3cf6a2edb12df28c2baa374b8e43968abff88c4f`.
- File SHA-256:
  `e81c389c422b834b681eff228fac5b988ca994e5334465312d22fa341a48843c`.
- Exact objective: validate the checked implication and its imported target,
  identify the inclusion-of-zero convention, and distinguish a proved
  dependency bridge from a proof of either open conjecture. Any status or
  identity correction must follow exact source semantics.

## Negative controls (2)

### T09 — Erdős 14 unique-sum lower bound

- Target: `Erdos14.erdos_14.parts.i`.
- File: `FormalConjectures/ErdosProblems/14.lean`.
- Git blob: `52016d0053f4656cca69c135f4e95ef1449d63f6`.
- File SHA-256:
  `63e02a65ab619a881bcbec9319e71a61fc26bf8bdb9be069c85149bfcfc0cf4c`.
- Exact objective: search the assigned complete sources for a checked proof,
  counterexample, exact correction, or dependency discharge. Otherwise return
  a scoped typed non-result without treating source absence as mathematical
  openness or impossibility.

### T10 — Erdős 208 squarefree gaps

- Target: `Erdos208.erdos_208.parts.i`.
- File: `FormalConjectures/ErdosProblems/208.lean`.
- Git blob: `85ab18f2f5630262d98a244621e82c552ab087b9`.
- File SHA-256:
  `844f59de94e694b845de4f3e919fae009927517f49f2fe260163d10054d9dca9`.
- Exact objective: search the assigned complete sources for a checked proof,
  counterexample, exact correction, or dependency discharge. Otherwise return
  a scoped typed non-result; do not infer truth or current literature status
  from the mounted corpus alone.

## Prior Result Factory exclusions

The following assigned cases are excluded from scoring and may appear only in
duplicate-search context:

- Batch 1: Erdős 321, 750, 56, 94, 887.
- Batch 2: Erdős 697 delta bound, 822, 1, 291, 399, 945, 318, 697 threshold
  identity, 683/961 identity, 260.
- Batch 3: Erdős 479, 849, 850, 1074, 1063, 1136, 120, 214, 251, 938.

No target substitution is permitted after this freeze.
