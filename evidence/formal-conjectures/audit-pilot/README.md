# Formal Conjectures audit pilot: Phase 0

This directory freezes the source-local evaluation inputs for `FC-03` and
`EVAL-01` in the Vela ecosystem convergence program. It does not implement the
Formal Conjectures audit generator and does not create Vela scientific state.

## Records

- `phase-0-fixture-selection.v0.1.json` selects five exact base/head pairs and
  states the expected distinctions the audit must preserve. All five now have
  frozen, source-grounded classifications, including a bounded source-fidelity
  pass tied to the exact #4829 head.
- `precollection-design.v0.1.json` freezes the bounded human pilot before any
  outcome collection: twelve participants in six independent handoff dyads,
  all five fixtures, the balanced condition schedule, eligibility and missing-
  session rules, fixed stopping, primary estimands, cluster-level uncertainty,
  support thresholds, and amendment policy. It authorizes no recruitment or
  contact. Collection remains blocked on complete human ground truth, consent,
  recruitment, participant packets, allocation receipt, and private custody.
- `phase-0-baseline-observations.v0.1.json` is an intentionally empty result
  scaffold. Empty means measurements have not been collected; it does not mean
  zero time or zero defects.
- `collection-materials.v0.1.json` freezes the consent text, custody plan,
  allocation-receipt format, and session-opening checks without naming or
  contacting a participant.
- `condition-packet-set.v0.1.json` freezes five matched control/treatment pairs.
  Each pair has the same source, task wording, public evidence, and access
  limits; treatment adds only the retained core and observation audit records.
- `collection-readiness.v0.1.json` records those materials as complete while
  leaving collection closed. A human custodian, recruited and consented
  participants, activated private custody, and an instantiated outcome-blind
  allocation receipt remain required.

Current roots:

- collection materials: `sha256:7687a7ee455883a812b1079ca6e2e0d1ffe7fb2f369095f80507eefc039287a1`;
- ten-packet matched set: `sha256:709da24b77e18da5d897da71a2b526414c629287fb90c33911d642500bb2b753`;
- closed readiness record: `sha256:929274a55840910ad66a869e115dc6bd765a35205ae524fb71c6f3417f3b1cda`.
- `source-snapshots/` retains normalized GitHub pull-request, review, Check
  Runs, and legacy commit-status API observations acquired on August 12, 2026.
  Normalized evidence is a selected, sorted representation of primary API
  fields; it is not described as canonical GitHub response bytes. Its SHA-256
  roots are in the selection record so a later reader does not depend on
  mutable API state or a historical pull-request ref remaining fetchable.
- `phase-0-packet-manifest.v0.1.json` binds the selection, method,
  precollection design, empty observation scaffold, and every retained source
  observation by exact SHA-256.
- `../../../methods/formal-conjectures/audit-baseline.v0.1.json` defines the
  matched control/treatment tasks, planned hypotheses, clocks, ground truth,
  interface kill criteria, and analysis rules. `H2` and `H5` are the Phase 0
  primary hypotheses. Their precollection design is now frozen and rooted;
  collection is still blocked by consent, recruitment, packet, allocation, and
  private-custody opening conditions. `H1`, `H3`, and
  `H6` remain explicitly untested until later pilots.

## Five selected cases

| Fixture | Exact pull request | Required distinction |
| --- | --- | --- |
| `clean-source-faithful-min-modulus-4829` | `#4829` | The paper author found the open declaration faithful to Conjecture 1; the declaration is unchanged through the applied correction and exact final head |
| `conditional-erdos-427-4884` | `#4884` | A proof pass retains its Shiu-theorem condition |
| `fidelity-erdos-887-1237` | `#1237` | The exact head builds, but its answer slot sits inside the `C` and `n` binders instead of expressing one absolute `K` |
| `vacuity-erdos-80-4830` | `#4830` | A merged, mechanically clean statement can have an unsatisfiable boundary case |
| `unavailable-rupert-3959` | `#3959` | The exact head names a mutable external repository root but no exact proof file or revision |

The first case is clean only in a bounded source-fidelity sense. The paper
author explicitly reviewed `MinModulus.min_modulus` as faithful to Conjecture 1
and supplied the zero-modulus witness for its guard. The reviewed theorem is
unchanged through correction commit `225c54f1...` and exact final head
`0f8d60f1...`, which also has an exact-head maintainer approval and passing
build. This does not establish mathematical truth, proof correctness, or
fidelity of the file's other declarations.

The retired PR `#4878` candidate is not clean. Primary-source checking found
incorrect author and page-range citations despite approval and a passing
build. That failure is retained as a regression rule: community and mechanical
signals cannot substitute for source fidelity.

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

A human or AI review is advisory evidence by default. Either can become a Vela
Verification only through the local Repository's eligible-verifier policy,
committed method, exact-input, signing, and submission boundary; reviewer class
is retained provenance, not a quality rank, and this audit packet cannot mint a
Verification. Likewise, an FC review, merge, rejection, or correction is an
external community observation for Math. Only an authorized, attributed Math
Repository Decision changes local Standing; its performer may be human or
agent and must remain distinct from the Repository authority principal.

## Authority and limits

These files are evaluation evidence. They do not:

- change Formal Conjectures review or merge status;
- issue a Vela Verification or Decision;
- change Standing;
- infer proof absence or failure from unresolved exact artifact identity;
- establish external adoption or independent validation.

The mechanically passing, semantic-failure, availability, and community-status
axes must remain separate in every downstream projection.
