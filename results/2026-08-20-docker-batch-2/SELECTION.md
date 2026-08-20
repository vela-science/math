# Batch 2 lightweight source check

This is a selection correction based on independent evaluation commit
`5835fd03a9d623cf64a9c04a94a5d708d2a80726`. It authorizes no Vela mutation.

Exact sources checked before any model call:

- Math base and current `origin/main`:
  `5de716c896065c03c0a470d015ba2a328a527f73`.
- Formal Conjectures current `origin/main`:
  `9c4d5821819656af53c5473ded2116ea14a7ff1c`, tree
  `4ccf4dbcb68d8cc097551213ed13b184f910f110`.
- Reachable Lean source used for duplicate search: `williamjblair/lean-proofs`
  current `origin/main` `852ffa6b50f3501a66d7ffbc116d8ae9b749c60c`.
- Current accepted Math problems are 94, 321, and 887. All are excluded.
- Batch 1 problems 56, 94, 321, 750, and 887 are excluded.
- Exact selector search in this Math tree found no prior packet for any target
  below. Each selected target is still a `sorry` in the exact FC source and
  has no target-level `formal_proof` attribute.

| # | Class | Exact target | Source SHA-256 | Up-front comparison and related-byte rule |
|---|---|---|---|---|
| 1 | conditional/dependency | `Erdos697.erdos_697.variants.delta_lt` | `52bd695b7cf25cdf02972e50c53b0b3f6290a681d7aa1f58fdcd7618cde9e10a` | Exact theorem quantifies all `m : ℕ`; compare the `m = 0` specialization with real division before attempting proof. Entire `697.lean` is required. |
| 2 | negative control | `Erdos822.erdos_822` | `0ee0e9ac7f08f6de4ed165f8b6f18ffcadee0021d7170d6a8e0f9d296609b94a` | Exact target has only a paper citation and explicitly says the library interface is absent. Search all exact reachable sources before abstaining. |
| 3 | proof/search | `Erdos1.erdos_1.variants.least_N_5` | `6754c87ff3e02086075f6911afbe771875ae1967f15c41f1f8882fe207da6cf0` | Compare with the proved `least_N_3` pattern and include all of `1.lean`; do not reuse the `N = 3` result as the target proof. |
| 4 | proof/search | `Erdos291.erdos_291.parts.ii` | `f2cbf68a5592d5ba6f2e265fa9e53743b709e510cf02638142134534b004e648` | Target is infinitude of `gcd (a n) (L n) > 1`; the same file's generalization and evaluation lemmas are required. |
| 5 | proof/search | `Erdos399.erdos_399.variants.cambie` | `79c50670ecacbd211abb8211814729c8e3aacc5c7055f3790842e381e53f36be` | Target is the coprime fourth-power sum exclusion, not the already closed main counterexample. Entire `399.lean` is required. |
| 6 | proof/search | `Erdos945.erdos_945.variants.equivalence` | `7caf8d1ea9efca08a6ec421c7fb4526f4ad626feb08775d9b6e8c56fa6d3cf41` | Compare the exact definitions `Erdos945Prop` and `Erdos945Constant` before proposing either direction. Entire `945.lean` is required. |
| 7 | conditional/dependency | `Erdos318.erdos_318.parts.i` | `a4b903ccdada7879aedb81a9b02c435cc0a45cdcfbbcefb9fbd74b9db4ad5177` | Explicitly bind any result to `contain_single_even`; also check that the proposed witness really has `HasPosDensity`. Entire `318.lean` is required. |
| 8 | source-status/identity | `Erdos697.erdos_697.parts.i` and `.parts.ii` | `52bd695b7cf25cdf02972e50c53b0b3f6290a681d7aa1f58fdcd7618cde9e10a` | Compare each prose inequality and limit with the exact Lean hypothesis; answer only the byte-level swap/correction question. |
| 9 | source-status/identity | `Erdos683.erdos_683` versus `Erdos961.erdos_961` | `0b143cd140a099a504577866c493966df2eccd94cbaa1b7ce2d79d260fb017b7` / `667451a3842127bc52225a47cee1d13122fac01886c8f5dcff7ffe820e098e19` | Both complete files are required. Do not promote the TODO assertion of equivalence without an exact mathematical map in both directions. |
| 10 | negative control | `Erdos260.erdos_260` | `eeaeb6e213873ec1af670edaca0e422e76f5a98026f78e4006f5efa6f66f13f7` | Include the two explicitly named stronger-assumption directions and search reachable sources; absence must be scoped to inspected bytes. |

The slate is exactly four proof/search opportunities, two dependency questions,
two source-identity questions, and two negative controls. Decisive missing facts
do not require source-owner outreach. All ten assigned cases remain in the
denominator even if a session fails or abstains.

