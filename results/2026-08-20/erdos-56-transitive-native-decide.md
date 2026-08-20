# `math-result-candidate-erdos-56-transitive-native-decide-2026-08-20`

## Bounded assertion

At exact commits
`google-deepmind/formal-conjectures@9f5ee773841921f460b4a26a3552f5eca4accaa0`
and `plby/lean-proofs@bebe632f2f6227a40e00b145bfbf7b3e1d68f8c2`,
the linked declaration `Erdos56.erdos_56` builds and its recorded axiom closure
is exactly:

```text
propext
Classical.choice
Lean.ofReduceBool
Lean.trustCompiler
Quot.sound
```

The target has zero propositional binders. The compiled-reduction dependency
is transitive: `native_decide` does not occur in the target declaration's own
text, although supporting lemmas in the file use it. A declaration-only text
scan therefore misses a trust dependency that `#print axioms` exposes.

This is a trust-disclosure Result about exact proof bytes. It does not assert
that the theorem is false, that the proof owner concealed the dependency, or
that compiled reduction is never an acceptable verification policy.

## Observable facts available to every comparison condition

The numbered list is a quick summary. Every condition receives this entire
public packet, including the evidence and uncertainty, required Check and
authority, upstream message, and next action below.

1. The two exact upstream heads, files, and declaration names above.
2. The exact checkout built and the five-name axiom closure above was read.
3. The target has zero propositional binders.
4. `native_decide` is absent from the target theorem's own text and present in
   supporting lemmas, so the trust dependency is transitive.
5. The target locator confidence is `high`, by file and declaration name.
6. There is no repository-level licence and no licence in the linked
   `src/v4.24.0` subtree; other version subtrees do contain licence files.
7. Statement fidelity and the proof owner's trust policy remain unresolved,
   and the current Math profile excludes Erdős 56.

## Explicit nonclaims

- The trust closure does not establish falsehood, concealment, or scientific
  rejection.
- Zero propositional binders does not prove complete statement fidelity.
- The packet does not impose a universal policy against compiled reduction.
- The licence observation is not a repository-wide claim that no licence file
  exists, and the current Math authority cannot admit this candidate.

## Answerable questions

1. **E56-Q1:** What is the exact recorded axiom closure?
2. **E56-Q2:** Why is the compiled-reduction dependency called transitive?
3. **E56-Q3:** What do the build, binder, and closure facts establish and not
   establish?
4. **E56-Q4:** Who owns the proof, link classification, and any future
   authority action?
5. **E56-Q5:** What is the exact rights/licence uncertainty?
6. **E56-Q6:** Which independent Checks are still required?
7. **E56-Q7:** What is the single next human action?

Expected answers are held out. Their public byte commitment is in
[`ADJUDICATION_COMMITMENT.md`](ADJUDICATION_COMMITMENT.md).

## Same-information baseline views that can be constructed later

- **Git/source only:** the entire public packet's information through the exact
  FC/proof files plus plain-text build, closure, binder, Check, authority,
  uncertainty, rights, and next-action facts.
- **Native FC/registry presentation:** that same complete information set
  through the native proof link and source/trust presentation, without adding
  keyed answers.
- **Vela package:** that same complete information set as a source-bound trust
  artifact and Check input under a separately scoped Repository; no current
  Math Standing or extra source facts.

## Exact evidence and uncertainty

- Formal Conjectures link:
  [`FormalConjectures/ErdosProblems/56.lean`](https://github.com/google-deepmind/formal-conjectures/blob/9f5ee773841921f460b4a26a3552f5eca4accaa0/FormalConjectures/ErdosProblems/56.lean#L141-L150).
- Exact target:
  [`src/v4.24.0/ErdosProblems/Erdos56.lean`](https://github.com/plby/lean-proofs/blob/bebe632f2f6227a40e00b145bfbf7b3e1d68f8c2/src/v4.24.0/ErdosProblems/Erdos56.lean#L1272-L1346).
- Exact build and axiom reading:
  [`evaluations/fc-build-audit-v1/builds.json`](../../evaluations/fc-build-audit-v1/builds.json),
  file SHA-256
  `sha256:daeebec98ea61b6fccf4ea696306815020fcfdd88190f295bb4b2a5ea2a90cbf`.
- Curated audit finding:
  [`evaluations/fc-build-audit-v1/findings.json`](../../evaluations/fc-build-audit-v1/findings.json),
  file SHA-256
  `sha256:beeebc9b4ed1d2e381e0bf6386cff32f83d1f1b759d70f54cafa94c6847b18e5`.
- Target locator confidence: `high`, by file and declaration-name match.
- Source owner: `plby/lean-proofs`. GitHub exposes no repository-level licence,
  and neither the repository root nor the linked `src/v4.24.0` project subtree
  contains a licence file. Other version subtrees do contain licence files, so
  this packet makes no repository-wide no-licence claim. It references facts
  and locators only and does not prepare or redistribute a source patch.

The remaining uncertainty is policy and statement fidelity. The exact build
establishes the closure on one host at one source commit; it does not decide
whether Formal Conjectures intends `formal_proof` to permit this trust base or
whether the external theorem's complete type faithfully matches
`Erdos56.erdos_56`.

## Required independent Check and intended authority

1. In a clean checkout at `bebe632...`, build the v4.24.0 project and run
   `#print axioms Erdos56.erdos_56` under its pinned toolchain.
2. Independently compare the complete external and Formal Conjectures theorem
   types, including binder order and the `answer(False)` orientation.
3. Obtain the proof owner's explicit trust policy and contribution/licence
   direction before proposing source changes.

`plby/lean-proofs` owns the proof bytes and trust choice. Formal Conjectures
maintainers own whether the link's source status needs a disclosure or a
stricter Check. The current Vela Math profile covers only Erdős 321, 94, and
887, so this Repository authority must not admit the Erdős 56 candidate. A
separately established, appropriately scoped Repository authority could later
decide the bounded trust-closure assertion after the independent build and
fidelity Check; no profile migration or new authority is proposed here.

## Exact upstream message — not posted

> At commit `bebe632f2f6227a40e00b145bfbf7b3e1d68f8c2`, a clean build and
> `#print axioms Erdos56.erdos_56` report `Lean.ofReduceBool` and
> `Lean.trustCompiler` in addition to Mathlib's standard three axioms. The
> dependency is transitive through supporting lemmas; it is not visible in the
> target declaration itself. Is compiled reduction the intended trust policy
> for this Result, or would you welcome a contribution that removes it? The
> repository root and linked `src/v4.24.0` project expose no licence file, so
> please also state the contribution/licence terms before anyone prepares a
> code patch.

The one human action is the proof owner's combined trust and contribution
direction. No new issue, comment, or patch was posted by this task.
