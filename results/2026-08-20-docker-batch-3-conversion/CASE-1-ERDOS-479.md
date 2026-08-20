# Case 1 — Erdős 479 domain correction

## Exact identity and evaluation result

- Problem/declaration: Erdős 479, `Erdos479.erdos_479`.
- Evaluated source:
  `google-deepmind/formal-conjectures@9c4d5821819656af53c5473ded2116ea14a7ff1c`,
  `FormalConjectures/ErdosProblems/479.lean`.
- Source SHA-256:
  `5c034287066750c318dae057cf5cfc5021cd958d7a948f2cd78daf136c1ac98e`.
- Current FC `origin/main` `e13dd7284e72012a1616806d09cb6b8025e387af`
  has the same file SHA-256.
- Evaluator verdict: `qualified_candidate`, conversion-ready because exact
  binder elaboration shows that Lean omits only natural `k = 0`, and an
  independent Lean theorem proving `{n : ℕ | 2^n ≡ 0 [MOD n]}.Infinite`
  compiled under Lean 4.27.0 / Mathlib
  `a3a10db0e9d66acbebf76c5e6a135066525ac900` with only `propext`,
  `Classical.choice`, and `Quot.sound` reported.

## Proven semantic correction

The docstring says `k ≠ 1`; the theorem says `k > 1`. Since `k : ℕ`,

`k ≠ 1 ↔ k = 0 ∨ 1 < k`.

For the omitted case, take `n = 2^m`. The inequality `m ≤ 2^m` gives
`2^m ∣ 2^(2^m)`, so `2^n ≡ 0 [MOD n]`; distinct powers of two give infinitely
many witnesses. Therefore the checked `k = 0` proposition plus the existing
`k > 1` quantification is extensionally equivalent to quantifying `k ≠ 1`.
This proves a statement-translation mismatch and its bridge. It does not prove
any `k > 1` research case.

Classification: translation/formalization bug in the FC theorem statement,
not an error in the cited mathematical problem and not a category/status
metadata issue.

## Smallest truthful change and owner

Owning repository: `google-deepmind/formal-conjectures`.

Change the theorem guard from `∀ᵉ (k > 1),` to `∀ᵉ (k ≠ 1),` and retain a
source-native checked lemma for the `k = 0` infinite set, either adjacent to
the declaration or in the proof realization. Do not alter the answer,
category, or the unresolved `k > 1` content.

Formal Conjectures maintainers own source acceptance. Math Repository
authority could later own a Vela conversion transaction, but this packet
authorizes and performs none.

## Exact retained evidence and nonclaims

- Producer candidate SHA-256:
  `9321f5fb41266e9eacb9d35f3181d0c4adcf772a3fc9060b2aaaf083580d0ec9`.
- Producer receipt SHA-256:
  `a0af792c9dea1aa39e1078091c47aa2d5c120276e7a05bc156b087384518a190`.
- Producer commands/output SHA-256:
  `f49d9393610063ce418f6d7d009096f63245030be46182b4c60ff331a1147c31`.
- Producer raw-stream SHA-256 retained in the receipt:
  `aa106ab743d455c6e4217831139b64ba8d141ebb23f5b1d3d08e02df18e50e77`.
- Evaluator report/verdict paths are bound in `manifest.json`.

The evaluator commit retains the build report but not the exact independent
Lean proof source. Therefore this packet does not pretend to contain those
proof bytes; obtaining or reconstructing and retaining them is an integration
gate.

No theorem proof of Erdős 479, source-owner adoption, Vela Check, independent
Verification, Decision, or Standing change is claimed.

## Required independent Check

On a clean worktree at current FC main, retain the exact `k = 0` Lean source,
build the edited module under the repository-pinned toolchain, run
`#print axioms` on the bridge, compare the declaration before/after, and
confirm the diff changes no `k > 1` content. This Check must be performed by a
task distinct from the source editor; task separation alone must not be
described as independence without the applicable protocol evidence.

## Falsifiers

- The binder does not elaborate to `ℕ`, or `k = 0` is not the only omitted
  case.
- The infinite witness lemma fails on the pinned FC toolchain or relies on
  `sorryAx`, an undeclared axiom, network data, or changed definitions.
- The proposed guard change alters the `k > 1` predicate, answer, or category.
- Current source bytes or target identity no longer match the hashes above.
- A current exact proof/correction duplicate exists.
- Retained proof bytes lack a compatible explicit licence.

## Integration gates

1. Re-run current Math/FC/lean-proofs duplicate and source-hash checks.
2. Retain the exact bridge proof source and explicit licence.
3. Build the exact edited FC module and inspect axioms.
4. Confirm a one-guard source diff plus any adjacent bridge only.
5. Obtain independent source-diff and semantic Check.
6. Leave any later source merge or Vela conversion to the respective owners.
