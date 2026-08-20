# `math-result-candidate-erdos-750-conditional-stiebitz-2026-08-20`

## Bounded assertion

At exact commits
`google-deepmind/formal-conjectures@9f5ee773841921f460b4a26a3552f5eca4accaa0`
and
`Shashi456/erdos-formalizations@286f856aa3fc08957b80950fd18a45aab8d045ea`,
the linked declaration `Erdos750.erdos_750_FC` builds and its recorded axiom
closure is exactly:

```text
propext
Classical.choice
Erdos750.stiebitz_lower_bound
Quot.sound
```

The proof is therefore conditional on
`Erdos750.stiebitz_lower_bound`. Formal Conjectures already describes that
scope correctly: its
[`Erdos750.erdos_750`](https://github.com/google-deepmind/formal-conjectures/blob/9f5ee773841921f460b4a26a3552f5eca4accaa0/FormalConjectures/ErdosProblems/750.lean#L106-L144)
uses `conditional formal_proof ... assuming erdos_750.variants.stiebitz` and
the linked source declares
[`axiom stiebitz_lower_bound`](https://github.com/Shashi456/erdos-formalizations/blob/286f856aa3fc08957b80950fd18a45aab8d045ea/Erdos/P750/Proof.lean#L210-L221).

This is a candidate Result of the form “the external declaration's statement
follows from the stated Stiebitz theorem at these exact source bytes.” Calling
it a Result about the exact Formal Conjectures occurrence remains conditional
on the pending complete-type comparison below. It is not an unconditional
formal proof of Erdős 750 and not a new proof of Stiebitz's theorem.

## Observable facts available to every comparison condition

The numbered list is a quick summary. Every condition receives this entire
public packet, including the evidence and uncertainty, required Check and
authority, upstream message, and next action below.

1. The two exact upstream heads, files, and declaration names above.
2. Formal Conjectures uses `conditional formal_proof` and names
   `erdos_750.variants.stiebitz` as its assumption.
3. The external source declares `axiom stiebitz_lower_bound`.
4. The exact checkout built and the four-name axiom closure above was read.
5. The static locator confidence is `medium` because the URL names a file but
   not a declaration.
6. The external declaration uses `V : Type`; Formal Conjectures uses
   `V : Type*`; complete-type fidelity remains pending.
7. The source repository is Apache-2.0, and the current Math profile excludes
   Erdős 750.

## Explicit nonclaims

- The packet does not prove Stiebitz's theorem or an unconditional Erdős 750
  result.
- A successful build and axiom reading do not establish statement fidelity.
- Formal Conjectures' `research solved` category does not erase its explicit
  `conditional` scope.
- The current Vela Math Repository authority cannot admit this out-of-scope
  candidate.

## Answerable questions

1. **E750-Q1:** What is the exact recorded axiom closure?
2. **E750-Q2:** What conditional Result is, and is not, established?
3. **E750-Q3:** Does Formal Conjectures currently disclose the condition?
4. **E750-Q4:** What does the mechanical Check establish, and what fidelity
   question remains?
5. **E750-Q5:** Who owns the proof, source status, and any future authority
   action?
6. **E750-Q6:** Which independent Checks are still required?
7. **E750-Q7:** What is the single next human action?

Expected answers are held out. Their public byte commitment is in
[`ADJUDICATION_COMMITMENT.md`](ADJUDICATION_COMMITMENT.md).

## Same-information baseline views that can be constructed later

- **Git/source only:** the entire public packet's information through the exact
  FC and proof files plus plain-text build, closure, Check, authority,
  uncertainty, and next-action facts.
- **Native FC/registry presentation:** that same complete information set
  through the conditional attribute, proof link, and source dependency
  presentation, without adding keyed answers.
- **Vela package:** that same complete information set as a source-bound
  conditional artifact and Check input under a separately scoped Repository;
  no current Math Standing or extra source facts.

## Exact evidence and uncertainty

- Static target resolution:
  [`evaluations/fc-conditional-proof-audit-v1/results.json`](../../evaluations/fc-conditional-proof-audit-v1/results.json),
  file SHA-256
  `sha256:839ec9604718a19ed9da630b169c06a1d36f3ebcb26f62c5f24332118b37a941`.
- Exact build and axiom reading:
  [`evaluations/fc-build-audit-v1/builds.json`](../../evaluations/fc-build-audit-v1/builds.json),
  file SHA-256
  `sha256:daeebec98ea61b6fccf4ea696306815020fcfdd88190f295bb4b2a5ea2a90cbf`.
- Curated audit finding:
  [`evaluations/fc-build-audit-v1/findings.json`](../../evaluations/fc-build-audit-v1/findings.json),
  file SHA-256
  `sha256:beeebc9b4ed1d2e381e0bf6386cff32f83d1f1b759d70f54cafa94c6847b18e5`.
- Source owner: `Shashi456/erdos-formalizations`; licence: Apache-2.0.
- Formal Conjectures review evidence: issue
  [#4881](https://github.com/google-deepmind/formal-conjectures/issues/4881)
  and merged problem-750 annotation PR
  [#4885](https://github.com/google-deepmind/formal-conjectures/pull/4885).

The audit locator was `medium` confidence because the `formal_proof` URL names
a file but not a declaration. Direct source inspection identifies
`Erdos750.erdos_750_FC`, but an independent statement-fidelity review must
still compare it with the exact Formal Conjectures occurrence, including the
source's documented `Type` versus Formal Conjectures' `Type*` difference.

## Required independent Check and intended authority

1. In a clean checkout at `286f856...`, build `Erdos/P750/Proof.lean` with its
   pinned toolchain and run `#print axioms Erdos750.erdos_750_FC`.
2. Independently compare the complete declaration types, not their names or
   prose summaries, and record the universe-level difference.
3. Ask the proof owner to confirm the exact intended Stiebitz theorem and
   references before anyone attempts to discharge the axiom.

`Shashi456/erdos-formalizations` owns the proof bytes. Formal Conjectures
maintainers own the conditional source status. The current Vela Math profile
covers only Erdős 321, 94, and 887, so this Repository authority must not admit
the Erdős 750 candidate. A separately established, appropriately scoped
Repository authority could later decide the bounded conditional implication
after those Checks; no profile migration or new authority is proposed here.

## Exact upstream message — not posted

> At commit `286f856aa3fc08957b80950fd18a45aab8d045ea`, a clean build and
> `#print axioms Erdos750.erdos_750_FC` report Mathlib's standard three axioms
> plus only `Erdos750.stiebitz_lower_bound`. Formal Conjectures now correctly
> marks the link conditional at commit
> `9f5ee773841921f460b4a26a3552f5eca4accaa0`. Would you like an external
> contribution to formalize the stated Stiebitz lower bound, and are the
> references and declaration in `Proof.lean` the exact specification you want
> that contribution to target? Until that dependency is discharged, downstream
> users should cite this as a conditional Result.

The one human action is the proof owner's yes/no scope decision for discharging
the Stiebitz dependency. No new issue or comment was posted by this task.
