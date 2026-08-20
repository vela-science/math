# Erdős 56 — draft source-owner issue

**Status:** Not sent. User approval is required before creating the issue.

**Destination:** `plby/lean-proofs`

**Frozen candidate:**
[`math-result-candidate-erdos-56-transitive-native-decide-2026-08-20`](../../results/2026-08-20/erdos-56-transitive-native-decide.md)

## Exact draft title

`Erdős 56: clarify native_decide trust and v4.24.0 contribution terms`

## Exact draft body

> At commit `bebe632f2f6227a40e00b145bfbf7b3e1d68f8c2`, a retained
> exact-commit build and axiom reading of `Erdos56.erdos_56` reports
> `Lean.ofReduceBool` and `Lean.trustCompiler` in addition to Mathlib's
> standard three axioms. The dependency is transitive through supporting
> lemmas; `native_decide` is not present in the target theorem declaration
> itself.
>
> Is compiled reduction the intended trust policy for this result, or would
> you welcome a contribution that removes it? I also found no licence file at
> the repository root or in the linked `src/v4.24.0` subtree, although other
> version subtrees do contain licence files. Before preparing a patch, could
> you state the contribution/licence terms for this project?

## Review and evidence gate

- This is a neutral trust disclosure, not an accusation of falsehood or
  concealment and not a universal objection to compiled reduction.
- It makes the precise root/subtree licence observation and does not claim the
  whole repository lacks licence files. No source is copied or patched.
- If issue creation is authorized, retain the issue URL, posting account,
  timestamp, and source head. Record the owner's trust decision,
  contribution/licence terms, or refusal as evidence before preparing code.
  Silence does not satisfy the gate.
- A fresh exact v4.24.0 build, axiom reading, and full declaration-type
  comparison are still required. The current Math authority excludes Erdős
  56; any Vela Decision would need a separately scoped Repository and
  authority.
