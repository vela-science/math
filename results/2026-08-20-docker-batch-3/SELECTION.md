# Batch 3 frozen source check

This slate was frozen before inference.

Exact execution and source identities:

- Math base/current `origin/main`:
  `5de716c896065c03c0a470d015ba2a328a527f73`.
- Formal Conjectures `origin/main`:
  `9c4d5821819656af53c5473ded2116ea14a7ff1c`, tree
  `4ccf4dbcb68d8cc097551213ed13b184f910f110`.
- Reachable `lean-proofs` `origin/main`:
  `852ffa6b50f3501a66d7ffbc116d8ae9b749c60c`.
- Docker context: `desktop-linux`.
- Image:
  `vela-math-result-candidate@sha256:c290b6490fb78c3702694b311fe9f07bd03002d7c1c979b3e5723d6b9f579e01`.
- Candidate runner: Codex CLI 0.145.0 using the existing read-only OAuth file.

The exact target names below were searched in current Math and the reachable
`lean-proofs` tree and were absent. Each target remains `sorry` in the exact FC
file. Problems used in Batches 1 and 2 are excluded.

| # | Class | Exact target | FC file SHA-256 | Up-front comparison |
|---|---|---|---|---|
| 1 | statement correction | `Erdos479.erdos_479` | `5c034287066750c318dae057cf5cfc5021cd958d7a948f2cd78daf136c1ac98e` | Prose quantifies `k ≠ 1`; Lean quantifies only `k > 1`. Determine the exact omitted domain and whether it changes content. |
| 2 | statement correction | `Erdos849.erdos_849` | `0ab7af0a6266830b9527c1a9a1b68ef8ad33a074d2a575c18572766d905ce9de` | Prose says the equation has exactly `t` solutions; Lean takes `ncard` of `n` values and existentially hides `k`. Compare pair-count and first-coordinate count. |
| 3 | statement correction | `Erdos850.erdos_850` | `5128fc19d679a8b7f31c9a894c997a66173138192840531b763c4f3df8f06eaa` | Prose says integers; Lean uses naturals and `Nat.primeFactors`. Determine whether this is a real domain loss or conventional wording. |
| 4 | computational/proof | `Erdos1074.erdos_1074.variants.EHSNumbers_init` | `72b74c90c3fbdf66fedcd744d6c90da05fdfc7e87673a016787ae4586c705c45` | Entire file is required, including definitions and already checked single-member examples. Any enumeration claim needs exact retained stdout/certificate evidence. |
| 5 | proof opportunity | `Erdos1063.erdos_1063.variants.monier_upper_bound` | `fc5662ca5de6c05aafd2ad299b1cbab771918474957e6aaf44da523ee23b17f6` | Entire file is required, including `n`, `exists_exception`, and checked `small_values`; do not claim those neighboring results as the target proof. |
| 6 | proof opportunity | `Erdos1136.erdos_1136.variants.multiples_of_three` | `e9db3914f0a3722670777d3ea9604032e3a37ae15b090488f312e6569b1b9791` | Separate the elementary avoidance argument from the density-of-multiples dependency and inspect exact available APIs before proposing Lean. |
| 7 | proof opportunity | `Erdos120.erdos_120.variants.finite_set` | `ba3ea6bd91fdf936a6687f386cbfeb7867463035c7250020d4b7b9eb7f6a6450` | Compare the formal negation of `Erdos120For` with the cited finite-set claim; distinguish a measure-theoretic route from a checked proof. |
| 8 | dependency bridge | `Erdos214.erdos_214.variants.bounds` | `7b385ee0fc14ea75c391b84abb6981061a707892c216e4dd163bade87dc5dc1e` | Entire file is required. Determine exactly which neighboring `sorry` declarations imply `4 ≤ k ∧ k ≤ 7`, and whether the bridge itself can be proved without importing their truth silently. |
| 9 | negative control | `Erdos251.erdos_251` | `d2ab131b7662a7ea25717dc65ca227be0927c63d954c74c5d43680194d633184` | Search exact reachable sources for a proof or counterexample; scope absence to inspected bytes and check indexing/coercions before abstaining. |
| 10 | negative control | `Erdos938.erdos_938` | `23d1782dd0600610fbc0597542be2ae2e86bd14eebc43600e4ab2c1342904ed1` | Search exact reachable sources and compare the prose's consecutive powerful-number triple with the exact `Finset`/`nth` statement before abstaining. |

All ten cases remain in the denominator regardless of outcome.
