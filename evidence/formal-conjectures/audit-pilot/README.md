# Formal Conjectures audit pilot: Phase 0

This directory freezes the source-local evaluation inputs for `FC-03` and
`EVAL-01` in the Vela ecosystem convergence program. It does not implement the
Formal Conjectures audit generator and does not create Vela scientific state.

## Records

- `phase-0-fixture-selection.v0.1.json` selects five exact base/head pairs and
  states the expected distinctions the audit must preserve. Four have frozen,
  source-grounded classifications; the clean control remains a candidate
  pending exact-head human review, so the five-fixture ground-truth exit is not
  met.
- `phase-0-baseline-observations.v0.1.json` is an intentionally empty result
  scaffold. Empty means measurements have not been collected; it does not mean
  zero time or zero defects.
- `source-snapshots/` retains normalized GitHub pull-request, review, Check
  Runs, and legacy commit-status API observations acquired on August 12, 2026.
  Normalized evidence is a selected, sorted representation of primary API
  fields; it is not described as canonical GitHub response bytes. Its SHA-256
  roots are in the selection record so a later reader does not depend on
  mutable API state or a historical pull-request ref remaining fetchable.
- `phase-0-packet-manifest.v0.1.json` binds the selection, method, empty
  observation scaffold, and every retained source observation by exact
  SHA-256.
- `../../../methods/formal-conjectures/audit-baseline.v0.1.json` defines the
  matched control/treatment tasks, planned hypotheses, clocks, ground truth,
  interface kill criteria, and analysis rules. `H2` and `H5` are the planned
  Phase 0 primary hypotheses. This is not yet a complete preregistration: the
  sample, eligibility, allocation, counterbalance schedule, stopping rule,
  estimator, uncertainty method, and claim thresholds require a rooted
  precollection supplement. Collection and all H2/H5 support claims are
  blocked until that supplement is frozen. `H1`, `H3`, and `H6` remain
  explicitly untested until later pilots.

## Five selected cases

| Fixture | Exact pull request | Required distinction |
| --- | --- | --- |
| `clean-candidate-dean-4878` | `#4878` | Clean control candidate only; a human review of the exact head is still required |
| `conditional-erdos-427-4884` | `#4884` | A proof pass retains its Shiu-theorem condition |
| `fidelity-erdos-887-1237` | `#1237` | The exact head builds, but its answer slot sits inside the `C` and `n` binders instead of expressing one absolute `K` |
| `vacuity-erdos-80-4830` | `#4830` | A merged, mechanically clean statement can have an unsatisfiable boundary case |
| `unavailable-rupert-3959` | `#3959` | The exact head names a mutable external repository root but no exact proof file or revision |

The first case is deliberately called a candidate, not clean. Approval and
successful native checks are useful observations, not a witness-backed
statement-fidelity verdict. It fulfills the `clean_source_faithful` target role
only after a domain reviewer checks commit
`521f6a64402d238f1d040edfeda42c3d8eeb0b98` against the cited sources.

The availability case is equally narrow. At PR `#3959` head
`868cc092aeb713dbf8027883c5fa575e550cfae9`, the metadata does not identify
which external file or revision is the proof artifact. Later open PR `#4895`
records that the external repository has multiple candidate proof routes and
proposes one immutable locator. This establishes an unresolved exact artifact
identity at the fixture head; it does not establish proof absence or failure.

Two rejected candidates are retained as a regression guard. PR `#3941`'s
forum post resolves to immutable raw Gist bytes, and PR `#4883`'s empty
`formal_conjectures` location denotes an intentional proof in the source file.
Neither may be classified as unavailable merely to fill the fifth role.

Handoff observations are also typed explicitly. H5 requires a rooted sender
review, a distinct linked receiver continuation, and a matching pair record
with separate pseudonymous context. All three must agree on ids, fixture,
condition, packet root, participants, receiver context, and timestamps. A
single-participant observation or two different pseudonyms without an
independence basis cannot test the handoff hypothesis.

The exact semantic-witness records disclose that Codex prepared and rooted the
packet. Their conclusions are attributed separately to human-authored
source-local observations: the confirmed Erdős 887 finding in `REVIEW_MATH`
and PR `#4877`'s exact correction of PR `#4830`. AI packet preparation is
advisory transcription; it does not itself supply human ground truth, create a
Math Repository Decision, or change Standing.

An AI review is advisory observation by default. It can become a Vela
Verification only through the local Repository's eligible-verifier policy,
committed method, exact-input, signing, and submission boundary; this audit
packet cannot mint one. Likewise, an FC review, merge, rejection, or correction
is an external community observation for Math. Only an authorized human Math
Repository Decision can change local Math Standing.

## Authority and limits

These files are evaluation evidence. They do not:

- change Formal Conjectures review or merge status;
- issue a Vela Verification or Decision;
- change Standing;
- infer proof absence or failure from unresolved exact artifact identity;
- establish external adoption or independent validation.

The mechanically passing, semantic-failure, availability, and community-status
axes must remain separate in every downstream projection.
