# Erdős 750 — draft source-owner issue

**Status:** Not sent. User approval is required before creating the issue.

**Destination:** `Shashi456/erdos-formalizations`

**Frozen candidate:**
[`math-result-candidate-erdos-750-conditional-stiebitz-2026-08-20`](../../results/2026-08-20/erdos-750-conditional-stiebitz.md)

## Exact draft title

`Erdős 750: is a contribution proving stiebitz_lower_bound wanted?`

## Exact draft body

> At commit `286f856aa3fc08957b80950fd18a45aab8d045ea`, a retained
> exact-commit build and axiom reading of `Erdos750.erdos_750_FC` reports Mathlib's
> standard three axioms plus only `Erdos750.stiebitz_lower_bound`.
> Formal Conjectures now marks its link conditional on the corresponding
> Stiebitz statement in merged PR
> [google-deepmind/formal-conjectures#4885](https://github.com/google-deepmind/formal-conjectures/pull/4885).
>
> Would you like an external contribution to formalize
> `stiebitz_lower_bound`? If yes, are the declaration and references currently
> in `Erdos/P750/Proof.lean` the exact specification to target, and which
> toolchain/branch should the contribution use? If not, a short “keep this
> conditional” answer is enough for downstream users.

## Review and evidence gate

- The repository is Apache-2.0. This draft copies no source and names only the
  declaration, commit, and public review locator.
- It treats the current proof as conditional and makes no statement-fidelity
  or unconditional-proof claim.
- If issue creation is authorized, retain the issue URL, posting account,
  timestamp, and source head. Record the owner's yes/no answer, requested
  specification, or refusal as evidence before planning proof work. Silence
  does not satisfy the gate.
- A fresh exact build, axiom reading, and full declaration-type comparison are
  still required. The current Math authority excludes Erdős 750; any Vela
  Decision would need a separately scoped Repository and authority.
