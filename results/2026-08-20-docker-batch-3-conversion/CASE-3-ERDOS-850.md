# Case 3 — Erdős 850 domain wording

## Exact identity and evaluation result

- Problem/declaration: Erdős 850, `Erdos850.erdos_850`.
- Evaluated source:
  `google-deepmind/formal-conjectures@9c4d5821819656af53c5473ded2116ea14a7ff1c`,
  `FormalConjectures/ErdosProblems/850.lean`.
- Source SHA-256:
  `5128fc19d679a8b7f31c9a894c997a66173138192840531b763c4f3df8f06eaa`.
- Current FC `origin/main` `e13dd7284e72012a1616806d09cb6b8025e387af`
  has the same file SHA-256.
- Evaluator verdict: `qualified_candidate`, conversion-ready as a bounded
  source-identity correction. The exact module compiled; direct type/API
  inspection confirmed `x y : ℕ`, `Nat.primeFactors`, and the formal zero
  convention.

## Proven semantic correction

The docstring says “two distinct integers.” The theorem quantifies
`∃ x y : ℕ` and applies `Nat.primeFactors` to `x`, `x+1`, and `x+2`.
Unrestricted integers are not this type, and the exact bytes define no
positive-integer convention or integer prime-factor predicate. In particular,
negative and mixed-sign triples are outside the formal domain, while zero is
inside it with Mathlib's `Nat.primeFactors 0 = ∅` convention.

Thus the prose is strictly broader/ambiguous relative to the exact theorem.
Changing it to “two distinct natural numbers” is the smallest statement-
fidelity correction supported by the bytes.

Classification: documentation/translation bug in FC source, not a theorem
bug, not a proved counterexample, and not category/status metadata.

## Smallest truthful change and owner

Owning repository: `google-deepmind/formal-conjectures`.

Change only the docstring phrase “two distinct integers” to “two distinct
natural numbers.” Do not change the theorem type to integers, invent an
integer prime-factor convention, change `answer(sorry)`, or claim that the
open existence question is resolved.

Formal Conjectures maintainers own editorial intent and source acceptance.
Math Repository authority owns no right to rewrite the source from this
packet and performs no Vela transaction.

## Exact retained evidence and nonclaims

- Producer candidate SHA-256:
  `8f9012ba17621c3802dbba2f2009c9aa59ea2c9a6a721ce1c0d3ea2b02578bf1`.
- Producer receipt SHA-256:
  `aab650440957867c1586b9fc78a2a74129c3a2837c534b26caa14aeeaafdbbb4`.
- Producer commands/output SHA-256:
  `8ccd8249f169d8ecff7c3175522cde7219a76824486c598a5178270f03a0598a`.
- Producer raw-stream SHA-256 retained in the receipt:
  `0bb8f83b752c0fb82e5ae46cded62a5ede5963a0214db390c724f6bd0707e3c5`.

No mathematical source bug, theorem proof, source-owner intent, adoption,
Vela Check, Decision, or Standing change is claimed.

## Required independent Check

On current FC main, confirm the exact theorem still uses naturals and
`Nat.primeFactors`, confirm no local convention redefines “integers,” and
inspect a docstring-only diff. Build/lint the source as required by FC. A
separate semantic reviewer must confirm that changing the theorem domain would
be materially larger and unsupported.

## Falsifiers

- Current source supplies an explicit convention that “integers” here means
  natural/positive integers.
- The theorem no longer quantifies naturals or no longer uses
  `Nat.primeFactors`.
- The cited mathematical source demonstrably intends unrestricted integers,
  making a docstring narrowing unfaithful; that evidence would require a new
  source-owned decision, not assumption here.
- The change touches theorem bytes, answer/category metadata, or scientific
  status.
- A current exact correction duplicate exists.

## Integration gates

1. Refresh source hash and duplicate search.
2. Produce a docstring-only FC diff.
3. Run FC build/lint and independent semantic review.
4. Retain Apache-2.0 attribution.
5. Leave source acceptance to FC maintainers; do not route as a theorem Result.
