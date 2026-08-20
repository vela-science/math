# Docker source-native Result attempts — Batch 2

This directory contains ten producer-side candidate packets for independent
evaluation. Nothing here is a Vela Submission, Verification, Decision, or
Standing mutation, and no scientific authority is asserted.

## Execution boundary

- Branch: `codex/docker-result-attempts-batch-2-2026-08-20`
- Base: Math `origin/main` at
  `5de716c896065c03c0a470d015ba2a328a527f73`
- Formal Conjectures source: `origin/main` at
  `9c4d5821819656af53c5473ded2116ea14a7ff1c`
- Reachable comparison source: `lean-proofs` `origin/main` at
  `852ffa6b50f3501a66d7ffbc116d8ae9b749c60c`
- Docker context: `desktop-linux`
- Image:
  `vela-math-result-candidate@sha256:c290b6490fb78c3702694b311fe9f07bd03002d7c1c979b3e5723d6b9f579e01`
- Candidate runner: Codex CLI 0.145.0 through the existing OAuth path
- Model sessions: 10 assigned, 10 completed, 0 retries
- Summed candidate-session elapsed time: 1001.90 seconds
- No Lean build was completed by a candidate session; build/check status is
  preserved verbatim in each packet.

The exact up-front source check and fixed denominator are in `SELECTION.md`.
Each output directory contains the unedited candidate `candidate.json`, a
mechanically reduced `tool-calls.json`, and a producer `receipt.json`. The raw
JSONL event stream was credential-scanned, hashed into the receipt, and then
removed; it is not a campaign artifact.

## Outcomes

| # | Case | Type | Candidate outcome | Elapsed |
|---|---|---|---|---:|
| 1 | Erdős 697 delta bound | proposed result | Falsifies the stated universal target at `m = 0`; proposes a domain repair but does not prove the repaired bound. | 102.72 s |
| 2 | Erdős 822 negative control | typed non-result | Finds no proof-bearing theorem in the exact reachable sources; paper prose and TODO text are not promoted. | 86.75 s |
| 3 | Erdős 1 least `N = 5` | proposed result | Gives the witness `{3,6,11,12,13}`, its 32 subset sums, and a finite-search certificate claim for all `N < 13`; Lean formalization remains unchecked. | 171.62 s |
| 4 | Erdős 291 infinite gcd | typed non-result | Derives a candidate infinite family only through the still-unproved `steinerberger_generalization`; no unconditional result. | 127.89 s |
| 5 | Erdős 399 Cambie variant | proposed result | Gives a complete mathematical mod-8 case split; Lean formalization remains unchecked. | 132.44 s |
| 6 | Erdős 945 equivalence | proposed result | Gives a two-direction mathematical proof sketch for the exact definitions; Lean formalization remains unchecked. | 80.09 s |
| 7 | Erdős 318 positive density | typed non-result | Gives an explicit conditional witness, but retains the unresolved `contain_single_even` and density dependencies. | 71.53 s |
| 8 | Erdős 697 threshold identity | proposed result | Identifies an exact swap between the prose inequalities and the Lean hypotheses in parts i and ii. | 52.41 s |
| 9 | Erdős 683/961 identity | typed non-result | Does not establish the TODO equivalence; identifies the missing fixed-power/polylog bridge and small-start branch. | 81.87 s |
| 10 | Erdős 260 negative control | typed non-result | Finds neither proof nor counterexample in inspected bytes and keeps stronger TODO variants separate. | 94.58 s |

Session 9's schema-valid packet has an empty `proposed_result` string. Its
typed non-result is still inspectable through the question, evidence,
limitations, build/check outcome, and smallest independent check. This output
limitation is preserved rather than retried or silently repaired.

## Independent-evaluation handoff

Evaluate the ten packets individually against their exact source commits and
paths. In particular, independently check the `m = 0` semantics in case 1,
the exhaustive-search claim in case 3, the mod-8 coverage in case 5, both
directions and endpoint handling in case 6, and the byte-level prose/Lean swap
in case 8. Treat mathematical sketches, finite-search reports, and process exit
success as candidate evidence only—not acceptance.
