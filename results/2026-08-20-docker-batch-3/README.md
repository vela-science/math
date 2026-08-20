# Docker Result Factory — Batch 3

Ten source-native candidate sessions were run for independent evaluation.
These packets do not constitute Vela Submissions, Verifications, Decisions,
independence findings, or Standing changes.

## Exact boundary

- Branch: `codex/docker-result-attempts-batch-3-2026-08-20`
- Math base: `5de716c896065c03c0a470d015ba2a328a527f73`
- FC source: `9c4d5821819656af53c5473ded2116ea14a7ff1c`
- Reachable lean-proofs source:
  `852ffa6b50f3501a66d7ffbc116d8ae9b749c60c`
- Docker context: `desktop-linux`
- Image:
  `vela-math-result-candidate@sha256:c290b6490fb78c3702694b311fe9f07bd03002d7c1c979b3e5723d6b9f579e01`
- Runner: Codex CLI 0.145.0 through the existing read-only OAuth path
- Sessions: 10 assigned, 10 completed, 0 model retries
- Summed session elapsed time: 1290.59 seconds
- Observable shell calls retained with exact output: 85

The slate and duplicate gate are in `SELECTION.md`; packet rules are in
`CONTRACT.md`. Each output directory contains the unedited candidate JSON,
full-output `tool-calls.json`, and a hash receipt. Raw model event streams were
credential-scanned, hashed in the receipts, and removed before commit.

## Candidate outcomes

| # | Target | Status | Candidate outcome | Time |
|---|---|---|---|---:|
| 1 | Erdős 479 | statement correction | Lean omits `k = 0`; candidate supplies a mathematical infinite witness family and proposes `k ≠ 1`. | 102.15 s |
| 2 | Erdős 849 | statement correction | Candidate concludes no defect is established because admissible binomial coefficients are strictly increasing in `k`; equivalence is not Lean-checked. | 190.33 s |
| 3 | Erdős 850 | statement correction | Recommends changing prose “integers” to “natural numbers”; flags negative/zero conventions. | 117.76 s |
| 4 | Erdős 1074 initial EHS numbers | computational certificate | Exact retained factorization/residue output certifies the first seven values through 17; no Lean proof. | 112.54 s |
| 5 | Erdős 1063 Monier bound | dependency finding | Reduces the target to two explicit factorial/binomial divisibility lemmas; no proof term. | 151.95 s |
| 6 | Erdős 1136 multiples of three | proof sketch | Separates an elementary avoidance proof from the density-of-multiples limit. | 119.67 s |
| 7 | Erdős 120 finite set | proof sketch | Identifies a finite homothetic-copy lemma not supplied by Steinhaus's difference-set theorem alone. | 124.83 s |
| 8 | Erdős 214 bounds | dependency finding | Gives a conditional `sSup` bridge from `HasRedCopies 4`, `¬ HasRedCopies 8`, and antitonicity. | 125.91 s |
| 9 | Erdős 251 | typed non-result | No proof/counterexample in inspected bytes; records a zero-based indexing/scaling issue. | 134.15 s |
| 10 | Erdős 938 | typed non-result | No proof/counterexample; records that formal powerful-number enumeration begins at 0. | 111.30 s |

Session 2's `result_status` says `statement_correction`, while its nonblank
result concludes that no fidelity defect is established. The original packet
is retained unchanged; the evaluator should decide whether this is a useful
fidelity result or a status-classification failure.

## Smallest evaluation handoff

Evaluate each packet against its exact source and retained commands. Prioritize
the mathematical/Lean check of case 1's `k = 0` bridge, independent replay of
case 4's finite certificate, the missing divisibility lemmas in case 5, the
density API route in case 6, the quantifier-order dependency in case 7, and
the conditional `sSup` bridge in case 8. Treat every sketch and certificate as
candidate evidence only.
